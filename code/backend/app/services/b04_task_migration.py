"""b04 任务迁移管理服务：场景、任务台账、排查备注、自定义台账与导入导出。"""

from datetime import datetime
from typing import List, Optional, Tuple

from fastapi import UploadFile
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.core.exceptions import BizError, NotFoundError
from app.models.b04_task_migration import (
    CHECK_STATUSES,
    NOTE_KIND_CHECK_RESULT,
    NOTE_KIND_TROUBLESHOOT,
    SCHEDULE_STATUSES,
    TASK_STATUSES,
    TASK_STATUS_TRANSITIONS,
    B04SavedView,
    B04SavedViewMember,
    B04Scenario,
    B04Task,
    B04TaskNote,
)
from app.models.b06_tag import B06Tag, B06TaskTag
from app.services import b06_tag as tag_svc
from app.schemas.b04_task_migration import (
    NoteCreate,
    SavedViewCreate,
    SavedViewUpdate,
    ScenarioCreate,
    ScenarioUpdate,
    TaskUpdate,
)
from app.utils import excel as xl

# 任务导入模板列
TASK_IMPORT_HEADERS = [
    "工作流名称",
    "任务名称",
    "脚本名称",
    "Owner",
    "迁移状态",
    "调度状态",
    "数据校验状态",
    "输入表",
    "输出表",
]
# 任务导出列
TASK_EXPORT_HEADERS = [
    "工作流名称",
    "任务名称",
    "脚本名称",
    "Owner",
    "任务URI",
    "迁移状态",
    "调度状态",
    "数据校验状态",
    "输入表",
    "输出表",
    "最新排查备注",
    "更新时间",
]


def build_task_uri(space_name: str, task_name: str, workflow_name: str) -> str:
    """任务URI：项目名称://任务名称@工作流名称（场景内唯一）。"""
    return f"{space_name}://{task_name}@{workflow_name}"


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
    migration_status: Optional[str] = None,
    schedule_status: Optional[str] = None,
    check_status: Optional[str] = None,
    owner: Optional[str] = None,
    tag_ids: Optional[List[int]] = None,
    tag_match: str = "all",
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
    if migration_status:
        q = q.filter(B04Task.migration_status == migration_status)
    if schedule_status:
        q = q.filter(B04Task.schedule_status == schedule_status)
    if check_status:
        q = q.filter(B04Task.check_status == check_status)
    if owner:
        q = q.filter(B04Task.owner == owner)
    if tag_ids:
        if tag_match == "all":
            # 任务需包含全部所选标签。
            # 注意：必须用 scalar_subquery() 包裹计数子查询，否则 Query == int 会在
            # Python 层求值为 False，编译成 WHERE false 导致查不到数据（已用单测复现）。
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
            # 满足任一标签
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
    migration_status: Optional[str] = None,
    schedule_status: Optional[str] = None,
    check_status: Optional[str] = None,
    owner: Optional[str] = None,
    tag_ids: Optional[List[int]] = None,
    tag_match: str = "all",
) -> Tuple[List[B04Task], int]:
    get_scenario(sdb, space_id, scenario_id)
    q = _task_query(
        sdb,
        space_id,
        scenario_id,
        keyword,
        workflow_name,
        migration_status,
        schedule_status,
        check_status,
        owner,
        tag_ids,
        tag_match,
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


def update_task(
    sdb: Session, space_id: int, task_id: int, payload: TaskUpdate, operator: str
) -> B04Task:
    obj = get_task(sdb, space_id, task_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(obj, field, value)
    obj.updated_by = operator
    obj.updated_at = datetime.now()
    sdb.commit()
    sdb.refresh(obj)
    return obj


def _validate_transition(current: str, target: str) -> None:
    if target not in TASK_STATUSES:
        raise BizError(f"非法的迁移状态: {target}")
    allowed = TASK_STATUS_TRANSITIONS.get(current, set())
    if target not in allowed:
        allowed_text = "、".join(sorted(allowed)) or "无（终态）"
        raise BizError(f"迁移状态不能从「{current}」变更为「{target}」，可流转至: {allowed_text}")


def update_task_status(
    sdb: Session, space_id: int, task_id: int, status: str, operator: str
) -> B04Task:
    obj = get_task(sdb, space_id, task_id)
    _validate_transition(obj.migration_status, status)
    obj.migration_status = status
    obj.updated_by = operator
    obj.updated_at = datetime.now()
    sdb.commit()
    sdb.refresh(obj)
    return obj


def batch_update_task_status(
    sdb: Session, space_id: int, ids: List[int], status: str, operator: str
) -> int:
    """批量状态流转：先全部校验，任一非法则整体拒绝并提示。"""
    if status not in TASK_STATUSES:
        raise BizError(f"非法的迁移状态: {status}")
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
    invalid = [
        f"{r.task_name}（{r.migration_status}）"
        for r in rows
        if status not in TASK_STATUS_TRANSITIONS.get(r.migration_status, set())
    ]
    if invalid:
        raise BizError(
            f"以下任务不能流转为「{status}」: {'、'.join(invalid[:5])}"
            + (" 等" if len(invalid) > 5 else "")
        )
    now = datetime.now()
    for r in rows:
        r.migration_status = status
        r.updated_by = operator
        r.updated_at = now
    sdb.commit()
    return len(rows)


# ── 导入 / 导出 ──
def import_tasks(
    sdb: Session,
    space_id: int,
    scenario_id: int,
    space_name: str,
    file: UploadFile,
    operator: str,
    mode: str = "overwrite",
) -> dict:
    """导入任务台账。

    mode=overwrite：按 task_uri 覆盖更新已存在行的导入字段；
    mode=incremental：跳过已存在行（skipped 计数）。
    """
    get_scenario(sdb, space_id, scenario_id)
    if mode not in ("overwrite", "incremental"):
        raise BizError("非法的导入模式")
    xl.check_import_file(file.filename)
    content = file.file.read()
    headers, rows, line_nos = xl.read_tabular(content, file.filename or "")
    if len(rows) > xl.MAX_IMPORT_ROWS:
        raise BizError(f"单次导入不得超过 {xl.MAX_IMPORT_ROWS} 行")
    missing = [h for h in ("工作流名称", "任务名称") if h not in headers]
    if missing:
        raise BizError(f"导入文件缺少必需列: {', '.join(missing)}")

    inserted = updated = skipped = 0
    errors = []
    for row, line_no in zip(rows, line_nos):
        try:
            workflow = xl._to_str(row.get("工作流名称"))
            task_name = xl._to_str(row.get("任务名称"))
            if not workflow or not task_name:
                raise ValueError("工作流名称/任务名称不能为空")
            migration_status = xl._to_str(row.get("迁移状态")) or "未开始"
            schedule_status = xl._to_str(row.get("调度状态")) or "未提交"
            check_status = xl._to_str(row.get("数据校验状态")) or "未校验"
            if migration_status not in TASK_STATUSES:
                raise ValueError(f"非法的迁移状态: {migration_status}")
            if schedule_status not in SCHEDULE_STATUSES:
                raise ValueError(f"非法的调度状态: {schedule_status}")
            if check_status not in CHECK_STATUSES:
                raise ValueError(f"非法的数据校验状态: {check_status}")
            uri = build_task_uri(space_name, task_name, workflow)
            values = {
                "script_name": xl._to_str(row.get("脚本名称")) or None,
                "owner": xl._to_str(row.get("Owner")) or None,
                "migration_status": migration_status,
                "schedule_status": schedule_status,
                "check_status": check_status,
                "input_tables": xl._to_str(row.get("输入表")) or None,
                "output_tables": xl._to_str(row.get("输出表")) or None,
            }
            existing = (
                sdb.query(B04Task)
                .filter(
                    B04Task.scenario_id == scenario_id,
                    B04Task.task_uri == uri,
                    B04Task.deleted_at.is_(None),
                )
                .first()
            )
            if existing:
                if mode == "incremental":
                    skipped += 1
                    continue
                for field, value in values.items():
                    setattr(existing, field, value)
                existing.updated_by = operator
                existing.updated_at = datetime.now()
                updated += 1
            else:
                sdb.add(
                    B04Task(
                        space_id=space_id,
                        scenario_id=scenario_id,
                        workflow_name=workflow,
                        task_name=task_name,
                        task_uri=uri,
                        created_by=operator,
                        **values,
                    )
                )
                inserted += 1
        except ValueError as exc:
            errors.append({"row": line_no, "message": str(exc)})
    sdb.commit()
    return {"inserted": inserted, "updated": updated, "skipped": skipped, "errors": errors}


def _tasks_to_xlsx(rows: List[B04Task]) -> bytes:
    data = [
        [
            r.workflow_name,
            r.task_name,
            r.script_name or "",
            r.owner or "",
            r.task_uri,
            r.migration_status,
            r.schedule_status,
            r.check_status,
            r.input_tables or "",
            r.output_tables or "",
            r.latest_note or "",
            r.updated_at.strftime("%Y-%m-%d %H:%M:%S") if r.updated_at else "",
        ]
        for r in rows
    ]
    return xl.make_xlsx(
        TASK_EXPORT_HEADERS,
        data,
        widths=[18, 24, 24, 10, 40, 14, 12, 12, 24, 24, 30, 20],
    )


def export_tasks(
    sdb: Session,
    space_id: int,
    scenario_id: int,
    keyword: Optional[str] = None,
    workflow_name: Optional[str] = None,
    migration_status: Optional[str] = None,
    schedule_status: Optional[str] = None,
    check_status: Optional[str] = None,
    owner: Optional[str] = None,
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
            migration_status,
            schedule_status,
            check_status,
            owner,
            tag_ids,
            tag_match,
        )
        .order_by(B04Task.id.asc())
        .all()
    )
    return _tasks_to_xlsx(rows)


def task_template() -> bytes:
    return xl.make_xlsx(
        TASK_IMPORT_HEADERS,
        [
            [
                "etl_workflow",
                "ods_order_sync",
                "ods_order_sync.sql",
                "张三",
                "未开始",
                "未提交",
                "未校验",
                "ods.ods_order_di",
                "ods.ods_order_di",
            ]
        ],
        widths=[18, 24, 24, 10, 14, 12, 12, 24, 24],
    )


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
    sdb: Session, space_id: int, task_id: int, payload: NoteCreate, operator: str
) -> B04TaskNote:
    task = get_task(sdb, space_id, task_id)
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
    # 冗余最新备注摘要到任务行（列表展示用）
    summary = payload.problem_desc or payload.fix_plan or payload.cause_analysis or ""
    task.latest_note = summary[:500] if summary else task.latest_note
    task.updated_by = operator
    task.updated_at = datetime.now()
    sdb.commit()
    sdb.refresh(obj)
    return obj

# ── 标签管理 / 任务标签 ──
# 标签主表与标签 CRUD、任务标签关联逻辑统一在 app.services.b06_tag 中实现（b06 标签管理模块）；
# 本模块任务列表/台账仅调用 tag_svc 完成打标签与标签附加，不直接维护标签表。
# ── 自定义台账 ──
_ALLOWED_FILTER_KEYS = {
    "keyword",
    "workflow_name",
    "migration_status",
    "schedule_status",
    "check_status",
    "owner",
}


def _clean_filter_config(config: dict) -> dict:
    out = {k: v for k, v in (config or {}).items() if k in _ALLOWED_FILTER_KEYS and v}
    if config.get("tag_ids"):
        out["tag_ids"] = config["tag_ids"]
    if config.get("tag_match"):
        out["tag_match"] = config["tag_match"]
    return out


def _snapshot_members(sdb: Session, space_id: int, view: B04SavedView, operator: str) -> None:
    """固化台账：按当前筛选条件快照命中任务 ID 为成员。

    成员表以 (view_id, task_id) 唯一约束，故复用/复活已逻辑删除的旧行，避免重复插入冲突。
    """
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
    """R3：按显式任务 ID 写入/复活固化成员（修正 _snapshot_members 的 task_id 索引笔误）。"""
    if not task_ids:
        return
    # 仅保留归属当前 space/scenario 的合法任务，避免悬挂成员
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

    # R3：勾选具体任务创建台账 → 强制 fixed，直接以所选任务 ID 落为成员（不走筛选快照）
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
    """R4：从台账移除一个或多个任务 → 无论原为何种类型，均转为「固化台账」并锁定剩余成员。"""
    view = get_saved_view(sdb, space_id, view_id)
    if view.view_mode == "dynamic":
        # 动态台账无成员表，先按当前命中集固化为成员
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
    """补充需求：向台账补充新增任务。

    动态引用台账会先按当前命中集快照为成员并转为「固化台账」，再把指定任务加入成员集合；
    已存在（含逻辑删除）的成员会被复活，保证幂等。
    """
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
    # 模式或筛选条件变化都重建成员（动态模式清空、固化模式重新快照）
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
    """导出自定义台账数据（引用原任务）。"""
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
    return _tasks_to_xlsx(rows)


def list_saved_view_tasks(
    sdb: Session,
    space_id: int,
    view_id: int,
    page: int,
    page_size: int,
    filters: dict = None,
) -> Tuple[List[B04Task], int]:
    """自定义台账数据：
    - 动态模式：按 filter_config 实时计算（引用原任务）；
    - 固化模式：从成员表取锁定任务（即使原任务改标签/状态仍保留成员）。

    filters（R2 台账内再筛选，D4）：动态=基础 ∩ 搜索；固化=锁定成员内按搜索过滤（不增删成员）。
    """
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
