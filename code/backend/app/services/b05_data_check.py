"""b05 数据校验管理服务：校验结果导入（双模板）、校验概览（最新/近7天）、任务级校验结果刷新。

依据《数据校验-数据校验结果导入与刷新需求》V1.0：
- `b05_check_result` 按「数据日期 + 库名 + 表名」记录每次校验的源/目标端数据量与结果（目标端库表口径，D3）；
- 数据校验列表以 b03 库表清单为行，左连最新校验结果与近 7 天校验序列（T-7~T-1，降序，D8）；
- 导入支持「默认模板」与「腾讯数据校验工具模板」（convert_check_result.py 转换逻辑），
  按前端选择的数据日期批量 upsert（D5）；
- 导入确认后按血缘输出正式表刷新 `b04_task.check_result`（多输出表全部通过才为通过，D7）。
"""

from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Set, Tuple

from fastapi import UploadFile
from sqlalchemy import and_, func, or_, tuple_
from sqlalchemy.orm import Session

from app.core.exceptions import BizError, NotFoundError
from app.models.b03_data_migration import B03Scenario, B03TableItem
from app.models.b04_task_migration import (
    CHECK_RESULT_FAILED,
    CHECK_RESULT_NONE,
    CHECK_RESULT_PASSED,
    B04Task,
)
from app.models.b05_data_check import (
    CHECK_TEMPLATES,
    CHECK_TEMPLATE_DEFAULT,
    CHECK_TEMPLATE_TENCENT,
    B05CheckResult,
)
from app.models.b07_lineage import TABLE_TYPE_FORMAL, B07Lineage
from app.schemas.b05_data_check import RECENT_DAYS, CheckResultDay
from app.utils import excel as xl

# ── 导入模板列定义 ──
# 默认模板：库名、表名、源端数据量、目标端数据量、结果(通过/不通过)
DEFAULT_TEMPLATE_HEADERS = ["库名", "表名", "源端数据量", "目标端数据量", "结果"]
# 腾讯数据校验工具模板（TDM 校验结果 CSV 原始字段，参考 convert_check_result.py）
TENCENT_TEMPLATE_HEADERS = ["srcDatabase", "srcTable", "srcResult", "dstResult", "checkResult"]
# 各模板必要列（缺失即拒绝导入）
DEFAULT_REQUIRED_COLUMNS = {"库名", "表名", "结果"}
TENCENT_REQUIRED_COLUMNS = {"srcDatabase", "srcTable", "checkResult"}
# 模板列名 → 统一字段
DEFAULT_COLUMN_MAP = {
    "库名": "db_name",
    "表名": "table_name",
    "源端数据量": "src_volume",
    "目标端数据量": "dst_volume",
    "结果": "result",
}
TENCENT_COLUMN_MAP = {
    "srcDatabase": "db_name",
    "srcTable": "table_name",
    "srcResult": "src_volume",
    "dstResult": "dst_volume",
    "checkResult": "result",
}

# 数据校验结果导入单文件行数上限（b05 专用，5 万行；不影响 b03/b04 的 xl.MAX_IMPORT_ROWS=5000）
MAX_CHECK_IMPORT_ROWS = 50000
# 预取同日已有记录的分块大小（tuple IN 分块，避免超长 SQL）
_EXISTING_CHUNK = 1000


def _template_headers(template: str) -> List[str]:
    if template == CHECK_TEMPLATE_DEFAULT:
        return DEFAULT_TEMPLATE_HEADERS
    return TENCENT_TEMPLATE_HEADERS


def check_template_xlsx(template: str) -> bytes:
    """生成导入模板 xlsx（默认模板含中文表头示例；腾讯模板含 TDM 字段示例）。"""
    if template == CHECK_TEMPLATE_DEFAULT:
        return xl.make_xlsx(
            DEFAULT_TEMPLATE_HEADERS,
            [["ods_order", "ods_order_detail", "1000", "1000", "通过"]],
            [18] * len(DEFAULT_TEMPLATE_HEADERS),
        )
    return xl.make_xlsx(
        TENCENT_TEMPLATE_HEADERS,
        [["ods_order", "ods_order_detail", "1000", "1000", "true"]],
        [18] * len(TENCENT_TEMPLATE_HEADERS),
    )


def _table_key(
    db_name: Optional[str],
    table_name: Optional[str],
    target_db: Optional[str],
    target_table: Optional[str],
) -> Tuple[str, str]:
    """库表清单行的目标端库表键：目标库表为空时回退源库表（D3 落地的容错口径）。"""
    return (
        (target_db or db_name or "").strip(),
        (target_table or table_name or "").strip(),
    )


def _latest_map(
    sdb: Session, space_id: int, keys: Optional[Set[Tuple[str, str]]] = None
) -> Dict[Tuple[str, str], B05CheckResult]:
    """批量取每个库表键的最新一条校验记录（data_date 最大，同日取 id 最大）。

    keys=None 表示空间内全部键；返回 {(库名, 表名): B05CheckResult}。
    实现：先 GROUP BY 取每键最大日期，再按（键, 日期）批量取行——避免自连接，
    兼容 MySQL / StarRocks。
    """
    if keys is not None and not keys:
        return {}

    def _key_scope(query):
        if keys is None:
            return query
        return query.filter(tuple_(B05CheckResult.db_name, B05CheckResult.table_name).in_(list(keys)))

    max_rows = (
        _key_scope(
            sdb.query(
                B05CheckResult.db_name,
                B05CheckResult.table_name,
                func.max(B05CheckResult.data_date).label("max_date"),
            )
        )
        .filter(B05CheckResult.space_id == space_id, B05CheckResult.deleted_at.is_(None))
        .group_by(B05CheckResult.db_name, B05CheckResult.table_name)
        .all()
    )
    if not max_rows:
        return {}
    max_pairs = {(db, tbl, md) for db, tbl, md in max_rows}
    max_dates = {md for _, _, md in max_pairs}
    candidates = (
        _key_scope(sdb.query(B05CheckResult))
        .filter(
            B05CheckResult.space_id == space_id,
            B05CheckResult.deleted_at.is_(None),
            B05CheckResult.data_date.in_(max_dates),
        )
        .all()
    )
    latest: Dict[Tuple[str, str], B05CheckResult] = {}
    for r in candidates:
        if (r.db_name, r.table_name, r.data_date) not in max_pairs:
            continue
        cur = latest.get((r.db_name, r.table_name))
        if cur is None or r.id > cur.id:
            latest[(r.db_name, r.table_name)] = r
    return latest


def get_check_results_by_tables(
    sdb: Session, space_id: int, tables: Optional[List[Tuple[str, str]]] = None, days: int = 7
) -> Dict[Tuple[str, str], List[B05CheckResult]]:
    """按表批量取最近 N 天（T-1 起，不含今天）的校验结果，供血缘节点□渲染。

    tables: [(db_name, table_name), ...]；为 None 时返回本空间全部表的最近 N 天结果
    （血缘整图场景下避免前端拼接超长 URL 导致请求被拒）。
    返回 {(db_name, table_name): [B05CheckResult...]}（按日期降序）。
    """
    if days < 1:
        days = 1
    today = date.today()
    window_start = today - timedelta(days=days)
    window_end = today - timedelta(days=1)  # 不含今天（与近 7 天口径一致）
    q = sdb.query(B05CheckResult).filter(
        B05CheckResult.space_id == space_id,
        B05CheckResult.deleted_at.is_(None),
        B05CheckResult.data_date >= window_start,
        B05CheckResult.data_date <= window_end,
    )
    if tables:
        q = q.filter(tuple_(B05CheckResult.db_name, B05CheckResult.table_name).in_(tables))
    rows = q.order_by(B05CheckResult.data_date.desc()).all()
    out: Dict[Tuple[str, str], List[B05CheckResult]] = {}
    # 显式指定了表（tables 非 None）：为每张被请求的表预留空列表，未命中返回 []；
    # 未指定 tables 时只返回本空间有数据的表（避免前端整图拼接超长 URL）。
    if tables is not None:
        for t in tables:
            out.setdefault(t, [])
    for r in rows:
        out.setdefault((r.db_name, r.table_name), []).append(r)
    return out


def list_checks(
    sdb: Session,
    space_id: int,
    scenario_id: Optional[int] = None,
    keyword: Optional[str] = None,
    result: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
) -> Tuple[List[dict], int]:
    """数据校验概览：b03 库表清单为行 + 最新校验结果 + 近 7 天序列（T-7~T-1 降序，D8）。"""
    if scenario_id is not None:
        scenario = (
            sdb.query(B03Scenario)
            .filter(
                B03Scenario.id == scenario_id,
                B03Scenario.space_id == space_id,
                B03Scenario.deleted_at.is_(None),
            )
            .first()
        )
        if not scenario:
            raise NotFoundError(f"迁移场景不存在: {scenario_id}")

    q = sdb.query(B03TableItem).filter(
        B03TableItem.space_id == space_id,
        B03TableItem.deleted_at.is_(None),
    )
    if scenario_id is not None:
        q = q.filter(B03TableItem.scenario_id == scenario_id)
    if keyword:
        like = f"%{keyword}%"
        q = q.filter(
            or_(
                B03TableItem.db_name.like(like),
                B03TableItem.table_name.like(like),
                B03TableItem.target_db_name.like(like),
                B03TableItem.target_table_name.like(like),
            )
        )

    # 结果过滤：按各库表最新一条记录的结果过滤（无记录视作「无校验结果」）
    if result:
        latest_all = _latest_map(sdb, space_id)
        key_expr = tuple_(
            func.coalesce(B03TableItem.target_db_name, B03TableItem.db_name),
            func.coalesce(B03TableItem.target_table_name, B03TableItem.table_name),
        )
        if result == "无校验结果":
            has_record_keys = set(latest_all.keys())
            if has_record_keys:
                q = q.filter(key_expr.notin_(list(has_record_keys)))
        else:
            matched = {k for k, r in latest_all.items() if r.result == result}
            q = q.filter(key_expr.in_(list(matched)))

    total = q.count()
    rows = q.order_by(B03TableItem.id.asc()).offset((page - 1) * page_size).limit(page_size).all()

    # 批量取本页库表的最新记录与近 7 天窗口记录
    keys = {
        _table_key(r.db_name, r.table_name, r.target_db_name, r.target_table_name) for r in rows
    }
    keys.discard(("", ""))
    latest_map = _latest_map(sdb, space_id, keys)

    today = date.today()
    window_start = today - timedelta(days=RECENT_DAYS)  # T-7
    window_end = today - timedelta(days=1)  # T-1（不含今天，D8）
    window_map: Dict[Tuple[str, str], Dict[date, B05CheckResult]] = {}
    if keys:
        window_rows = (
            sdb.query(B05CheckResult)
            .filter(
                B05CheckResult.space_id == space_id,
                B05CheckResult.deleted_at.is_(None),
                tuple_(B05CheckResult.db_name, B05CheckResult.table_name).in_(list(keys)),
                B05CheckResult.data_date >= window_start,
                B05CheckResult.data_date <= window_end,
            )
            .all()
        )
        for r in window_rows:
            window_map.setdefault((r.db_name, r.table_name), {})[r.data_date] = r

    # 近 7 天日期序列：T-1 → T-7（降序，最近在左，D8）
    recent_dates = [today - timedelta(days=i) for i in range(1, RECENT_DAYS + 1)]

    out: List[dict] = []
    for r in rows:
        key = _table_key(r.db_name, r.table_name, r.target_db_name, r.target_table_name)
        latest = latest_map.get(key)
        per_day = window_map.get(key, {})
        recent_days = [
            CheckResultDay(
                data_date=d,
                result=per_day[d].result if d in per_day else None,
                src_volume=per_day[d].src_volume if d in per_day else None,
                dst_volume=per_day[d].dst_volume if d in per_day else None,
            )
            for d in recent_dates
        ]
        out.append(
            {
                "item_id": r.id,
                "scenario_id": r.scenario_id,
                "db_name": r.db_name,
                "table_name": r.table_name,
                "target_db_name": r.target_db_name,
                "target_table_name": r.target_table_name,
                "table_type": r.table_type,
                "latest_result": latest.result if latest else None,
                "latest_date": latest.data_date if latest else None,
                "latest_src_volume": latest.src_volume if latest else None,
                "latest_dst_volume": latest.dst_volume if latest else None,
                "recent_days": recent_days,
            }
        )
    return out, total


def _parse_row(
    template: str, row: dict
) -> Tuple[str, str, Optional[int], Optional[int], str]:
    """按模板解析单行为统一结构 (库名, 表名, 源端数据量, 目标端数据量, 结果)。"""
    col_map = DEFAULT_COLUMN_MAP if template == CHECK_TEMPLATE_DEFAULT else TENCENT_COLUMN_MAP
    header_of = {f: h for h, f in col_map.items()}

    def val(field: str) -> str:
        header = header_of.get(field)
        return xl._to_str(row.get(header)) if header else ""

    db_name = val("db_name")
    table_name = val("table_name")
    if not db_name or not table_name:
        raise ValueError("库名/表名不能为空")

    src_raw = val("src_volume")
    dst_raw = val("dst_volume")
    src_volume = xl._to_int(src_raw) if src_raw else None
    dst_volume = xl._to_int(dst_raw) if dst_raw else None

    if template == CHECK_TEMPLATE_DEFAULT:
        result = val("result")
        if result not in ("通过", "不通过"):
            raise ValueError(f"非法的校验结果: {result or '(空)'}")
    else:
        # 腾讯数据校验工具：checkResult == true（大小写不敏感）为通过，其余为不通过
        result = "通过" if val("result").lower() == "true" else "不通过"
    return db_name, table_name, src_volume, dst_volume, result


def import_check_results(
    sdb: Session,
    space_id: int,
    file: UploadFile,
    data_date: date,
    template: str,
    operator: str,
    scenario_id: Optional[int] = None,
) -> dict:
    """导入数据校验结果：解析 → 行校验 → upsert（同日同库表覆盖，D5）→ 任务级刷新（§8）。"""
    if template not in CHECK_TEMPLATES:
        raise BizError(f"非法的导入模板: {template}")
    if data_date > date.today():
        raise BizError("校验结果所属日期不能晚于今天")

    xl.check_import_file(file.filename)
    content = file.file.read()
    headers, rows, line_nos = xl.read_tabular(content, file.filename or "")
    if not rows:
        raise BizError("导入文件无数据行")
    if len(rows) > MAX_CHECK_IMPORT_ROWS:
        raise BizError(f"单次导入不得超过 {MAX_CHECK_IMPORT_ROWS} 行")

    required = (
        DEFAULT_REQUIRED_COLUMNS if template == CHECK_TEMPLATE_DEFAULT else TENCENT_REQUIRED_COLUMNS
    )
    missing = [c for c in _template_headers(template) if c in required and c not in headers]
    if missing:
        raise BizError(f"导入文件缺少必要列: {', '.join(missing)}")

    # 行级解析：错误行跳过并记录，不阻塞其它行
    errors: List[dict] = []
    parsed: Dict[Tuple[str, str], Tuple[str, str, Optional[int], Optional[int], str]] = {}
    for row, line_no in zip(rows, line_nos):
        try:
            db_name, table_name, src_volume, dst_volume, result = _parse_row(template, row)
        except ValueError as exc:
            errors.append({"row": line_no, "message": str(exc)})
            continue
        # 文件内同一（库名,表名）重复行：以最后一行为准
        parsed[(db_name, table_name)] = (db_name, table_name, src_volume, dst_volume, result)

    # 批量预取同日已有记录（分块 tuple IN，避免 5 万行逐行 SELECT）
    existing_map: Dict[Tuple[str, str], B05CheckResult] = {}
    keys_list = list(parsed.keys())
    for i in range(0, len(keys_list), _EXISTING_CHUNK):
        chunk = keys_list[i : i + _EXISTING_CHUNK]
        for rec in (
            sdb.query(B05CheckResult)
            .filter(
                B05CheckResult.space_id == space_id,
                B05CheckResult.data_date == data_date,
                B05CheckResult.deleted_at.is_(None),
                tuple_(B05CheckResult.db_name, B05CheckResult.table_name).in_(chunk),
            )
            .all()
        ):
            existing_map[(rec.db_name, rec.table_name)] = rec

    now = datetime.now()
    inserted = updated = 0
    new_rows: List[B05CheckResult] = []
    touched_keys: Set[Tuple[str, str]] = set()
    for (db_name, table_name), (_, _, src_volume, dst_volume, result) in parsed.items():
        existing = existing_map.get((db_name, table_name))
        if existing:
            existing.src_volume = src_volume
            existing.dst_volume = dst_volume
            existing.result = result
            existing.updated_by = operator
            existing.updated_at = now
            updated += 1
        else:
            new_rows.append(
                B05CheckResult(
                    space_id=space_id,
                    data_date=data_date,
                    db_name=db_name,
                    table_name=table_name,
                    src_volume=src_volume,
                    dst_volume=dst_volume,
                    result=result,
                    created_by=operator,
                )
            )
            inserted += 1
        touched_keys.add((db_name, table_name))
    if new_rows:
        sdb.add_all(new_rows)
    sdb.commit()

    # 清单外库表统计（D6：正常入库，仅提示条数；scenario_id 为空时按空间全量清单比较）
    item_q = sdb.query(B03TableItem).filter(
        B03TableItem.space_id == space_id, B03TableItem.deleted_at.is_(None)
    )
    if scenario_id is not None:
        item_q = item_q.filter(B03TableItem.scenario_id == scenario_id)
    list_keys = {
        _table_key(i.db_name, i.table_name, i.target_db_name, i.target_table_name)
        for i in item_q.all()
    }
    not_in_list = len(touched_keys - list_keys)

    # 导入后自动刷新任务级数据校验结果（§8）
    refreshed = refresh_task_check_results(sdb, space_id, touched_keys, operator)

    return {
        "inserted": inserted,
        "updated": updated,
        "skipped": len(errors),
        "errors": errors,
        "refreshed_tasks": refreshed,
        "not_in_list": not_in_list,
    }


def refresh_task_check_results(
    sdb: Session, space_id: int, touched_keys: Set[Tuple[str, str]], operator: str
) -> int:
    """按血缘输出正式表刷新任务数据校验结果（增量：仅本次导入涉及库表命中的任务）。

    关联链路（D3）：校验结果 库名.表名（目标端）→ b07_lineage.output_table
    AND output_table_type='正式表' → (project_name, task_name) → b04_task。
    判定（D7）：该任务全部正式输出表中，有记录的全为通过→通过；任一不通过→不通过；
    均无记录→无校验结果。返回实际发生变更的任务数。
    """
    if not touched_keys:
        return 0

    # 1. 血缘命中：输出表（正式表）→ 任务 → 该任务的全部正式输出表集合
    full_names = [f"{db}.{tbl}" for db, tbl in touched_keys]
    edges = (
        sdb.query(B07Lineage.project_name, B07Lineage.task_name, B07Lineage.output_table)
        .filter(
            B07Lineage.space_id == space_id,
            B07Lineage.output_table.in_(full_names),
            B07Lineage.output_table_type == TABLE_TYPE_FORMAL,
            B07Lineage.deleted_at.is_(None),
        )
        .all()
    )
    task_outputs: Dict[Tuple[str, str], Set[str]] = {}
    for project, task, output_table in edges:
        if not task or not project:
            continue  # 血缘缺项目/任务信息无法可靠归属，跳过
        task_outputs.setdefault((project, task), set()).add(output_table)
    if not task_outputs:
        return 0

    conditions = [
        and_(B04Task.project_name == p, B04Task.task_name == t) for p, t in task_outputs
    ]
    tasks = (
        sdb.query(B04Task)
        .filter(B04Task.space_id == space_id, B04Task.deleted_at.is_(None), or_(*conditions))
        .all()
    )
    if not tasks:
        return 0

    # 2. 批量取所有涉及输出表的最新校验记录（每张表独立取全历史最新）
    all_outputs: Set[Tuple[str, str]] = set()
    for outputs in task_outputs.values():
        for full in outputs:
            db_name, _, table_name = full.partition(".")
            if db_name and table_name:
                all_outputs.add((db_name, table_name))
    latest_map = _latest_map(sdb, space_id, all_outputs)

    # 3. 逐任务判定并写回
    now = datetime.now()
    changed = 0
    for task in tasks:
        outputs = task_outputs.get((task.project_name, task.task_name))
        if not outputs:
            continue
        results = []
        for full in outputs:
            db_name, _, table_name = full.partition(".")
            record = latest_map.get((db_name, table_name))
            if record is not None:
                results.append(record.result)
        if not results:
            new_value = CHECK_RESULT_NONE
        elif all(r == CHECK_RESULT_PASSED for r in results):
            new_value = CHECK_RESULT_PASSED
        else:
            new_value = CHECK_RESULT_FAILED
        if task.check_result != new_value:
            task.check_result = new_value
            task.updated_by = operator
            task.updated_at = now
            changed += 1
    sdb.commit()
    return changed


def refresh_all_task_check_results(sdb: Session, space_id: int, operator: str) -> int:
    """全空间重跑任务级数据校验结果刷新（B05-04：前端「刷新任务状态」按钮）。

    与增量刷新（refresh_task_check_results）判定口径一致：按血缘正式输出表聚合，
    该任务全部正式输出表中「有记录的全为通过」→通过；任一不通过→不通过；
    无正式输出表或所有输出表均无校验记录→无校验结果。返回实际发生变更的任务数。
    全空间重算，覆盖所有任务（含此前无校验结果的任务）。
    """
    tasks = (
        sdb.query(B04Task)
        .filter(B04Task.space_id == space_id, B04Task.deleted_at.is_(None))
        .all()
    )
    if not tasks:
        return 0

    # 1. 全空间血缘正式输出边 → 任务 → 该任务的全部正式输出表集合
    edges = (
        sdb.query(B07Lineage.project_name, B07Lineage.task_name, B07Lineage.output_table)
        .filter(
            B07Lineage.space_id == space_id,
            B07Lineage.output_table_type == TABLE_TYPE_FORMAL,
            B07Lineage.deleted_at.is_(None),
        )
        .all()
    )
    task_outputs: Dict[Tuple[str, str], Set[str]] = {}
    for project, task, output_table in edges:
        if not task or not project or not output_table:
            continue  # 血缘缺项目/任务/输出表信息无法可靠归属，跳过
        task_outputs.setdefault((project, task), set()).add(output_table)

    # 2. 批量取所有涉及输出表的最新校验记录（每张表独立取全历史最新）
    all_outputs: Set[Tuple[str, str]] = set()
    for outputs in task_outputs.values():
        for full in outputs:
            db_name, _, table_name = full.partition(".")
            if db_name and table_name:
                all_outputs.add((db_name, table_name))
    latest_map = _latest_map(sdb, space_id, all_outputs) if all_outputs else {}

    # 3. 逐任务判定并写回（含无正式输出表的任务 → 无校验结果）
    now = datetime.now()
    changed = 0
    for task in tasks:
        outputs = task_outputs.get((task.project_name, task.task_name))
        results = []
        if outputs:
            for full in outputs:
                db_name, _, table_name = full.partition(".")
                record = latest_map.get((db_name, table_name))
                if record is not None:
                    results.append(record.result)
        if not results:
            new_value = CHECK_RESULT_NONE
        elif all(r == CHECK_RESULT_PASSED for r in results):
            new_value = CHECK_RESULT_PASSED
        else:
            new_value = CHECK_RESULT_FAILED
        if task.check_result != new_value:
            task.check_result = new_value
            task.updated_by = operator
            task.updated_at = now
            changed += 1
    sdb.commit()
    return changed
