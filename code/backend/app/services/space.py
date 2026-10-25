"""项目空间管理服务：空间 CRUD、状态流转、成员管理、空间库初始化。"""

import logging
from datetime import datetime
from typing import List, Optional, Tuple

from sqlalchemy import func, or_
from sqlalchemy.orm import Session, sessionmaker

from app.core.deps import (
    ROLE_L1,
    ROLE_L2,
    get_space_role,
    get_accessible_space_ids,
)
from app.core.exceptions import BizError, ForbiddenError, NotFoundError
from app.database import (
    drop_space_database,
    ensure_space_tables,
    get_space_engine,
    space_db_name,
)
from app.models.role import ROLE_LEVEL_NAMES, CommonUserRole
from app.models.space import (
    SPACE_CODE_PATTERN,
    SPACE_STATUS_ACCEPTED,
    SPACE_STATUS_DELETED,
    SPACE_STATUS_DELIVERING,
    SPACE_STATUS_INIT,
    SPACE_STATUS_TRANSITIONS,
    SPACE_STATUSES,
    MigSpace,
    SpaceDeleteLog,
)
from app.models.user import USER_STATUS_ENABLED, CommonUser
from app.schemas.space import SpaceCreate, SpaceUpdate

import re

logger = logging.getLogger("migops")


def _ensure_code_available(db: Session, space_code: str) -> None:
    if not re.match(SPACE_CODE_PATTERN, space_code):
        raise BizError("项目简称须为小写字母开头，可含小写字母/数字/下划线，长度 2~32")
    if (
        db.query(MigSpace)
        .filter(MigSpace.space_code == space_code, MigSpace.deleted_at.is_(None))
        .first()
    ):
        raise BizError(f"项目简称已存在: {space_code}")


def init_space_schema(space_code: str, space_id: int) -> str:
    """初始化空间库结构：建库 → 建空间业务表 → 种子预置分类，返回库名。"""
    db_name = ensure_space_tables(space_code)
    engine = get_space_engine(db_name)
    session_cls = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    with session_cls() as sdb:
        # 局部导入避免模块初始化顺序依赖
        from app.services.b02_material import seed_preset_categories
        from app.services.b04_task_migration import (
            migrate_legacy_filter_configs,
            seed_default_template,
        )

        seed_preset_categories(sdb, space_id)
        # b04 任务迁移：注入默认迁移模板（保证存量/新空间均可导入，决策③）
        seed_default_template(sdb, space_id, operator="system")
        # 存量兼容：旧台账 filter_config 自动迁移为新字段名/枚举（决策③）
        migrate_legacy_filter_configs(sdb, space_id)
    return db_name


def ensure_existing_spaces_initialized(db: Session) -> None:
    """启动引导：为存量空间补建空间业务表与预置数据（幂等，失败不阻断启动）。"""
    spaces = db.query(MigSpace).filter(MigSpace.deleted_at.is_(None)).all()
    for space in spaces:
        try:
            init_space_schema(space.space_code, space.id)
        except Exception as exc:  # noqa: BLE001
            logger.warning("空间 %s 结构初始化失败: %s", space.space_code, exc)


def create_space(db: Session, payload: SpaceCreate, operator: str) -> MigSpace:
    """创建项目空间：查重 → 落空间记录 → 初始化空间库结构 → 创建人自动绑定 L1。"""
    space_code = payload.space_code.strip().lower()
    _ensure_code_available(db, space_code)

    if (
        db.query(MigSpace)
        .filter(MigSpace.space_name == payload.space_name, MigSpace.deleted_at.is_(None))
        .first()
    ):
        raise BizError(f"项目名称已存在: {payload.space_name}")

    obj = MigSpace(
        space_code=space_code,
        space_name=payload.space_name,
        customer_name=payload.customer_name,
        source_platform=payload.source_platform,
        target_platform=payload.target_platform,
        owner=payload.owner,
        remark=payload.remark,
        overall_progress=payload.overall_progress or 0,
        start_date=payload.start_date,
        end_date=payload.end_date,
        status=SPACE_STATUS_INIT,
        created_by=operator,
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)

    # 初始化空间库结构：建库 → 建空间业务表（b02~b04）→ 种子预置分类
    try:
        obj.db_name = init_space_schema(space_code, obj.id)
        db.commit()
    except ValueError as exc:
        raise BizError(str(exc))
    except Exception as exc:  # noqa: BLE001
        # 结构初始化失败则移除空间记录，避免留下半成品空间
        db.delete(obj)
        db.commit()
        logger.error("空间 %s 结构初始化失败: %s", space_code, exc)
        raise BizError("空间初始化失败，请重试或联系管理员")

    # 创建人自动成为该空间的项目管理员（L1）
    operator_id = None
    try:
        operator_id = int(operator)
    except (TypeError, ValueError):
        operator_id = None
    if operator_id:
        db.add(
            CommonUserRole(
                user_id=operator_id, role_level=ROLE_L1, space_id=obj.id, created_by=operator
            )
        )
        db.commit()
    return obj


def get_space(db: Session, space_id: int) -> MigSpace:
    obj = (
        db.query(MigSpace)
        .filter(MigSpace.id == space_id, MigSpace.deleted_at.is_(None))
        .first()
    )
    if not obj:
        raise NotFoundError(f"空间不存在: {space_id}")
    return obj


def list_spaces(
    db: Session,
    user: CommonUser,
    page: int,
    page_size: int,
    keyword: Optional[str] = None,
    status: Optional[str] = None,
) -> Tuple[List[MigSpace], int]:
    """按权限列出空间：L0 看全部，其他人仅看已绑定的空间。"""
    q = db.query(MigSpace).filter(MigSpace.deleted_at.is_(None))
    accessible = get_accessible_space_ids(db, user)
    if accessible is not None:
        if not accessible:
            return [], 0
        q = q.filter(MigSpace.id.in_(accessible))
    if status:
        q = q.filter(MigSpace.status == status)
    if keyword:
        like = f"%{keyword}%"
        q = q.filter(or_(MigSpace.space_name.like(like), MigSpace.space_code.like(like)))
    total = q.count()
    rows = (
        q.order_by(MigSpace.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return rows, total


def count_members(db: Session, space_ids: List[int]) -> dict:
    """批量统计空间成员数，避免列表页 N+1。"""
    if not space_ids:
        return {}
    rows = (
        db.query(CommonUserRole.space_id, func.count(CommonUserRole.id))
        .filter(CommonUserRole.space_id.in_(space_ids))
        .group_by(CommonUserRole.space_id)
        .all()
    )
    return {space_id: cnt for space_id, cnt in rows}


def update_space(db: Session, space_id: int, payload: SpaceUpdate, operator: str) -> MigSpace:
    obj = get_space(db, space_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(obj, field, value)
    obj.updated_by = operator
    obj.updated_at = datetime.now()
    db.commit()
    db.refresh(obj)
    return obj


def change_status(db: Session, space_id: int, status: str, operator: str) -> MigSpace:
    """状态流转：仅允许按状态机定义的方向推进。"""
    if status not in SPACE_STATUSES:
        raise BizError(f"非法的空间状态: {status}")
    obj = get_space(db, space_id)
    allowed = SPACE_STATUS_TRANSITIONS.get(obj.status, set())
    if status not in allowed:
        raise BizError(f"空间状态不能从「{obj.status}」变更为「{status}」")
    obj.status = status
    obj.updated_by = operator
    obj.updated_at = datetime.now()
    db.commit()
    db.refresh(obj)
    return obj


def delete_space(db: Session, space_id: int, operator: str) -> MigSpace:
    """物理删除项目空间（仅 L0 可调用，路由层 require_l0 已拦截）。

    执行顺序：
    1. 物理销毁空间业务库（DROP DATABASE）。失败则中止，不标记元数据，保持状态一致。
    2. 逻辑标记公共库元数据（deleted_at + status=已删除），保留用于审计追溯。
    3. 写删除审计日志（空间库已销毁，审计留存公共库）。
    """
    obj = get_space(db, space_id)  # 不存在或已删除 → NotFoundError
    db_name = obj.db_name
    space_code = obj.space_code
    space_name = obj.space_name

    # 1) 物理销毁空间业务库（失败即中止，不标记元数据）
    try:
        drop_space_database(db_name)
    except Exception as exc:  # noqa: BLE001
        logger.error("空间 %s 数据库删除失败: %s", space_code, exc)
        raise BizError("空间数据库删除失败，请确认数据库实例状态后重试")

    # 2) 逻辑标记公共库元数据（保留，便于审计追溯）
    now = datetime.now()
    obj.status = SPACE_STATUS_DELETED
    obj.deleted_at = now
    obj.updated_by = operator
    obj.updated_at = now

    # 3) 写删除审计（空间库已销毁，审计留存公共库）
    db.add(
        SpaceDeleteLog(
            space_id=obj.id,
            space_name=space_name,
            space_code=space_code,
            db_name=db_name,
            operator=operator,
            created_at=now,
        )
    )
    db.commit()
    db.refresh(obj)
    return obj


# ── 成员管理 ──
def list_members(db: Session, space_id: int) -> List[CommonUserRole]:
    get_space(db, space_id)
    return (
        db.query(CommonUserRole)
        .filter(CommonUserRole.space_id == space_id)
        .order_by(CommonUserRole.id.asc())
        .all()
    )


def add_member(db: Session, space_id: int, user_id: int, role_level: str, operator: str) -> CommonUserRole:
    if role_level not in (ROLE_L1, ROLE_L2):
        raise BizError(f"非法的空间角色: {role_level}")
    get_space(db, space_id)
    user = (
        db.query(CommonUser)
        .filter(CommonUser.id == user_id, CommonUser.deleted_at.is_(None))
        .first()
    )
    if not user:
        raise NotFoundError(f"用户不存在: {user_id}")
    if user.status != USER_STATUS_ENABLED:
        raise BizError("该账号已停用，不能加入空间")
    if (
        db.query(CommonUserRole)
        .filter(CommonUserRole.user_id == user_id, CommonUserRole.space_id == space_id)
        .first()
    ):
        raise BizError("该用户已是空间成员")
    row = CommonUserRole(
        user_id=user_id, role_level=role_level, space_id=space_id, created_by=operator
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def update_member_role(db: Session, space_id: int, user_id: int, role_level: str, operator: str) -> CommonUserRole:
    if role_level not in (ROLE_L1, ROLE_L2):
        raise BizError(f"非法的空间角色: {role_level}")
    row = (
        db.query(CommonUserRole)
        .filter(CommonUserRole.user_id == user_id, CommonUserRole.space_id == space_id)
        .first()
    )
    if not row:
        raise NotFoundError("该用户不是空间成员")
    row.role_level = role_level
    row.created_by = operator
    db.commit()
    db.refresh(row)
    return row


def remove_member(db: Session, space_id: int, user_id: int, operator: str) -> None:
    row = (
        db.query(CommonUserRole)
        .filter(CommonUserRole.user_id == user_id, CommonUserRole.space_id == space_id)
        .first()
    )
    if not row:
        raise NotFoundError("该用户不是空间成员")
    db.delete(row)
    db.commit()


def member_output(db: Session, row: CommonUserRole) -> dict:
    user = (
        db.query(CommonUser)
        .filter(CommonUser.id == row.user_id, CommonUser.deleted_at.is_(None))
        .first()
    )
    return {
        "user_id": row.user_id,
        "username": user.username if user else "",
        "name": user.name if user else "",
        "org_type": user.org_type if user else None,
        "role_level": row.role_level,
        "role_name": ROLE_LEVEL_NAMES.get(row.role_level, row.role_level),
    }
