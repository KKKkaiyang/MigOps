from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.config import settings
from app.core.deps import require_l0
from app.core.response import PageData, ok
from app.database import get_db
from app.models.user import CommonUser
from app.schemas.user import RoleSetIn, UserCreate, UserOut, UserUpdate
from app.services import user as svc

router = APIRouter(prefix="/common/users", tags=["common-用户管理"], dependencies=[Depends(require_l0)])


@router.get("")
def list_users(
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(settings.DEFAULT_PAGE_SIZE, ge=1, le=settings.MAX_PAGE_SIZE),
    keyword: str = Query(None),
):
    rows, total = svc.list_users(db, page, page_size, keyword)
    data = PageData[UserOut](
        list=[UserOut.model_validate(r) for r in rows],
        total=total,
        page=page,
        page_size=page_size,
    )
    return ok(data=data)


@router.post("", status_code=201)
def create_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
    admin: CommonUser = Depends(require_l0),
):
    obj, plain = svc.create_user(db, payload, operator=str(admin.id))
    return ok(
        data={"user": UserOut.model_validate(obj), "password": plain},
        message="创建成功",
    )


@router.get("/{user_id}")
def get_user(user_id: int, db: Session = Depends(get_db)):
    return ok(data=UserOut.model_validate(svc.get_user(db, user_id)))


@router.put("/{user_id}")
def update_user(
    user_id: int,
    payload: UserUpdate,
    db: Session = Depends(get_db),
    admin: CommonUser = Depends(require_l0),
):
    obj = svc.update_user(db, user_id, payload, operator=str(admin.id))
    return ok(data=UserOut.model_validate(obj), message="更新成功")


@router.post("/{user_id}/disable")
def disable_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin: CommonUser = Depends(require_l0),
):
    """注销（停用）用户：不可登录，数据保留，可恢复。"""
    obj = svc.set_user_status(db, user_id, "disabled", operator=str(admin.id))
    return ok(data=UserOut.model_validate(obj), message="已停用")


@router.post("/{user_id}/enable")
def enable_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin: CommonUser = Depends(require_l0),
):
    obj = svc.set_user_status(db, user_id, "enabled", operator=str(admin.id))
    return ok(data=UserOut.model_validate(obj), message="已启用")


@router.post("/{user_id}/reset-password")
def reset_password(
    user_id: int,
    db: Session = Depends(get_db),
    admin: CommonUser = Depends(require_l0),
):
    """重置密码：生成临时密码，用户首次登录强制修改。"""
    _obj, plain = svc.reset_password(db, user_id, operator=str(admin.id))
    return ok(data={"temp_password": plain}, message="密码已重置")


@router.get("/{user_id}/roles")
def get_roles(user_id: int, db: Session = Depends(get_db)):
    rows = svc.get_user_roles(db, user_id)
    return ok(data=[svc.role_output(db, r) for r in rows])


@router.put("/{user_id}/roles")
def set_roles(
    user_id: int,
    payload: RoleSetIn,
    db: Session = Depends(get_db),
    admin: CommonUser = Depends(require_l0),
):
    """设置用户角色（全量覆盖）：L0 全局；L1/L2 绑定具体空间。"""
    rows = svc.set_user_roles(db, user_id, payload.roles, operator=str(admin.id))
    return ok(data=[svc.role_output(db, r) for r in rows], message="角色已更新")
