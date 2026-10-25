"""b07 血缘管理服务：血缘边列表、脚本解析入库、重建、工作流聚合与删除。"""

from datetime import datetime
from typing import List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.models.b07_lineage import B07Lineage, TABLE_TYPE_FORMAL
from app.utils import lineage_parser


def _apply_default_db(edges: List[dict], default_db: Optional[str]) -> List[dict]:
    """为无库名前缀的正式表补上默认库名（幂等）。"""
    if not default_db:
        return edges
    default_db = default_db.strip()
    if not default_db:
        return edges
    out = []
    for e in edges:
        e = dict(e)
        src = e.get("source") or ""
        tgt = e.get("target") or ""
        if e.get("sourceType") == TABLE_TYPE_FORMAL and src and "." not in src:
            e["source"] = f"{default_db}.{src}"
        if e.get("targetType") == TABLE_TYPE_FORMAL and tgt and "." not in tgt:
            e["target"] = f"{default_db}.{tgt}"
        out.append(e)
    return out


def list_lineages(
    sdb: Session,
    space_id: int,
    workflow: Optional[str] = None,
    keyword: Optional[str] = None,
    table_type: Optional[str] = None,
) -> List[B07Lineage]:
    """列出血缘边（含筛选）；临时表不默认展示时由前端按图例开关控制。"""
    q = sdb.query(B07Lineage).filter(
        B07Lineage.space_id == space_id, B07Lineage.deleted_at.is_(None)
    )
    if workflow:
        q = q.filter(B07Lineage.workflow_name == workflow)
    if keyword:
        like = f"%{keyword}%"
        q = q.filter(
            (B07Lineage.input_table.like(like)) | (B07Lineage.output_table.like(like))
        )
    if table_type:
        q = q.filter(
            (B07Lineage.input_table_type == table_type)
            | (B07Lineage.output_table_type == table_type)
        )
    return q.order_by(B07Lineage.id.asc()).all()


def parse_task_uri(task_uri: str) -> tuple[Optional[str], Optional[str]]:
    """从 task_uri（格式 `space_name://task_name@workflow_name`）解析出 (task_name, workflow_name)。

    解析失败（格式不符）时返回 (None, None)，由调用方决定降级处理。
    """
    if not task_uri:
        return (None, None)
    right = task_uri.split("://", 1)[1] if "://" in task_uri else task_uri
    if "@" in right:
        task_name, workflow_name = right.rsplit("@", 1)
    else:
        task_name, workflow_name = right, None
    return (task_name or None, workflow_name or None)


def _aggregate_task_tables(rows: List[B07Lineage]) -> dict:
    """将一组血缘边聚合为去重的输入/输出表清单（含表类型）。

    返回 {input_tables: [TableRef], output_tables: [TableRef]}。
    """
    result: dict = {"input_tables": [], "output_tables": []}
    seen_in, seen_out = set(), set()
    for r in rows:
        if r.input_table and (r.input_table, r.input_table_type) not in seen_in:
            seen_in.add((r.input_table, r.input_table_type))
            result["input_tables"].append(
                {"table": r.input_table, "type": r.input_table_type}
            )
        if r.output_table and (r.output_table, r.output_table_type) not in seen_out:
            seen_out.add((r.output_table, r.output_table_type))
            result["output_tables"].append(
                {"table": r.output_table, "type": r.output_table_type}
            )
    return result


def get_lineages_by_project_task(
    sdb: Session, space_id: int, dw_project_space: str, task_name: str
) -> dict:
    """按（数仓项目空间 + 任务名称）聚合该任务的输入/输出表清单（去重，跨工作流合并）。

    关联键：b07_lineage.project_name = dw_project_space AND b07_lineage.task_name = task_name，
    不限 workflow_name（同一数仓项目空间内同名任务跨工作流合并）；临时表一并返回、由前端按类型过滤。
    返回 {input_tables: [TableRef], output_tables: [TableRef]}，无记录时返回空清单。
    """
    rows = (
        sdb.query(B07Lineage)
        .filter(
            B07Lineage.space_id == space_id,
            B07Lineage.project_name == dw_project_space,
            B07Lineage.task_name == task_name,
            B07Lineage.deleted_at.is_(None),
        )
        .all()
    )
    return _aggregate_task_tables(rows)


def get_lineages_by_task_uri(
    sdb: Session, space_id: int, task_uri: str
) -> dict:
    """兼容旧调用：按 task_uri 解析出的 (task_name, workflow_name) 聚合输入/输出表清单（去重）。

    新版主路径为 get_lineages_by_project_task（数仓项目空间 + 任务名称），本函数仅作过渡兼容。
    """
    task_name, workflow_name = parse_task_uri(task_uri)
    if not task_name or not workflow_name:
        return {"input_tables": [], "output_tables": []}
    rows = (
        sdb.query(B07Lineage)
        .filter(
            B07Lineage.space_id == space_id,
            B07Lineage.task_name == task_name,
            B07Lineage.workflow_name == workflow_name,
            B07Lineage.deleted_at.is_(None),
        )
        .all()
    )
    return _aggregate_task_tables(rows)


def get_lineage(sdb: Session, space_id: int, lineage_id: int) -> B07Lineage:
    obj = (
        sdb.query(B07Lineage)
        .filter(
            B07Lineage.id == lineage_id,
            B07Lineage.space_id == space_id,
            B07Lineage.deleted_at.is_(None),
        )
        .first()
    )
    if not obj:
        raise NotFoundError(f"血缘边不存在: {lineage_id}")
    return obj


def delete_lineage(sdb: Session, space_id: int, lineage_id: int, operator: str) -> None:
    obj = get_lineage(sdb, space_id, lineage_id)
    now = datetime.now()
    obj.deleted_at = now
    obj.updated_by = operator
    obj.updated_at = now
    sdb.commit()


def delete_workflow_lineages(sdb: Session, space_id: int, workflow: str, operator: str) -> int:
    """逻辑删除某工作流的全部血缘边，返回删除条数（避免逐条删除的 N+1 请求）。"""
    now = datetime.now()
    cnt = (
        sdb.query(B07Lineage)
        .filter(
            B07Lineage.space_id == space_id,
            B07Lineage.workflow_name == workflow,
            B07Lineage.deleted_at.is_(None),
        )
        .update(
            {
                B07Lineage.deleted_at: now,
                B07Lineage.updated_by: operator,
                B07Lineage.updated_at: now,
            }
        )
    )
    sdb.commit()
    return cnt


def parse_script(code: str, lang: Optional[str] = None) -> List[dict]:
    """解析 SQL/PySpark 脚本为血缘边列表（预览）。"""
    return lineage_parser.parse_text(code or "", lang)


def import_lineages(
    sdb: Session, space_id: int, payload, operator: str
) -> dict:
    """按工作流入库：add=仅插入；rebuild=先逻辑删除该工作流旧边再插入。

    edges 可直接传入（前端预览后回传），也可传 code 由后端解析。
    """
    if payload.edges:
        raw = [e.model_dump() for e in payload.edges]
        # 统一字段名：前端传入 source/target/source_type/target_type
        edges = [
            {
                "source": r.get("source"),
                "target": r.get("target"),
                "sourceType": r.get("source_type"),
                "targetType": r.get("target_type"),
            }
            for r in raw
        ]
    elif payload.code:
        edges = parse_script(payload.code, payload.lang)
    else:
        raise ValueError("edges 与 code 不能同时为空")

    edges = _apply_default_db(edges, payload.default_db)
    parsed = len(edges)
    # 仅保留 source 与 target 均非空的边
    edges = [e for e in edges if e.get("source") and e.get("target")]
    dropped = parsed - len(edges)

    if payload.mode == "rebuild":
        now = datetime.now()
        sdb.query(B07Lineage).filter(
            B07Lineage.space_id == space_id,
            B07Lineage.workflow_name == payload.workflow,
            B07Lineage.deleted_at.is_(None),
        ).update(
            {
                B07Lineage.deleted_at: now,
                B07Lineage.updated_by: operator,
                B07Lineage.updated_at: now,
            }
        )

    now = datetime.now()
    for e in edges:
        sdb.add(
            B07Lineage(
                space_id=space_id,
                workflow_name=payload.workflow,
                task_name=payload.task,
                task_type=payload.task_type,
                project_name=payload.project,
                script_name=payload.script_name,
                input_table=e["source"],
                input_table_type=e.get("sourceType"),
                output_table=e["target"],
                output_table_type=e.get("targetType"),
                created_by=operator,
                created_at=now,
                updated_by=operator,
                updated_at=now,
            )
        )
    sdb.commit()
    return {
        "mode": payload.mode,
        "workflow": payload.workflow,
        "inserted": len(edges),
        "parsed": parsed,
        "dropped": dropped,
    }


def list_workflows(sdb: Session, space_id: int) -> List[dict]:
    """聚合工作流：涉及表数、入口表（写入但未被本工作流读取的表）。"""
    rows = (
        sdb.query(B07Lineage)
        .filter(B07Lineage.space_id == space_id, B07Lineage.deleted_at.is_(None))
        .all()
    )
    wf_sources: dict[str, set] = {}
    wf_targets: dict[str, set] = {}
    for r in rows:
        wf = r.workflow_name or ""
        if not wf:
            continue
        wf_sources.setdefault(wf, set()).add(r.input_table)
        wf_targets.setdefault(wf, set()).add(r.output_table)
    result = []
    for wf, targets in wf_targets.items():
        sources = wf_sources.get(wf, set())
        focus = next((t for t in targets if t not in sources), None)
        if focus is None and targets:
            focus = next(iter(targets))
        result.append(
            {
                "name": wf,
                "count": len(sources | targets),
                "focus": focus,
            }
        )
    return result


def get_workflow_options(sdb: Session, space_id: int, workflow: str) -> dict:
    """某工作流下可选的任务/脚本/任务类型/项目（重建预填用）。"""
    rows = (
        sdb.query(
            B07Lineage.task_name,
            B07Lineage.script_name,
            B07Lineage.task_type,
            B07Lineage.project_name,
        )
        .filter(
            B07Lineage.space_id == space_id,
            B07Lineage.workflow_name == workflow,
            B07Lineage.deleted_at.is_(None),
        )
        .all()
    )
    tasks, scripts, task_types, projects = set(), set(), set(), set()
    for r in rows:
        if r.task_name:
            tasks.add(r.task_name)
        if r.script_name:
            scripts.add(r.script_name)
        if r.task_type:
            task_types.add(r.task_type)
        if r.project_name:
            projects.add(r.project_name)
    return {
        "workflow": workflow,
        "tasks": sorted(tasks),
        "scripts": sorted(scripts),
        "task_types": sorted(task_types),
        "projects": sorted(projects),
    }
