"""b04 任务迁移管理服务：场景、任务台账（基础表+扩展表）、迁移模板、排查备注、自定义台账与导入导出。

依据《任务迁移-任务台账数据模型重构需求》V1.0（D1~D7）：
- 任务主体 15 业务字段 + 5 维独立状态（替代旧状态机）；
- 空间级迁移模板驱动字段选择 / 必填 / 排序 / 列表展示 / 导入；
- 扩展字段按空间模板动态加列 f_1…n（b04_task_ext）。
"""

import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from fastapi import UploadFile
from sqlalchemy import func, or_, text
from sqlalchemy.orm import Session

from app.core.exceptions import BizError, NotFoundError
from app.database import ensure_task_ext_columns
from app.models.b04_task_migration import (
    NOTE_KIND_CHECK_RESULT,
    NOTE_KIND_TROUBLESHOOT,
    CHECK_RESULT_NONE,
    CHECK_RESULTS,
    B04MigrationTemplate,
    B04SavedView,
    B04SavedViewMember,
    B04Scenario,
    B04Task,
    B04TaskExt,
    B04TaskNote,
)
from app.models.b06_tag import B06TaskTag
from app.services import b06_tag as tag_svc
from app.schemas.b04_task_migration import (
    NOTE_KINDS,
    STATUS_DIMENSIONS,
    ScenarioCreate,
    ScenarioUpdate,
    SavedViewCreate,
    SavedViewUpdate,
    TaskUpdate,
)
from app.utils import excel as xl

# 扩展列名白名单：仅允许 f_<数字>，防止动态 DDL/SQL 注入（需求 §9.4）
_EXT_COL_RE = re.compile(r"^f_[0-9]+$")

# 任务导入单文件行数上限（b04 专用，5 万行；不影响 b03 的 xl.MAX_IMPORT_ROWS=5000）
MAX_TASK_IMPORT_ROWS = 50000

# 导入行级必填字段（B04-08：仅项目名称、任务名称不允许为空，其余字段可留空落 NULL；
# 模板中的「必选」配置保留，仅导入校验放宽）
IMPORT_REQUIRED_FIELDS = {"project_name", "task_name"}

# ── 基础表字段模板元数据：(field_key, 中文名, 是否锁定必填, 列表展示默认值) ──
# check_result（数据校验结果）为模板必选字段，但列表展示默认关闭（需求：列表显示默认：否），
# 其值由数据校验结果导入按血缘输出表自动刷新，见《数据校验-数据校验结果导入与刷新需求》。
BASE_TEMPLATE_FIELDS = [
    ("project_name", "项目名称", True, True),
    ("task_name", "任务名称", True, True),
    ("migration_owner", "迁移负责人", True, True),
    ("active_status", "任务活跃状态", True, True),
    ("migration_status", "迁移状态", True, True),
    ("dualrun_status", "双跑调度状态", True, True),
    ("check_status", "数据校验状态", True, True),
    ("acceptance_status", "客户验收状态", True, True),
    ("workflow_name", "工作流名称", False, True),
    ("env", "归属环境", False, True),
    ("business", "归属业务", False, True),
    ("task_type", "任务类型", False, True),
    ("remark", "备注信息", False, True),
    ("check_result", "数据校验结果", True, False),
]
_BASE_FIELD_KEYS = {k for k, _, _, _ in BASE_TEMPLATE_FIELDS}
_REQUIRED_BASE_FIELDS = {k for k, _, req, _ in BASE_TEMPLATE_FIELDS if req}


def build_task_uri(project_name: str, task_name: str, workflow_name: str) -> str:
    """任务URI：project_name://task_name@workflow_name（场景内唯一）。"""
    return f"{project_name}://{task_name}@{workflow_name}"


# ── 空间级迁移模板 ──
def build_default_template_config() -> dict:
    """默认模板：14 基础字段全选、9 项必填锁定、顺序 1..14、无扩展字段。

    其中「数据校验结果」为必选字段但列表展示默认关闭（需求：列表显示默认：否）。
    """
    fields = []
    for i, (key, label, req, in_list) in enumerate(BASE_TEMPLATE_FIELDS, start=1):
        fields.append(
            {
                "field_key": key,
                "field_label": label,
                "field_source": "base",
                "is_required": req,
                "display_in_list": in_list,
                "order": i,
                "ext_type": None,
                "enum_options": None,
            }
        )
    return {"fields": fields}


def get_template(sdb: Session, space_id: int) -> Optional[B04MigrationTemplate]:
    return (
        sdb.query(B04MigrationTemplate)
        .filter(
            B04MigrationTemplate.space_id == space_id,
            B04MigrationTemplate.deleted_at.is_(None),
        )
        .first()
    )


def seed_default_template(sdb: Session, space_id: int, operator: str) -> B04MigrationTemplate:
    """空间初始化时若无模板，注入默认模板（保证存量/新空间均可导入，决策③）。

    存量模板升级：早前版本模板缺少「数据校验结果」等后增必选字段时，按默认定义补齐，
    避免导入因「模板必填字段缺失」失败（见《数据校验-数据校验结果导入与刷新需求》）。
    """
    existing = get_template(sdb, space_id)
    if existing:
        _upgrade_template_fields(sdb, existing, operator)
        return existing
    obj = B04MigrationTemplate(
        space_id=space_id,
        name="默认迁移模板",
        config_json=build_default_template_config(),
        created_by=operator,
    )
    sdb.add(obj)
    sdb.commit()
    sdb.refresh(obj)
    return obj


def _upgrade_template_fields(
    sdb: Session, template: B04MigrationTemplate, operator: str
) -> bool:
    """存量模板补齐后增的基础字段（幂等）：缺失字段按 BASE_TEMPLATE_FIELDS 默认定义追加。"""
    config = template.config_json or {}
    fields = config.get("fields") or []
    present = {f.get("field_key") for f in fields}
    max_order = max((f.get("order", 0) for f in fields), default=0)
    added = False
    for key, label, req, in_list in BASE_TEMPLATE_FIELDS:
        if key in present:
            continue
        max_order += 1
        fields.append(
            {
                "field_key": key,
                "field_label": label,
                "field_source": "base",
                "is_required": req,
                "display_in_list": in_list,
                "order": max_order,
                "ext_type": None,
                "enum_options": None,
            }
        )
        added = True
    if added:
        template.config_json = {"fields": fields}
        template.updated_by = operator
        template.updated_at = datetime.now()
        sdb.commit()
    return added


def _ordered_ext_fields(config: dict) -> List[dict]:
    ext = [f for f in config.get("fields", []) if f.get("field_source") == "extension"]
    ext.sort(key=lambda f: f.get("order", 0))
    return ext


def upsert_template(
    sdb: Session, space_id: int, payload, operator: str
) -> B04MigrationTemplate:
    """保存/更新空间级迁移模板，并按扩展字段定义动态加列 f_n。"""
    config = payload.config_json
    ordered_ext = _ordered_ext_fields(config)
    ext_defs = [
        {"name": f"f_{i + 1}", "ext_type": f.get("ext_type") or "string"}
        for i, f in enumerate(ordered_ext)
    ]
    # 动态加列 / 删列（开发态清空重建多余列）
    engine = sdb.get_bind()
    ensure_task_ext_columns(engine, ext_defs)

    obj = get_template(sdb, space_id)
    if obj:
        obj.name = payload.name
        obj.config_json = config
        obj.updated_by = operator
        obj.updated_at = datetime.now()
    else:
        obj = B04MigrationTemplate(
            space_id=space_id,
            name=payload.name,
            config_json=config,
            created_by=operator,
        )
        sdb.add(obj)
    sdb.commit()
    sdb.refresh(obj)
    return obj


# ── 扩展字段读写（动态列，白名单防注入） ──
def get_ext_map(sdb: Session, task_ids: List[int]) -> Dict[int, Dict[str, str]]:
    """批量读取任务扩展字段，返回 {task_id: {f_n: value}}。"""
    if not task_ids:
        return {}
    rows = (
        sdb.execute(
            text("SELECT * FROM b04_task_ext WHERE task_id IN :ids"),
            {"ids": tuple(task_ids)},
        )
        .mappings()
        .all()
    )
    out: Dict[int, Dict[str, str]] = {}
    for r in rows:
        d = dict(r)
        tid = d.pop("task_id", None)
        out[tid] = {k: v for k, v in d.items() if _EXT_COL_RE.match(k)}
    return out


def _upsert_ext(sdb: Session, task_id: int, ext_values: Dict[str, Optional[str]]) -> None:
    cols = {c: v for c, v in ext_values.items() if _EXT_COL_RE.match(c)}
    if not cols:
        return
    exists = (
        sdb.execute(text("SELECT 1 FROM b04_task_ext WHERE task_id=:t"), {"t": task_id}).first()
    )
    if exists:
        sets = ", ".join(f"`{c}`=:c_{c}" for c in cols)
        params = {"t": task_id, **{f"c_{c}": cols[c] for c in cols}}
        sdb.execute(text(f"UPDATE b04_task_ext SET {sets} WHERE task_id=:t"), params)
    else:
        names = ", ".join(f"`{c}`" for c in cols)
        ph = ", ".join(f":c_{c}" for c in cols)
        params = {"t": task_id, **{f"c_{c}": cols[c] for c in cols}}
        sdb.execute(
            text(f"INSERT INTO b04_task_ext (task_id, {names}) VALUES (:t, {ph})"), params
        )


# ── 场景 ──
def get_scenario(sdb: Session, space_id: int, scenario_id: int) -> B04Scenario:
    obj = (
        sdb.query(B04Scenario)
        .filter(
            B04Scenario.id == scenario_id,
            B04Scenario.space_id == space_id,
            B04Scenario.deleted_at.is_(None),
        )
        .first()
    )
    if not obj:
        raise NotFoundError(f"任务迁移场景不存在: {scenario_id}")
    return obj


def list_scenarios(sdb: Session, space_id: int) -> List[dict]:
    rows = (
        sdb.query(B04Scenario)
        .filter(B04Scenario.space_id == space_id, B04Scenario.deleted_at.is_(None))
        .order_by(B04Scenario.id.desc())
        .all()
    )
    counts = dict(
        sdb.query(B04Task.scenario_id, func.count(B04Task.id))
        .filter(B04Task.space_id == space_id, B04Task.deleted_at.is_(None))
        .group_by(B04Task.scenario_id)
        .all()
    )
    return [
        {
            "id": r.id,
            "name": r.name,
            "remark": r.remark,
            "task_count": counts.get(r.id, 0),
            "created_by": r.created_by,
            "created_at": r.created_at,
        }
        for r in rows
    ]


def create_scenario(
    sdb: Session, space_id: int, payload: ScenarioCreate, operator: str
) -> B04Scenario:
    if (
        sdb.query(B04Scenario)
        .filter(
            B04Scenario.space_id == space_id,
            B04Scenario.name == payload.name,
            B04Scenario.deleted_at.is_(None),
        )
        .first()
    ):
        raise BizError(f"场景名称已存在: {payload.name}")
    obj = B04Scenario(
        space_id=space_id, name=payload.name, remark=payload.remark, created_by=operator
    )
    sdb.add(obj)
    sdb.commit()
    sdb.refresh(obj)
    return obj


def update_scenario(
    sdb: Session, space_id: int, scenario_id: int, payload: ScenarioUpdate, operator: str
) -> B04Scenario:
    obj = get_scenario(sdb, space_id, scenario_id)
    data = payload.model_dump(exclude_unset=True)
    if "name" in data and data["name"] != obj.name:
        if (
            sdb.query(B04Scenario)
            .filter(
                B04Scenario.space_id == space_id,
                B04Scenario.name == data["name"],
                B04Scenario.id != scenario_id,
                B04Scenario.deleted_at.is_(None),
            )
            .first()
        ):
            raise BizError(f"场景名称已存在: {data['name']}")
    for field, value in data.items():
        setattr(obj, field, value)
    obj.updated_by = operator
    obj.updated_at = datetime.now()
    sdb.commit()
    sdb.refresh(obj)
    return obj


def delete_scenario(sdb: Session, space_id: int, scenario_id: int) -> None:
    """删除场景：级联逻辑删除任务、备注与自定义台账。"""
    obj = get_scenario(sdb, space_id, scenario_id)
    now = datetime.now()
    obj.deleted_at = now
    sdb.query(B04Task).filter(
        B04Task.space_id == space_id,
        B04Task.scenario_id == scenario_id,
        B04Task.deleted_at.is_(None),
    ).update({B04Task.deleted_at: now})
    sdb.query(B04TaskNote).filter(
        B04TaskNote.space_id == space_id,
        B04TaskNote.task_id.in_(
            sdb.query(B04Task.id).filter(
                B04Task.space_id == space_id,
                B04Task.scenario_id == scenario_id,
                B04Task.deleted_at.is_(None),
            )
        ),
        B04TaskNote.deleted_at.is_(None),
    ).update({B04TaskNote.deleted_at: now})
    sdb.query(B04SavedView).filter(
        B04SavedView.space_id == space_id,
        B04SavedView.scenario_id == scenario_id,
        B04SavedView.deleted_at.is_(None),
    ).update({B04SavedView.deleted_at: now})
    sdb.commit()


# ── 任务台账 ──
def _task_query(
    sdb: Session,
    space_id: int,
    scenario_id: int,
    keyword: Optional[str] = None,
    workflow_name: Optional[str] = None,
    project_name: Optional[str] = None,
    migration_owner: Optional[str] = None,
    active_status: Optional[str] = None,
    migration_status: Optional[str] = None,
    dualrun_status: Optional[str] = None,
    check_status: Optional[str] = None,
    acceptance_status: Optional[str] = None,
    tag_ids: Optional[List[int]] = None,
    tag_match: str = "all",
    ext_filters: Optional[Dict[str, str]] = None,
):
    q = sdb.query(B04Task).filter(
        B04Task.space_id == space_id,
        B04Task.scenario_id == scenario_id,
        B04Task.deleted_at.is_(None),
    )
    if keyword:
        like = f"%{keyword}%"
        q = q.filter(or_(B04Task.task_name.like(like), B04Task.task_uri.like(like)))
    if workflow_name:
        q = q.filter(B04Task.workflow_name == workflow_name)
    if project_name:
        q = q.filter(B04Task.project_name == project_name)
    if migration_owner:
        q = q.filter(B04Task.migration_owner == migration_owner)
    if active_status:
        q = q.filter(B04Task.active_status == active_status)
    if migration_status:
        q = q.filter(B04Task.migration_status == migration_status)
    if dualrun_status:
        q = q.filter(B04Task.dualrun_status == dualrun_status)
    if check_status:
        q = q.filter(B04Task.check_status == check_status)
    if acceptance_status:
        q = q.filter(B04Task.acceptance_status == acceptance_status)
    # 扩展字段筛选（枚举类已建索引）：键必须经白名单
    ext_params = {}
    if ext_filters:
        for col, val in ext_filters.items():
            if not _EXT_COL_RE.match(col) or val is None:
                continue
            q = q.filter(
                text(
                    f"EXISTS(SELECT 1 FROM b04_task_ext e WHERE e.task_id=b04_task.id "
                    f"AND e.`{col}`=:e_{col})"
                )
            )
            ext_params[f"e_{col}"] = val
        if ext_params:
            q = q.params(**ext_params)
    if tag_ids:
        if tag_match == "all":
            tag_count = (
                sdb.query(func.count(B06TaskTag.id))
                .filter(
                    B06TaskTag.task_id == B04Task.id,
                    B06TaskTag.tag_id.in_(tag_ids),
                    B06TaskTag.deleted_at.is_(None),
                )
                .correlate(B04Task)
                .scalar_subquery()
            )
            q = q.filter(tag_count == len(tag_ids))
        else:
            subq = sdb.query(B06TaskTag.task_id).filter(
                B06TaskTag.space_id == space_id,
                B06TaskTag.tag_id.in_(tag_ids),
                B06TaskTag.deleted_at.is_(None),
            )
            q = q.filter(B04Task.id.in_(subq))
    return q


def list_tasks(
    sdb: Session,
    space_id: int,
    scenario_id: int,
    page: int,
    page_size: int,
    keyword: Optional[str] = None,
    workflow_name: Optional[str] = None,
    project_name: Optional[str] = None,
    migration_owner: Optional[str] = None,
    active_status: Optional[str] = None,
    migration_status: Optional[str] = None,
    dualrun_status: Optional[str] = None,
    check_status: Optional[str] = None,
    acceptance_status: Optional[str] = None,
    tag_ids: Optional[List[int]] = None,
    tag_match: str = "all",
    ext_filters: Optional[Dict[str, str]] = None,
) -> Tuple[List[B04Task], int]:
    get_scenario(sdb, space_id, scenario_id)
    q = _task_query(
        sdb,
        space_id,
        scenario_id,
        keyword,
        workflow_name,
        project_name,
        migration_owner,
        active_status,
        migration_status,
        dualrun_status,
        check_status,
        acceptance_status,
        tag_ids,
        tag_match,
        ext_filters,
    )
    total = q.count()
    rows = (
        q.order_by(B04Task.id.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return rows, total


def get_task(sdb: Session, space_id: int, task_id: int) -> B04Task:
    obj = (
        sdb.query(B04Task)
        .filter(
            B04Task.id == task_id,
            B04Task.space_id == space_id,
            B04Task.deleted_at.is_(None),
        )
        .first()
    )
    if not obj:
        raise NotFoundError(f"任务不存在: {task_id}")
    return obj


def get_task_by_key(sdb: Session, space_id: int, project_name: str, task_name: str) -> B04Task:
    """按（项目名称 + 任务名称）定位任务（D5：血缘任务名直达任务详情）。

    任务名在同一项目空间内唯一；未找到返回 None（由路由层转 404/业务提示）。
    """
    obj = (
        sdb.query(B04Task)
        .filter(
            B04Task.space_id == space_id,
            B04Task.project_name == project_name,
            B04Task.task_name == task_name,
            B04Task.deleted_at.is_(None),
        )
        .first()
    )
    return obj


def update_task(
    sdb: Session, space_id: int, task_id: int, payload: TaskUpdate, operator: str
) -> B04Task:
    obj = get_task(sdb, space_id, task_id)
    data = payload.model_dump(exclude_unset=True)
    ext_values = data.pop("ext", None)
    for field, value in data.items():
        setattr(obj, field, value)
    obj.updated_by = operator
    obj.updated_at = datetime.now()
    if ext_values:
        _upsert_ext(sdb, task_id, ext_values)
    sdb.commit()
    sdb.refresh(obj)
    return obj


def update_task_status(
    sdb: Session, space_id: int, task_id: int, payload, operator: str
) -> B04Task:
    """5 维状态独立更新：仅更新 payload 中提供的维度（互不约束，D1）。"""
    obj = get_task(sdb, space_id, task_id)
    data = payload.model_dump(exclude_unset=True)
    applied = False
    for dim, value in data.items():
        if value is not None and dim in STATUS_DIMENSIONS:
            if value not in STATUS_DIMENSIONS[dim]:
                raise BizError(f"非法的{dim}取值: {value}")
            setattr(obj, dim, value)
            applied = True
    if not applied:
        raise BizError("未提供任何有效的状态维度")
    obj.updated_by = operator
    obj.updated_at = datetime.now()
    sdb.commit()
    sdb.refresh(obj)
    return obj


def batch_update_task_status(
    sdb: Session,
    space_id: int,
    ids: List[int],
    dimension: str,
    value: str,
    operator: str,
) -> int:
    """批量更新某一维度的状态。"""
    if dimension not in STATUS_DIMENSIONS:
        raise BizError(f"非法的状态维度: {dimension}")
    if value not in STATUS_DIMENSIONS[dimension]:
        raise BizError(f"维度 {dimension} 的非法取值: {value}")
    rows = (
        sdb.query(B04Task)
        .filter(
            B04Task.space_id == space_id,
            B04Task.id.in_(ids),
            B04Task.deleted_at.is_(None),
        )
        .all()
    )
    if not rows:
        raise NotFoundError("未找到可更新的任务")
    now = datetime.now()
    for r in rows:
        setattr(r, dimension, value)
        r.updated_by = operator
        r.updated_at = now
    sdb.commit()
    return len(rows)


# ── 导入 / 导出（模板驱动，D7） ──
def import_tasks(
    sdb: Session,
    space_id: int,
    scenario_id: int,
    file: UploadFile,
    operator: str,
    mode: str = "overwrite",
) -> dict:
    """按空间模板导入任务台账（强制先配模板，D7）。

    mode=overwrite：按 task_uri 覆盖更新已存在行；
    mode=incremental：跳过已存在行。
    B04-08：行级仅强制 项目名称/任务名称 非空，其余字段留空落 NULL（模板必选配置保留）。
    """
    get_scenario(sdb, space_id, scenario_id)
    if mode not in ("overwrite", "incremental"):
        raise BizError("非法的导入模式")
    template = get_template(sdb, space_id)
    if not template:
        raise BizError("请先在空间内配置迁移模板后再导入")
    config = template.config_json
    fields = config.get("fields", [])
    if not fields:
        raise BizError("迁移模板未配置任何字段")

    ordered_ext = _ordered_ext_fields(config)
    ext_label_to_col = {f["field_label"]: f"f_{i + 1}" for i, f in enumerate(ordered_ext)}

    xl.check_import_file(file.filename)
    content = file.file.read()
    headers, rows, line_nos = xl.read_tabular(content, file.filename or "")
    if len(rows) > MAX_TASK_IMPORT_ROWS:
        raise BizError(f"单次导入不得超过 {MAX_TASK_IMPORT_ROWS} 行")

    # 必填字段须出现在 Excel 表头中（模板下载生成的文件必然满足）
    selected_labels = {f["field_label"] for f in fields}
    for req_field in (f for f in fields if f.get("is_required")):
        if req_field["field_label"] not in selected_labels:
            raise BizError(f"模板必填字段缺失: {req_field['field_label']}")

    inserted = updated = skipped = 0
    errors = []
    enum_changes = False  # 是否因 D6 动态收集枚举新增值而需更新模板
    now = datetime.now()

    # 预取场景内已有任务（task_uri → task），避免 5 万行逐行 SELECT
    existing_tasks: Dict[str, B04Task] = {
        t.task_uri: t
        for t in sdb.query(B04Task)
        .filter(
            B04Task.scenario_id == scenario_id,
            B04Task.deleted_at.is_(None),
        )
        .all()
    }
    # 文件内新建任务（task_uri → (base_values, ext_values)），重复行后者覆盖前者
    new_rows: Dict[str, Tuple[Dict[str, Optional[str]], Dict[str, Optional[str]]]] = {}

    for row, line_no in zip(rows, line_nos):
        try:
            base_values: Dict[str, Optional[str]] = {}
            ext_values: Dict[str, Optional[str]] = {}
            for f in fields:
                label = f["field_label"]
                raw = xl._to_str(row.get(label))
                # B04-08：行级仅强制 项目名称/任务名称 非空，其余字段（含模板必选项）允许留空
                if f["field_key"] in IMPORT_REQUIRED_FIELDS and not raw:
                    raise ValueError(f"必填字段[{label}]缺失")
                if f["field_source"] == "extension":
                    col = ext_label_to_col[label]
                    ext_values[col] = raw or None
                    # D6：枚举类扩展字段首次导入动态收集新值
                    if f.get("ext_type") == "enum" and raw:
                        opts = f.get("enum_options") or []
                        if not any(o.get("code") == raw for o in opts):
                            opts.append({"code": raw, "label": raw})
                            f["enum_options"] = opts
                            enum_changes = True
                else:
                    key = f["field_key"]
                    if key in STATUS_DIMENSIONS:
                        if raw:
                            if raw not in STATUS_DIMENSIONS[key]:
                                raise ValueError(f"[{label}]非法取值: {raw}")
                            base_values[key] = raw
                        else:
                            base_values[key] = None
                    elif key == "check_result":
                        # 数据校验结果：通过/不通过/无校验结果；留空落 NULL（B04-08 导入放宽）
                        if raw and raw not in CHECK_RESULTS:
                            raise ValueError(f"[{label}]非法取值: {raw}")
                        base_values[key] = raw or None
                    else:
                        base_values[key] = raw or None

            # 互填规则（§3.3）：工作流名称/任务名称不能全空
            wn = base_values.get("workflow_name") or ""
            tn = base_values.get("task_name") or ""
            if not wn and not tn:
                raise ValueError("工作流名称与任务名称不能都为空")
            if not tn:
                base_values["task_name"] = wn
            if not wn:
                base_values["workflow_name"] = tn
            pn = base_values.get("project_name") or "default"
            uri = build_task_uri(pn, base_values["task_name"], base_values["workflow_name"])

            existing = existing_tasks.get(uri)
            if existing is not None:
                if mode == "incremental":
                    skipped += 1
                    continue
                for field, value in base_values.items():
                    setattr(existing, field, value)
                existing.updated_by = operator
                existing.updated_at = now
                _upsert_ext(sdb, existing.id, ext_values)
                updated += 1
            else:
                # 文件内同一 task_uri 重复行：后者覆盖前者（与 b05 导入去重口径一致）
                new_rows[uri] = (base_values, ext_values)
        except ValueError as exc:
            errors.append({"row": line_no, "message": str(exc)})

    # 批量插入新任务（一次 add_all + flush），再按 ID 补扩展字段
    new_objs: List[Tuple[B04Task, Dict[str, Optional[str]]]] = []
    for uri, (base_values, ext_values) in new_rows.items():
        obj = B04Task(
            space_id=space_id,
            scenario_id=scenario_id,
            task_uri=uri,
            created_by=operator,
            **base_values,
        )
        sdb.add(obj)
        new_objs.append((obj, ext_values))
    if new_objs:
        sdb.flush()
        for obj, ext_values in new_objs:
            _upsert_ext(sdb, obj.id, ext_values)
            inserted += 1

    # D6：若导入过程中收集到新的枚举值，回写模板
    if enum_changes:
        template.config_json = config
        sdb.add(template) if template not in sdb.new else None
        sdb.commit()
    sdb.commit()
    return {"inserted": inserted, "updated": updated, "skipped": skipped, "errors": errors}


def _build_export_xlsx(sdb: Session, rows: List[B04Task], config: dict) -> bytes:
    """按模板字段导出 xlsx（含扩展字段，f_n 经模板映射中文名）。"""
    fields = config.get("fields", [])
    ordered_ext = _ordered_ext_fields(config)
    ext_col_for_label = {f["field_label"]: f"f_{i + 1}" for i, f in enumerate(ordered_ext)}
    headers = [f["field_label"] for f in fields]
    ext_map = get_ext_map(sdb, [r.id for r in rows])
    data = []
    for r in rows:
        row = []
        for f in fields:
            if f["field_source"] == "extension":
                col = ext_col_for_label[f["field_label"]]
                row.append(ext_map.get(r.id, {}).get(col) or "")
            else:
                val = getattr(r, f["field_key"], "")
                row.append(val if val is not None else "")
        data.append(row)
    widths = [18] * len(headers)
    return xl.make_xlsx(headers, data, widths)


def export_tasks(
    sdb: Session,
    space_id: int,
    scenario_id: int,
    keyword: Optional[str] = None,
    workflow_name: Optional[str] = None,
    project_name: Optional[str] = None,
    migration_owner: Optional[str] = None,
    active_status: Optional[str] = None,
    migration_status: Optional[str] = None,
    dualrun_status: Optional[str] = None,
    check_status: Optional[str] = None,
    acceptance_status: Optional[str] = None,
    tag_ids: Optional[List[int]] = None,
    tag_match: str = "all",
) -> bytes:
    rows = (
        _task_query(
            sdb,
            space_id,
            scenario_id,
            keyword,
            workflow_name,
            project_name,
            migration_owner,
            active_status,
            migration_status,
            dualrun_status,
            check_status,
            acceptance_status,
            tag_ids,
            tag_match,
        )
        .order_by(B04Task.id.asc())
        .all()
    )
    template = get_template(sdb, space_id)
    config = template.config_json if template else build_default_template_config()
    return _build_export_xlsx(sdb, rows, config)


def task_template_xlsx(sdb: Session, space_id: int) -> bytes:
    """按空间模板生成导入 Excel（列由模板按 order 生成，D7）。"""
    template = get_template(sdb, space_id)
    if not template:
        raise BizError("请先配置迁移模板后再下载导入模板")
    config = template.config_json
    fields = config.get("fields", [])
    headers = [f["field_label"] for f in fields]
    sample = []
    for f in fields:
        if f["field_source"] == "extension":
            sample.append("")
            continue
        key = f["field_key"]
        if key == "project_name":
            sample.append("default")
        elif key == "task_name":
            sample.append("ods_order_sync")
        elif key == "workflow_name":
            sample.append("etl_workflow")
        elif key == "env":
            sample.append("生产")
        elif key == "migration_owner":
            sample.append("张三")
        elif key in STATUS_DIMENSIONS:
            sample.append(list(STATUS_DIMENSIONS[key])[0])
        elif key == "check_result":
            sample.append(CHECK_RESULT_NONE)
        else:
            sample.append("")
    widths = [18] * len(headers)
    return xl.make_xlsx(headers, [sample], widths)


# ── 排查备注 ──
def list_notes(sdb: Session, space_id: int, task_id: int) -> List[B04TaskNote]:
    get_task(sdb, space_id, task_id)
    return (
        sdb.query(B04TaskNote)
        .filter(
            B04TaskNote.space_id == space_id,
            B04TaskNote.task_id == task_id,
            B04TaskNote.deleted_at.is_(None),
        )
        .order_by(B04TaskNote.id.asc())
        .all()
    )


def create_note(
    sdb: Session, space_id: int, task_id: int, payload, operator: str
) -> B04TaskNote:
    get_task(sdb, space_id, task_id)
    obj = B04TaskNote(
        space_id=space_id,
        task_id=task_id,
        note_kind=payload.note_kind,
        problem_desc=payload.problem_desc,
        cause_analysis=payload.cause_analysis,
        fix_plan=payload.fix_plan,
        created_by=operator,
    )
    sdb.add(obj)
    # 备注不再冗余到 b04_task（latest_note 已移出基础表，D3）
    sdb.commit()
    sdb.refresh(obj)
    return obj


# ── 自定义台账 ──
_ALLOWED_FILTER_KEYS = {
    "keyword",
    "workflow_name",
    "project_name",
    "migration_owner",
    "active_status",
    "migration_status",
    "dualrun_status",
    "check_status",
    "acceptance_status",
}


def _clean_filter_config(config: dict) -> dict:
    out = {k: v for k, v in (config or {}).items() if k in _ALLOWED_FILTER_KEYS and v}
    if config.get("tag_ids"):
        out["tag_ids"] = config["tag_ids"]
    if config.get("tag_match"):
        out["tag_match"] = config["tag_match"]
    return out


def _snapshot_members(sdb: Session, space_id: int, view: B04SavedView, operator: str) -> None:
    """固化台账：按当前筛选条件快照命中任务 ID 为成员。"""
    filters = _clean_filter_config(view.filter_config or {})
    rows = _task_query(sdb, space_id, view.scenario_id, **filters).all()
    now = datetime.now()
    existing = {
        r.task_id: r
        for r in sdb.query(B04SavedViewMember)
        .filter(B04SavedViewMember.view_id == view.id, B04SavedViewMember.space_id == space_id)
        .all()
    }
    for r in rows:
        if r.id in existing:
            existing[r.id].deleted_at = None
            existing[r.id].updated_by = operator
            existing[r.id].updated_at = now
        else:
            sdb.add(
                B04SavedViewMember(
                    space_id=space_id,
                    view_id=view.id,
                    task_id=r.id,
                    created_by=operator,
                )
            )


def _rebuild_members(sdb: Session, space_id: int, view: B04SavedView, operator: str) -> None:
    """重建台账成员：动态模式清空成员；固化模式按筛选快照。"""
    now = datetime.now()
    sdb.query(B04SavedViewMember).filter(
        B04SavedViewMember.view_id == view.id,
        B04SavedViewMember.space_id == space_id,
    ).update({B04SavedViewMember.deleted_at: now})
    if view.view_mode == "fixed":
        _snapshot_members(sdb, space_id, view, operator)


def _set_members_from_ids(
    sdb: Session, space_id: int, view: B04SavedView, task_ids: List[int], operator: str
) -> None:
    """R3：按显式任务 ID 写入/复活固化成员。"""
    if not task_ids:
        return
    valid = {
        r.id
        for r in sdb.query(B04Task.id)
        .filter(
            B04Task.space_id == space_id,
            B04Task.scenario_id == view.scenario_id,
            B04Task.id.in_(task_ids),
        )
        .all()
    }
    now = datetime.now()
    existing = {
        r.task_id: r
        for r in sdb.query(B04SavedViewMember)
        .filter(B04SavedViewMember.view_id == view.id, B04SavedViewMember.space_id == space_id)
        .all()
    }
    for tid in valid:
        if tid in existing:
            existing[tid].deleted_at = None
            existing[tid].updated_by = operator
            existing[tid].updated_at = now
        else:
            sdb.add(
                B04SavedViewMember(
                    space_id=space_id, view_id=view.id, task_id=tid, created_by=operator
                )
            )


def list_saved_views(sdb: Session, space_id: int, scenario_id: int) -> List[dict]:
    get_scenario(sdb, space_id, scenario_id)
    rows = (
        sdb.query(B04SavedView)
        .filter(
            B04SavedView.space_id == space_id,
            B04SavedView.scenario_id == scenario_id,
            B04SavedView.deleted_at.is_(None),
        )
        .order_by(B04SavedView.id.desc())
        .all()
    )
    result = []
    for r in rows:
        filters = _clean_filter_config(r.filter_config or {})
        count = _task_query(sdb, space_id, scenario_id, **filters).count()
        result.append(
            {
                "id": r.id,
                "scenario_id": r.scenario_id,
                "name": r.name,
                "description": r.description,
                "filter_config": r.filter_config,
                "view_mode": r.view_mode,
                "task_count": count,
                "created_by": r.created_by,
                "created_at": r.created_at,
            }
        )
    return result


def create_saved_view(
    sdb: Session, space_id: int, scenario_id: int, payload: SavedViewCreate, operator: str
) -> B04SavedView:
    get_scenario(sdb, space_id, scenario_id)
    if (
        sdb.query(B04SavedView)
        .filter(
            B04SavedView.space_id == space_id,
            B04SavedView.scenario_id == scenario_id,
            B04SavedView.name == payload.name,
            B04SavedView.deleted_at.is_(None),
        )
        .first()
    ):
        raise BizError(f"台账名称已存在: {payload.name}")

    if payload.member_ids:
        obj = B04SavedView(
            space_id=space_id,
            scenario_id=scenario_id,
            name=payload.name,
            description=payload.description,
            filter_config={},
            view_mode="fixed",
            created_by=operator,
        )
        sdb.add(obj)
        sdb.commit()
        sdb.refresh(obj)
        _set_members_from_ids(sdb, space_id, obj, list(payload.member_ids), operator)
        sdb.commit()
        return obj

    obj = B04SavedView(
        space_id=space_id,
        scenario_id=scenario_id,
        name=payload.name,
        description=payload.description,
        filter_config=_clean_filter_config(payload.filter_config),
        view_mode=payload.view_mode or "dynamic",
        created_by=operator,
    )
    sdb.add(obj)
    sdb.commit()
    sdb.refresh(obj)
    if obj.view_mode == "fixed":
        _snapshot_members(sdb, space_id, obj, operator)
        sdb.commit()
    return obj


def remove_members(
    sdb: Session, space_id: int, view_id: int, task_ids: List[int], operator: str
) -> B04SavedView:
    """R4：从台账移除任务 → 无论原为何种类型，均转为「固化台账」并锁定剩余成员。"""
    view = get_saved_view(sdb, space_id, view_id)
    if view.view_mode == "dynamic":
        _snapshot_members(sdb, space_id, view, operator)
        sdb.commit()
    now = datetime.now()
    sdb.query(B04SavedViewMember).filter(
        B04SavedViewMember.view_id == view_id,
        B04SavedViewMember.space_id == space_id,
        B04SavedViewMember.task_id.in_(task_ids),
        B04SavedViewMember.deleted_at.is_(None),
    ).update({B04SavedViewMember.deleted_at: now})
    view.view_mode = "fixed"
    view.updated_by = operator
    view.updated_at = now
    sdb.commit()
    sdb.refresh(view)
    return view


def add_members(
    sdb: Session, space_id: int, view_id: int, task_ids: List[int], operator: str
) -> B04SavedView:
    """补充需求：向台账补充新增任务。"""
    view = get_saved_view(sdb, space_id, view_id)
    now = datetime.now()
    if view.view_mode == "dynamic":
        _snapshot_members(sdb, space_id, view, operator)
        sdb.commit()
        view.view_mode = "fixed"
        view.updated_by = operator
        view.updated_at = now
        sdb.commit()
    _set_members_from_ids(sdb, space_id, view, list(task_ids), operator)
    sdb.commit()
    sdb.refresh(view)
    return view


def get_saved_view(sdb: Session, space_id: int, view_id: int) -> B04SavedView:
    obj = (
        sdb.query(B04SavedView)
        .filter(
            B04SavedView.id == view_id,
            B04SavedView.space_id == space_id,
            B04SavedView.deleted_at.is_(None),
        )
        .first()
    )
    if not obj:
        raise NotFoundError(f"自定义台账不存在: {view_id}")
    return obj


def update_saved_view(
    sdb: Session, space_id: int, view_id: int, payload: SavedViewUpdate, operator: str
) -> B04SavedView:
    obj = get_saved_view(sdb, space_id, view_id)
    data = payload.model_dump(exclude_unset=True)
    if "name" in data and data["name"] != obj.name:
        if (
            sdb.query(B04SavedView)
            .filter(
                B04SavedView.space_id == space_id,
                B04SavedView.scenario_id == obj.scenario_id,
                B04SavedView.name == data["name"],
                B04SavedView.id != view_id,
                B04SavedView.deleted_at.is_(None),
            )
            .first()
        ):
            raise BizError(f"台账名称已存在: {data['name']}")
    if "filter_config" in data and data["filter_config"] is not None:
        data["filter_config"] = _clean_filter_config(data["filter_config"])
    for field, value in data.items():
        setattr(obj, field, value)
    obj.updated_by = operator
    obj.updated_at = datetime.now()
    _rebuild_members(sdb, space_id, obj, operator)
    sdb.commit()
    sdb.refresh(obj)
    return obj


def delete_saved_view(sdb: Session, space_id: int, view_id: int) -> None:
    obj = get_saved_view(sdb, space_id, view_id)
    now = datetime.now()
    sdb.query(B04SavedViewMember).filter(
        B04SavedViewMember.view_id == view_id,
        B04SavedViewMember.space_id == space_id,
    ).update({B04SavedViewMember.deleted_at: now})
    obj.deleted_at = now
    sdb.commit()


def get_saved_view_out(sdb: Session, space_id: int, view_id: int) -> dict:
    """自定义台账详情（含命中任务数）。"""
    view = get_saved_view(sdb, space_id, view_id)
    if view.view_mode == "fixed":
        count = (
            sdb.query(B04SavedViewMember)
            .filter(
                B04SavedViewMember.view_id == view_id,
                B04SavedViewMember.space_id == space_id,
                B04SavedViewMember.deleted_at.is_(None),
            )
            .count()
        )
    else:
        filters = _clean_filter_config(view.filter_config or {})
        count = _task_query(sdb, space_id, view.scenario_id, **filters).count()
    return {
        "id": view.id,
        "scenario_id": view.scenario_id,
        "name": view.name,
        "description": view.description,
        "filter_config": view.filter_config,
        "view_mode": view.view_mode,
        "task_count": count,
        "created_by": view.created_by,
        "created_at": view.created_at,
    }


def export_saved_view_tasks(sdb: Session, space_id: int, view_id: int) -> bytes:
    """导出自定义台账数据（引用原任务，按模板字段）。"""
    view = get_saved_view(sdb, space_id, view_id)
    if view.view_mode == "fixed":
        rows = (
            sdb.query(B04Task)
            .join(B04SavedViewMember, B04SavedViewMember.task_id == B04Task.id)
            .filter(
                B04SavedViewMember.view_id == view_id,
                B04SavedViewMember.space_id == space_id,
                B04SavedViewMember.deleted_at.is_(None),
                B04Task.space_id == space_id,
            )
            .order_by(B04Task.id.asc())
            .all()
        )
    else:
        filters = _clean_filter_config(view.filter_config or {})
        rows = (
            _task_query(sdb, space_id, view.scenario_id, **filters)
            .order_by(B04Task.id.asc())
            .all()
        )
    template = get_template(sdb, space_id)
    config = template.config_json if template else build_default_template_config()
    return _build_export_xlsx(sdb, rows, config)


def list_saved_view_tasks(
    sdb: Session,
    space_id: int,
    view_id: int,
    page: int,
    page_size: int,
    filters: dict = None,
) -> Tuple[List[B04Task], int]:
    """自定义台账数据：动态=按 filter_config 实时；固化=从成员表取锁定任务。"""
    view = get_saved_view(sdb, space_id, view_id)
    filters = _clean_filter_config(filters or {})
    if view.view_mode == "fixed":
        member_ids = [
            r.task_id
            for r in sdb.query(B04SavedViewMember.task_id)
            .filter(
                B04SavedViewMember.view_id == view_id,
                B04SavedViewMember.space_id == space_id,
                B04SavedViewMember.deleted_at.is_(None),
            )
            .all()
        ]
        q = _task_query(sdb, space_id, view.scenario_id, **filters).filter(
            B04Task.id.in_(member_ids)
        )
    else:
        base = _clean_filter_config(view.filter_config or {})
        q = _task_query(sdb, space_id, view.scenario_id, **{**base, **filters})
    total = q.count()
    rows = q.order_by(B04Task.id.asc()).offset((page - 1) * page_size).limit(page_size).all()
    return rows, total


# ── 存量兼容：旧台账 filter_config 自动迁移（决策③） ──
# 旧键 → 新键；旧枚举值 → 新枚举值（best-effort，无法映射者清空该过滤项）
_LEGACY_FILTER_KEY_MAP = {
    "owner": "migration_owner",
    "schedule_status": "dualrun_status",
}
_LEGACY_MIGRATION_STATUS_MAP = {
    "未开始": "未开始",
    "改造完成": "已完成",
    "调度成功": "已完成",
    "数据校验通过": "已完成",
    "数据校验不通过": "已完成",
    "客户验收通过": "已完成",
    "客户验收不通过": "已完成",
    "挂起": None,
    "废弃": None,
}
_LEGACY_SCHEDULE_STATUS_MAP = {
    "未提交": "未调度",
    "已提交": "调度中",
    "调度中": "调度中",
    "调度成功": "调度中",
    "调度失败": "提交报错",
}
_LEGACY_CHECK_STATUS_MAP = {
    "未校验": None,
    "校验中": None,
    "校验通过": "校验通过",
    "校验不通过": "校验不通过",
}


def migrate_legacy_filter_configs(sdb: Session, space_id: int) -> int:
    """将 b04_saved_view.filter_config 中旧键/旧枚举值映射为新键/新枚举值。

    返回迁移的台账数量。无法映射的过滤项置空；开发态清空重建场景通常无存量数据。
    """
    rows = (
        sdb.query(B04SavedView)
        .filter(B04SavedView.space_id == space_id, B04SavedView.deleted_at.is_(None))
        .all()
    )
    migrated = 0
    for v in rows:
        cfg = v.filter_config or {}
        new_cfg = {}
        for k, val in cfg.items():
            nk = _LEGACY_FILTER_KEY_MAP.get(k, k)
            if nk == "migration_status" and val in _LEGACY_MIGRATION_STATUS_MAP:
                mapped = _LEGACY_MIGRATION_STATUS_MAP[val]
                if mapped:
                    new_cfg[nk] = mapped
            elif nk == "dualrun_status" and val in _LEGACY_SCHEDULE_STATUS_MAP:
                mapped = _LEGACY_SCHEDULE_STATUS_MAP[val]
                if mapped:
                    new_cfg[nk] = mapped
            elif nk == "check_status" and val in _LEGACY_CHECK_STATUS_MAP:
                mapped = _LEGACY_CHECK_STATUS_MAP[val]
                if mapped:
                    new_cfg[nk] = mapped
            elif nk in _ALLOWED_FILTER_KEYS:
                new_cfg[nk] = val
            # 其它键（如 tag_ids/tag_match）保留
            elif k in ("tag_ids", "tag_match"):
                new_cfg[k] = val
        if new_cfg != cfg:
            v.filter_config = new_cfg
            migrated += 1
    if migrated:
        sdb.commit()
    return migrated
