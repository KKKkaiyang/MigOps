"""认证与权限依赖：从 JWT 还原当前用户，并提供角色/权限校验工具。

角色模型（公共业务需求 §5）：
- L0 系统管理员：全局角色（space_id 为空），拥有全部功能权限；
- L1 项目管理员 / L2 项目成员：按项目空间绑定，仅在该空间内生效；
- 权限等级 L0 > L1 > L2。
"""

from typing import Generator, List, Optional

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session, sessionmaker

from app.core.exceptions import ForbiddenError, NotFoundError, UnauthorizedError
from app.core.security import decode_access_token
from app.database import SessionLocal, get_db, get_space_engine
from app.models.role import CommonUserRole
from app.models.space import MigSpace
from app.models.user import USER_STATUS_ENABLED, CommonUser

ROLE_L0 = "L0"
ROLE_L1 = "L1"
ROLE_L2 = "L2"
ROLE_LEVELS = {ROLE_L0: 0, ROLE_L1: 1, ROLE_L2: 2}

_bearer = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
    db: Session = Depends(get_db),
) -> CommonUser:
    """解析 Bearer Token 并加载当前用户（需为启用态）。"""
    if not credentials:
        raise UnauthorizedError()
    payload = decode_access_token(credentials.credentials)
    user_id = payload.get("sub")
    if not user_id:
        raise UnauthorizedError()
    user = (
        db.query(CommonUser)
        .filter(CommonUser.id == int(user_id), CommonUser.deleted_at.is_(None))
        .first()
    )
    if not user:
        raise UnauthorizedError()
    if user.status != USER_STATUS_ENABLED:
        raise ForbiddenError("账号已停用，请联系管理员")
    return user


def list_user_roles(db: Session, user_id: int) -> List[CommonUserRole]:
    return db.query(CommonUserRole).filter(CommonUserRole.user_id == user_id).all()


def is_l0(db: Session, user: CommonUser) -> bool:
    """是否为全局系统管理员。"""
    return (
        db.query(CommonUserRole)
        .filter(
            CommonUserRole.user_id == user.id,
            CommonUserRole.role_level == ROLE_L0,
            CommonUserRole.space_id.is_(None),
        )
        .first()
        is not None
    )


def get_space_role(db: Session, user_id: int, space_id: int) -> Optional[str]:
    """查询用户在指定空间内的角色（L0 用户恒返回 L0）。"""
    if (
        db.query(CommonUserRole)
        .filter(
            CommonUserRole.user_id == user_id,
            CommonUserRole.role_level == ROLE_L0,
            CommonUserRole.space_id.is_(None),
        )
        .first()
    ):
        return ROLE_L0
    row = (
        db.query(CommonUserRole)
        .filter(
            CommonUserRole.user_id == user_id,
            CommonUserRole.space_id == space_id,
        )
        .first()
    )
    return row.role_level if row else None


def require_l0(user: CommonUser = Depends(get_current_user), db: Session = Depends(get_db)) -> CommonUser:
    """仅系统管理员可访问（用户管理等平台级功能）。"""
    if not is_l0(db, user):
        raise ForbiddenError("该功能仅系统管理员可操作")
    return user


def require_space_creator(user: CommonUser = Depends(get_current_user), db: Session = Depends(get_db)) -> CommonUser:
    """空间创建权限：L0 全局，或任一空间担任 L1 的项目管理员。

    与公共业务需求 §4.4 / 概览页 §3（「+ 创建迁移空间」按钮仅 L0/L1）保持一致；
    L2 项目成员无创建权限（前端按钮已隐藏，此处为服务端兜底，避免越权直接调接口）。
    """
    if is_l0(db, user):
        return user
    has_l1 = (
        db.query(CommonUserRole)
        .filter(
            CommonUserRole.user_id == user.id,
            CommonUserRole.role_level == ROLE_L1,
        )
        .first()
    )
    if not has_l1:
        raise ForbiddenError("仅系统管理员或项目管理员可创建空间")
    return user


def require_space_admin(db: Session, user: CommonUser, space_id: int) -> str:
    """空间管理员校验：L0 或该空间的 L1；返回用户在该空间的有效角色。"""
    role = get_space_role(db, user.id, space_id)
    if role is None or ROLE_LEVELS[role] > ROLE_LEVELS[ROLE_L1]:
        raise ForbiddenError("仅系统管理员或项目管理员可操作")
    return role


def require_space_member(db: Session, user: CommonUser, space_id: int) -> str:
    """空间成员校验：L0 或该空间的 L1/L2。"""
    role = get_space_role(db, user.id, space_id)
    if role is None:
        raise ForbiddenError("无权访问该项目空间")
    return role


def get_accessible_space_ids(db: Session, user: CommonUser) -> Optional[List[int]]:
    """返回用户可见的空间 ID 列表；L0 返回 None 表示不受限（全部可见）。"""
    if is_l0(db, user):
        return None
    rows = (
        db.query(CommonUserRole.space_id)
        .filter(CommonUserRole.user_id == user.id, CommonUserRole.space_id.isnot(None))
        .distinct()
        .all()
    )
    return [r[0] for r in rows]


def space_exists(db: Session, space_id: int) -> bool:
    return (
        db.query(MigSpace)
        .filter(MigSpace.id == space_id, MigSpace.deleted_at.is_(None))
        .first()
        is not None
    )


def get_space_db(space_id: int) -> Generator[Session, None, None]:
    """空间业务库会话依赖：按 space_id 路由到 mig_<space_code>_db。

    公共库（用户/角色/空间主记录）与空间库同实例不同库，跨库不做 JOIN：
    权限校验走 get_db（common_user_role 在公共库），业务数据走本依赖。
    """
    common = SessionLocal()
    try:
        space = (
            common.query(MigSpace)
            .filter(MigSpace.id == space_id, MigSpace.deleted_at.is_(None))
            .first()
        )
        if not space:
            raise NotFoundError(f"空间不存在: {space_id}")
        engine = get_space_engine(space.db_name)
        session_cls = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
        sdb = session_cls()
        try:
            yield sdb
        finally:
            sdb.close()
    finally:
        common.close()
