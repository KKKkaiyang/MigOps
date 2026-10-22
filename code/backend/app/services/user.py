"""用户管理服务：创建、列表、更新、停用/启用、重置密码、角色绑定。"""

from datetime import datetime
from typing import List, Optional, Tuple

from sqlalchemy.orm import Session

from app.core.deps import ROLE_L0, ROLE_L1, ROLE_L2, space_exists
from app.core.exceptions import BizError, NotFoundError
from app.core.security import (
    gen_temp_password,
    hash_password,
    validate_password_complexity,
)
from app.models.role import CommonUserRole
from app.models.space import MigSpace
from app.models.user import (
    ORG_TYPES,
    USER_STATUS_DISABLED,
    USER_STATUS_ENABLED,
    CommonUser,
)
from app.schemas.user import RoleItem, UserCreate, UserUpdate


def get_user(db: Session, user_id: int) -> CommonUser:
    obj = (
        db.query(CommonUser)
        .filter(CommonUser.id == user_id, CommonUser.deleted_at.is_(None))
        .first()
    )
    if not obj:
        raise NotFoundError(f"用户不存在: {user_id}")
    return obj


def create_user(db: Session, payload: UserCreate, operator: str) -> Tuple[CommonUser, str]:
    """创建用户，返回 (用户, 明文密码)。

    明文密码：调用方传入则使用（需满足复杂度），否则系统生成临时密码，
    并通过 must_change_password 强制首次登录修改。
    """
    if (
        db.query(CommonUser)
        .filter(CommonUser.username == payload.username, CommonUser.deleted_at.is_(None))
        .first()
    ):
        raise BizError(f"用户名已存在: {payload.username}")

    if payload.org_type and payload.org_type not in ORG_TYPES:
        raise BizError(f"非法的用户归属: {payload.org_type}")

    if payload.password:
        validate_password_complexity(payload.password)
        plain = payload.password
        must_change = 0
    else:
        plain = gen_temp_password()
        must_change = 1

    obj = CommonUser(
        username=payload.username,
        password=hash_password(plain),
        name=payload.name,
        email=payload.email,
        phone=payload.phone,
        org_type=payload.org_type,
        status=USER_STATUS_ENABLED,
        must_change_password=must_change,
        created_by=operator,
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj, plain


def list_users(
    db: Session, page: int, page_size: int, keyword: Optional[str] = None
) -> Tuple[List[CommonUser], int]:
    q = db.query(CommonUser).filter(CommonUser.deleted_at.is_(None))
    if keyword:
        like = f"%{keyword}%"
        q = q.filter(
            (CommonUser.username.like(like)) | (CommonUser.name.like(like))
        )
    total = q.count()
    rows = q.order_by(CommonUser.id.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return rows, total


def update_user(db: Session, user_id: int, payload: UserUpdate, operator: str) -> CommonUser:
    obj = get_user(db, user_id)
    if payload.org_type and payload.org_type not in ORG_TYPES:
        raise BizError(f"非法的用户归属: {payload.org_type}")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(obj, field, value)
    obj.updated_by = operator
    obj.updated_at = datetime.now()
    db.commit()
    db.refresh(obj)
    return obj


def set_user_status(db: Session, user_id: int, status: str, operator: str) -> CommonUser:
    """停用 / 启用用户（注销语义：停用可恢复）。"""
    if status not in (USER_STATUS_ENABLED, USER_STATUS_DISABLED):
        raise BizError(f"非法的账号状态: {status}")
    obj = get_user(db, user_id)
    if obj.id == _operator_id(operator) and status == USER_STATUS_DISABLED:
        raise BizError("不能停用当前登录账号")
    obj.status = status
    obj.updated_by = operator
    obj.updated_at = datetime.now()
    if status == USER_STATUS_DISABLED:
        obj.login_fail_count = 0
        obj.locked_until = None
    db.commit()
    db.refresh(obj)
    return obj


def _operator_id(operator: str) -> Optional[int]:
    try:
        return int(operator)
    except (TypeError, ValueError):
        return None


def reset_password(db: Session, user_id: int, operator: str) -> Tuple[CommonUser, str]:
    """管理员重置密码：生成临时密码并强制首次登录修改。"""
    obj = get_user(db, user_id)
    plain = gen_temp_password()
    obj.password = hash_password(plain)
    obj.must_change_password = 1
    obj.login_fail_count = 0
    obj.locked_until = None
    obj.updated_by = operator
    obj.updated_at = datetime.now()
    db.commit()
    db.refresh(obj)
    return obj, plain


def get_user_roles(db: Session, user_id: int) -> List[CommonUserRole]:
    get_user(db, user_id)
    return db.query(CommonUserRole).filter(CommonUserRole.user_id == user_id).all()


def set_user_roles(db: Session, user_id: int, roles: List[RoleItem], operator: str) -> List[CommonUserRole]:
    """全量覆盖用户角色绑定。

    规则：L0 为全局角色（space_id 必须为空）；L1/L2 必须绑定已存在的空间。
    """
    user = get_user(db, user_id)
    for item in roles:
        if item.role_level not in (ROLE_L0, ROLE_L1, ROLE_L2):
            raise BizError(f"非法的角色等级: {item.role_level}")
        if item.role_level == ROLE_L0 and item.space_id:
            raise BizError("L0 系统管理员为全局角色，不能绑定到具体空间")
        if item.role_level in (ROLE_L1, ROLE_L2) and not item.space_id:
            raise BizError("L1/L2 角色必须绑定到具体项目空间")
        if item.space_id and not space_exists(db, item.space_id):
            raise BizError(f"项目空间不存在: {item.space_id}")

    db.query(CommonUserRole).filter(CommonUserRole.user_id == user_id).delete()

    created = []
    for item in roles:
        row = CommonUserRole(
            user_id=user.id,
            role_level=item.role_level,
            space_id=item.space_id,
            created_by=operator,
        )
        db.add(row)
        created.append(row)
    db.commit()
    for row in created:
        db.refresh(row)
    return created


def role_output(db: Session, row: CommonUserRole) -> dict:
    from app.models.role import ROLE_LEVEL_NAMES

    space_name = None
    if row.space_id:
        space = (
            db.query(MigSpace)
            .filter(MigSpace.id == row.space_id, MigSpace.deleted_at.is_(None))
            .first()
        )
        space_name = space.space_name if space else None
    return {
        "id": row.id,
        "role_level": row.role_level,
        "role_name": ROLE_LEVEL_NAMES.get(row.role_level, row.role_level),
        "space_id": row.space_id,
        "space_name": space_name,
    }
