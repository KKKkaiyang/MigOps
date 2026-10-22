from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.config import settings
from app.core.deps import (
    get_current_user,
    get_space_role,
    require_space_admin,
    require_space_member,
)
from app.core.response import PageData, ok
from app.database import get_db
from app.models.role import CommonUserRole
from app.models.user import CommonUser
from app.schemas.space import (
    SpaceCreate,
    SpaceMemberIn,
    SpaceMemberRoleIn,
    SpaceOut,
    SpaceStatusIn,
    SpaceUpdate,
)
from app.services import space as svc

router = APIRouter(prefix="/b01/spaces", tags=["b01-项目空间管理"])


@router.post("", status_code=201)
def create_space(
    payload: SpaceCreate,
    db: Session = Depends(get_db),
    user: CommonUser = Depends(get_current_user),
):
    obj = svc.create_space(db, payload, operator=str(user.id))
    return ok(data=_to_out(db, obj, user), message="创建成功")


@router.get("")
def list_spaces(
    db: Session = Depends(get_db),
    user: CommonUser = Depends(get_current_user),
    page: int = Query(1, ge=1),
    page_size: int = Query(settings.DEFAULT_PAGE_SIZE, ge=1, le=settings.MAX_PAGE_SIZE),
    keyword: str = Query(None),
    status: str = Query(None),
):
    rows, total = svc.list_spaces(db, user, page, page_size, keyword, status)
    member_counts = svc.count_members(db, [r.id for r in rows])
    data = PageData[SpaceOut](
        list=[_to_out(db, r, user, member_counts.get(r.id, 0)) for r in rows],
        total=total,
        page=page,
        page_size=page_size,
    )
    return ok(data=data)


@router.get("/{space_id}")
def get_space(
    space_id: int,
    db: Session = Depends(get_db),
    user: CommonUser = Depends(get_current_user),
):
    require_space_member(db, user, space_id)
    obj = svc.get_space(db, space_id)
    return ok(data=_to_out(db, obj, user))


@router.put("/{space_id}")
def update_space(
    space_id: int,
    payload: SpaceUpdate,
    db: Session = Depends(get_db),
    user: CommonUser = Depends(get_current_user),
):
    require_space_admin(db, user, space_id)
    obj = svc.update_space(db, space_id, payload, operator=str(user.id))
    return ok(data=_to_out(db, obj, user), message="更新成功")


@router.post("/{space_id}/status")
def change_status(
    space_id: int,
    payload: SpaceStatusIn,
    db: Session = Depends(get_db),
    user: CommonUser = Depends(get_current_user),
):
    """修改空间状态（仅系统管理员 / 项目管理员）。"""
    require_space_admin(db, user, space_id)
    obj = svc.change_status(db, space_id, payload.status, operator=str(user.id))
    return ok(data=_to_out(db, obj, user), message="状态已更新")


# ── 成员管理 ──
@router.get("/{space_id}/members")
def list_members(
    space_id: int,
    db: Session = Depends(get_db),
    user: CommonUser = Depends(get_current_user),
):
    require_space_member(db, user, space_id)
    rows = svc.list_members(db, space_id)
    return ok(data=[svc.member_output(db, r) for r in rows])


@router.post("/{space_id}/members", status_code=201)
def add_member(
    space_id: int,
    payload: SpaceMemberIn,
    db: Session = Depends(get_db),
    user: CommonUser = Depends(get_current_user),
):
    require_space_admin(db, user, space_id)
    row = svc.add_member(
        db, space_id, payload.user_id, payload.role_level, operator=str(user.id)
    )
    return ok(data=svc.member_output(db, row), message="成员已添加")


@router.put("/{space_id}/members/{user_id}")
def update_member_role(
    space_id: int,
    user_id: int,
    payload: SpaceMemberRoleIn,
    db: Session = Depends(get_db),
    user: CommonUser = Depends(get_current_user),
):
    require_space_admin(db, user, space_id)
    row = svc.update_member_role(
        db, space_id, user_id, payload.role_level, operator=str(user.id)
    )
    return ok(data=svc.member_output(db, row), message="角色已更新")


@router.delete("/{space_id}/members/{user_id}")
def remove_member(
    space_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    user: CommonUser = Depends(get_current_user),
):
    require_space_admin(db, user, space_id)
    svc.remove_member(db, space_id, user_id, operator=str(user.id))
    return ok(message="成员已移除")


def _to_out(db: Session, obj, user: CommonUser, member_count: Optional[int] = None) -> SpaceOut:
    out = SpaceOut.model_validate(obj)
    out.my_role = get_space_role(db, user.id, obj.id)
    if member_count is None:
        member_count = (
            db.query(CommonUserRole).filter(CommonUserRole.space_id == obj.id).count()
        )
    out.member_count = member_count
    return out
