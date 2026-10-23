"""b04 任务迁移管理接口。

空间业务表位于空间库（mig_<space_code>_db），经 get_space_db 路由；
权限校验经 get_db（common_user_role 位于公共库）。
"""

from typing import Optional
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Query, Response, UploadFile
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_space_db, require_space_member
from app.core.response import PageData, ok
from app.database import get_db
from app.models.user import CommonUser
from app.schemas.b04_task_migration import (
    NoteCreate,
    NoteOut,
    SavedViewAddMembers,
    SavedViewCreate,
    SavedViewRemoveMembers,
    SavedViewUpdate,
    ScenarioCreate,
    ScenarioUpdate,
    TaskBatchStatusIn,
    TaskOut,
    TaskStatusIn,
    TaskUpdate,
)
from app.schemas.b06_tag import TagBrief, TaskBatchTagIn, TaskTagIn
from app.services import b04_task_migration as svc
from app.services import b06_tag as tag_svc
from app.services.space import get_space
from app.utils.excel import XLSX_MEDIA_TYPE

router = APIRouter(prefix="/b04", tags=["b04-任务迁移管理"])


def _xlsx_response(content: bytes, filename: str) -> Response:
    return Response(
        content=content,
        media_type=XLSX_MEDIA_TYPE,
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"
        },
    )


def _parse_int_list(raw: Optional[str]) -> Optional[list]:
    """解析逗号分隔的整数列表（空值返回 None）。"""
    if not raw:
        return None
    out = []
    for part in raw.split(","):
        part = part.strip()
        if part.isdigit():
            out.append(int(part))
    return out or None


def _task_out_with_tags(task, tag_map: dict) -> TaskOut:
    out = TaskOut.model_validate(task)
    out.tags = [TagBrief(**t) for t in tag_map.get(task.id, [])]
    return out


# ── 迁移场景 ──
@router.get("/scenarios")
def list_scenarios(
    space_id: int,
    db: Session = Depends(get_db),
    sdb: Session = Depends(get_space_db),
    user: CommonUser = Depends(get_current_user),
):
    require_space_member(db, user, space_id)
    return ok(data=svc.list_scenarios(sdb, space_id))


@router.post("/scenarios", status_code=201)
def create_scenario(
    space_id: int,
    payload: ScenarioCreate,
    db: Session = Depends(get_db),
    sdb: Session = Depends(get_space_db),
    user: CommonUser = Depends(get_current_user),
):
    require_space_member(db, user, space_id)
    obj = svc.create_scenario(sdb, space_id, payload, operator=str(user.id))
    return ok(data={"id": obj.id, "name": obj.name}, message="创建成功")


@router.put("/scenarios/{scenario_id}")
def update_scenario(
    space_id: int,
    scenario_id: int,
    payload: ScenarioUpdate,
    db: Session = Depends(get_db),
    sdb: Session = Depends(get_space_db),
    user: CommonUser = Depends(get_current_user),
):
    require_space_member(db, user, space_id)
    svc.update_scenario(sdb, space_id, scenario_id, payload, operator=str(user.id))
    return ok(message="更新成功")


@router.delete("/scenarios/{scenario_id}")
def delete_scenario(
    space_id: int,
    scenario_id: int,
    db: Session = Depends(get_db),
    sdb: Session = Depends(get_space_db),
    user: CommonUser = Depends(get_current_user),
):
    require_space_member(db, user, space_id)
    svc.delete_scenario(sdb, space_id, scenario_id)
    return ok(message="删除成功")


# ── 任务台账 ──
@router.get("/scenarios/{scenario_id}/tasks")
def list_tasks(
    space_id: int,
    scenario_id: int,
    db: Session = Depends(get_db),
    sdb: Session = Depends(get_space_db),
    user: CommonUser = Depends(get_current_user),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    keyword: str = Query(None),
    workflow_name: str = Query(None),
    migration_status: str = Query(None),
    schedule_status: str = Query(None),
    check_status: str = Query(None),
    owner: str = Query(None),
    tag_ids: str = Query(None, description="逗号分隔的标签ID，按 tag_match 规则筛选"),
    tag_match: str = Query("all", description="all=任务需含全部所选标签;any=含任一标签"),
):
    require_space_member(db, user, space_id)
    tag_id_list = _parse_int_list(tag_ids)
    rows, total = svc.list_tasks(
        sdb,
        space_id,
        scenario_id,
        page,
        page_size,
        keyword,
        workflow_name,
        migration_status,
        schedule_status,
        check_status,
        owner,
        tag_id_list,
        tag_match,
    )
    tag_map = tag_svc.get_task_tags_map(sdb, space_id, [r.id for r in rows])
    data = PageData[TaskOut](
        list=[_task_out_with_tags(r, tag_map) for r in rows],
        total=total,
        page=page,
        page_size=page_size,
    )
    return ok(data=data)


@router.get("/tasks/{task_id}")
def get_task(
    space_id: int,
    task_id: int,
    db: Session = Depends(get_db),
    sdb: Session = Depends(get_space_db),
    user: CommonUser = Depends(get_current_user),
):
    require_space_member(db, user, space_id)
    obj = svc.get_task(sdb, space_id, task_id)
    return ok(data=TaskOut.model_validate(obj))


@router.put("/tasks/{task_id}")
def update_task(
    space_id: int,
    task_id: int,
    payload: TaskUpdate,
    db: Session = Depends(get_db),
    sdb: Session = Depends(get_space_db),
    user: CommonUser = Depends(get_current_user),
):
    require_space_member(db, user, space_id)
    svc.update_task(sdb, space_id, task_id, payload, operator=str(user.id))
    return ok(message="更新成功")


@router.post("/tasks/{task_id}/status")
def update_task_status(
    space_id: int,
    task_id: int,
    payload: TaskStatusIn,
    db: Session = Depends(get_db),
    sdb: Session = Depends(get_space_db),
    user: CommonUser = Depends(get_current_user),
):
    require_space_member(db, user, space_id)
    svc.update_task_status(sdb, space_id, task_id, payload.status, operator=str(user.id))
    return ok(message="状态已更新")


@router.post("/scenarios/{scenario_id}/tasks/batch-status")
def batch_update_task_status(
    space_id: int,
    scenario_id: int,
    payload: TaskBatchStatusIn,
    db: Session = Depends(get_db),
    sdb: Session = Depends(get_space_db),
    user: CommonUser = Depends(get_current_user),
):
    require_space_member(db, user, space_id)
    svc.get_scenario(sdb, space_id, scenario_id)
    affected = svc.batch_update_task_status(
        sdb, space_id, payload.ids, payload.status, operator=str(user.id)
    )
    return ok(data={"affected": affected}, message=f"已更新 {affected} 条")


@router.post("/scenarios/{scenario_id}/tasks/import")
def import_tasks(
    space_id: int,
    scenario_id: int,
    db: Session = Depends(get_db),
    sdb: Session = Depends(get_space_db),
    user: CommonUser = Depends(get_current_user),
    file: UploadFile = File(...),
    mode: str = Query("overwrite", description="overwrite=覆盖导入; incremental=增量导入"),
):
    require_space_member(db, user, space_id)
    space = get_space(db, space_id)
    result = svc.import_tasks(
        sdb, space_id, scenario_id, space.space_name, file, operator=str(user.id), mode=mode
    )
    return ok(data=result, message="导入完成")


@router.get("/scenarios/{scenario_id}/tasks/template")
def task_template(
    space_id: int,
    scenario_id: int,
    db: Session = Depends(get_db),
    sdb: Session = Depends(get_space_db),
    user: CommonUser = Depends(get_current_user),
):
    require_space_member(db, user, space_id)
    return _xlsx_response(svc.task_template(), "任务台账导入模板.xlsx")


@router.get("/scenarios/{scenario_id}/tasks/export")
def export_tasks(
    space_id: int,
    scenario_id: int,
    db: Session = Depends(get_db),
    sdb: Session = Depends(get_space_db),
    user: CommonUser = Depends(get_current_user),
    keyword: str = Query(None),
    workflow_name: str = Query(None),
    migration_status: str = Query(None),
    schedule_status: str = Query(None),
    check_status: str = Query(None),
    owner: str = Query(None),
    tag_ids: str = Query(None, description="逗号分隔的标签ID，按 tag_match 规则筛选"),
    tag_match: str = Query("all", description="all=任务需含全部所选标签;any=含任一标签"),
):
    require_space_member(db, user, space_id)
    tag_id_list = _parse_int_list(tag_ids)
    content = svc.export_tasks(
        sdb,
        space_id,
        scenario_id,
        keyword,
        workflow_name,
        migration_status,
        schedule_status,
        check_status,
        owner,
        tag_id_list,
        tag_match,
    )
    return _xlsx_response(content, "任务台账.xlsx")

# ── 任务标签（标签主表与 CRUD 见 b06 标签管理模块；此处仅任务侧打标签） ──
# ── 任务标签 ──
@router.get("/tasks/{task_id}/tags")
def get_task_tags(
    space_id: int,
    task_id: int,
    db: Session = Depends(get_db),
    sdb: Session = Depends(get_space_db),
    user: CommonUser = Depends(get_current_user),
):
    require_space_member(db, user, space_id)
    return ok(data=tag_svc.get_task_tags(sdb, space_id, task_id))


@router.put("/tasks/{task_id}/tags")
def set_task_tags(
    space_id: int,
    task_id: int,
    payload: TaskTagIn,
    db: Session = Depends(get_db),
    sdb: Session = Depends(get_space_db),
    user: CommonUser = Depends(get_current_user),
):
    require_space_member(db, user, space_id)
    tags = tag_svc.set_task_tags(sdb, space_id, task_id, payload, operator=str(user.id))
    return ok(data=tags, message="标签已更新")


@router.post("/scenarios/{scenario_id}/tasks/batch-tags")
def batch_task_tags(
    space_id: int,
    scenario_id: int,
    payload: TaskBatchTagIn,
    db: Session = Depends(get_db),
    sdb: Session = Depends(get_space_db),
    user: CommonUser = Depends(get_current_user),
):
    require_space_member(db, user, space_id)
    svc.get_scenario(sdb, space_id, scenario_id)
    affected = tag_svc.batch_task_tags(
        sdb,
        space_id,
        payload.ids,
        payload.tag_ids,
        payload.action,
        operator=str(user.id),
    )
    action_text = "打标签" if payload.action == "add" else "移除标签"
    return ok(data={"affected": affected}, message=f"已为 {affected} 个任务{action_text}")


# ── 排查备注 ──
@router.get("/tasks/{task_id}/notes")
def list_notes(
    space_id: int,
    task_id: int,
    db: Session = Depends(get_db),
    sdb: Session = Depends(get_space_db),
    user: CommonUser = Depends(get_current_user),
):
    require_space_member(db, user, space_id)
    rows = svc.list_notes(sdb, space_id, task_id)
    return ok(data=[NoteOut.model_validate(r) for r in rows])


@router.post("/tasks/{task_id}/notes", status_code=201)
def create_note(
    space_id: int,
    task_id: int,
    payload: NoteCreate,
    db: Session = Depends(get_db),
    sdb: Session = Depends(get_space_db),
    user: CommonUser = Depends(get_current_user),
):
    require_space_member(db, user, space_id)
    obj = svc.create_note(sdb, space_id, task_id, payload, operator=str(user.id))
    return ok(data=NoteOut.model_validate(obj), message="备注已添加")


# ── 自定义台账 ──
@router.get("/scenarios/{scenario_id}/saved-views")
def list_saved_views(
    space_id: int,
    scenario_id: int,
    db: Session = Depends(get_db),
    sdb: Session = Depends(get_space_db),
    user: CommonUser = Depends(get_current_user),
):
    require_space_member(db, user, space_id)
    return ok(data=svc.list_saved_views(sdb, space_id, scenario_id))


@router.post("/scenarios/{scenario_id}/saved-views", status_code=201)
def create_saved_view(
    space_id: int,
    scenario_id: int,
    payload: SavedViewCreate,
    db: Session = Depends(get_db),
    sdb: Session = Depends(get_space_db),
    user: CommonUser = Depends(get_current_user),
):
    require_space_member(db, user, space_id)
    obj = svc.create_saved_view(sdb, space_id, scenario_id, payload, operator=str(user.id))
    return ok(data={"id": obj.id, "name": obj.name}, message="台账已创建")


@router.put("/saved-views/{view_id}")
def update_saved_view(
    space_id: int,
    view_id: int,
    payload: SavedViewUpdate,
    db: Session = Depends(get_db),
    sdb: Session = Depends(get_space_db),
    user: CommonUser = Depends(get_current_user),
):
    require_space_member(db, user, space_id)
    svc.update_saved_view(sdb, space_id, view_id, payload, operator=str(user.id))
    return ok(message="更新成功")


@router.delete("/saved-views/{view_id}")
def delete_saved_view(
    space_id: int,
    view_id: int,
    db: Session = Depends(get_db),
    sdb: Session = Depends(get_space_db),
    user: CommonUser = Depends(get_current_user),
):
    require_space_member(db, user, space_id)
    svc.delete_saved_view(sdb, space_id, view_id)
    return ok(message="删除成功")


@router.get("/saved-views/{view_id}")
def get_saved_view(
    space_id: int,
    view_id: int,
    db: Session = Depends(get_db),
    sdb: Session = Depends(get_space_db),
    user: CommonUser = Depends(get_current_user),
):
    require_space_member(db, user, space_id)
    return ok(data=svc.get_saved_view_out(sdb, space_id, view_id))


@router.get("/saved-views/{view_id}/tasks")
def list_saved_view_tasks(
    space_id: int,
    view_id: int,
    db: Session = Depends(get_db),
    sdb: Session = Depends(get_space_db),
    user: CommonUser = Depends(get_current_user),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    keyword: Optional[str] = Query(None),
    workflow_name: Optional[str] = Query(None),
    migration_status: Optional[str] = Query(None),
    schedule_status: Optional[str] = Query(None),
    check_status: Optional[str] = Query(None),
    owner: Optional[str] = Query(None),
    tag_ids: Optional[str] = Query(None),
    tag_match: str = Query("all"),
):
    require_space_member(db, user, space_id)
    filters = {
        k: v
        for k, v in {
            "keyword": keyword,
            "workflow_name": workflow_name,
            "migration_status": migration_status,
            "schedule_status": schedule_status,
            "check_status": check_status,
            "owner": owner,
            "tag_ids": _parse_int_list(tag_ids),
            "tag_match": tag_match,
        }.items()
        if v is not None and not (isinstance(v, list) and len(v) == 0)
    }
    rows, total = svc.list_saved_view_tasks(sdb, space_id, view_id, page, page_size, filters)
    tag_map = tag_svc.get_task_tags_map(sdb, space_id, [r.id for r in rows])
    data = PageData[TaskOut](
        list=[_task_out_with_tags(r, tag_map) for r in rows],
        total=total,
        page=page,
        page_size=page_size,
    )
    return ok(data=data)


@router.post("/saved-views/{view_id}/remove-members")
def remove_saved_view_members(
    space_id: int,
    view_id: int,
    payload: SavedViewRemoveMembers,
    db: Session = Depends(get_db),
    sdb: Session = Depends(get_space_db),
    user: CommonUser = Depends(get_current_user),
):
    """R4：从台账移除任务（批量）→ 台账强制转固化并锁定剩余成员。"""
    require_space_member(db, user, space_id)
    svc.remove_members(sdb, space_id, view_id, payload.task_ids, operator=str(user.id))
    return ok(message="已移除指定任务，台账已转为固化台账")


@router.post("/saved-views/{view_id}/add-members")
def add_saved_view_members(
    space_id: int,
    view_id: int,
    payload: SavedViewAddMembers,
    db: Session = Depends(get_db),
    sdb: Session = Depends(get_space_db),
    user: CommonUser = Depends(get_current_user),
):
    """补充需求：向台账补充新增任务（动态引用台账将自动固化为成员集合）。"""
    require_space_member(db, user, space_id)
    svc.add_members(sdb, space_id, view_id, payload.task_ids, operator=str(user.id))
    return ok(message="已向台账补充任务")


@router.get("/saved-views/{view_id}/tasks/export")
def export_saved_view_tasks(
    space_id: int,
    view_id: int,
    db: Session = Depends(get_db),
    sdb: Session = Depends(get_space_db),
    user: CommonUser = Depends(get_current_user),
):
    require_space_member(db, user, space_id)
    content = svc.export_saved_view_tasks(sdb, space_id, view_id)
    return _xlsx_response(content, "自定义台账.xlsx")
