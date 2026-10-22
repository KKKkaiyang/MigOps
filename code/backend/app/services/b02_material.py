"""b02 项目资料管理服务：分类、资料索引、markdown 密码保护。

密码策略（确认决策 D10 / D16）：
- 查看密码仅存 bcrypt 哈希，NULL = 无需密码；
- 查看/下载需有效 view_token，编辑免密；
- 连续错误 VIEW_PWD_MAX_FAILS 次锁定 VIEW_PWD_LOCK_MINUTES 分钟。
"""

import logging
import math
from datetime import datetime, timedelta
from typing import List, Optional, Tuple

from sqlalchemy.orm import Session

from app.config import settings
from app.core.exceptions import BizError, ForbiddenError, NotFoundError
from app.core.security import (
    create_view_token,
    decode_view_token,
    hash_password,
    verify_password,
)
from app.models.b02_material import (
    MATERIAL_TYPE_EXTERNAL_LINK,
    MATERIAL_TYPE_MARKDOWN,
    MATERIAL_TYPE_PLATFORM_LEDGER,
    PRESET_CATEGORIES,
    B02Category,
    B02Material,
)
from app.schemas.b02_material import (
    CategoryCreate,
    CategoryOut,
    CategoryUpdate,
    MaterialCreate,
    MaterialOut,
    MaterialUpdate,
)

logger = logging.getLogger("migops")


# ── 预置分类种子 ──
def seed_preset_categories(sdb: Session, space_id: int) -> None:
    """种子预置资料分类（幂等，空间结构初始化时调用）。"""
    existing = {
        c.name
        for c in sdb.query(B02Category)
        .filter(B02Category.space_id == space_id, B02Category.deleted_at.is_(None))
        .all()
    }
    created = False
    for name, sort_no in PRESET_CATEGORIES:
        if name in existing:
            continue
        sdb.add(
            B02Category(space_id=space_id, name=name, sort_no=sort_no, is_preset=1)
        )
        created = True
    if created:
        sdb.commit()


# ── 输出转换 ──
def category_out(obj: B02Category, material_count: int = 0) -> CategoryOut:
    out = CategoryOut.model_validate(obj)
    out.material_count = material_count
    return out


def material_out(obj: B02Material, include_content: bool = False) -> MaterialOut:
    out = MaterialOut.model_validate(obj)
    out.has_password = bool(obj.view_password_hash)
    if not include_content:
        out.content = None
    return out


# ── 分类 ──
def list_categories(sdb: Session, space_id: int) -> List[B02Category]:
    return (
        sdb.query(B02Category)
        .filter(B02Category.space_id == space_id, B02Category.deleted_at.is_(None))
        .order_by(B02Category.sort_no.asc(), B02Category.id.asc())
        .all()
    )


def count_materials_by_category(sdb: Session, space_id: int) -> dict:
    rows = (
        sdb.query(B02Material.category_id, B02Material.id)
        .filter(B02Material.space_id == space_id, B02Material.deleted_at.is_(None))
        .all()
    )
    counts: dict = {}
    for category_id, _ in rows:
        counts[category_id] = counts.get(category_id, 0) + 1
    return counts


def get_category(sdb: Session, space_id: int, category_id: int) -> B02Category:
    obj = (
        sdb.query(B02Category)
        .filter(
            B02Category.id == category_id,
            B02Category.space_id == space_id,
            B02Category.deleted_at.is_(None),
        )
        .first()
    )
    if not obj:
        raise NotFoundError(f"分类不存在: {category_id}")
    return obj


def create_category(
    sdb: Session, space_id: int, payload: CategoryCreate, operator: str
) -> B02Category:
    if (
        sdb.query(B02Category)
        .filter(
            B02Category.space_id == space_id,
            B02Category.name == payload.name,
            B02Category.deleted_at.is_(None),
        )
        .first()
    ):
        raise BizError(f"分类名称已存在: {payload.name}")
    obj = B02Category(
        space_id=space_id,
        name=payload.name,
        sort_no=payload.sort_no,
        is_preset=0,
        created_by=operator,
    )
    sdb.add(obj)
    sdb.commit()
    sdb.refresh(obj)
    return obj


def update_category(
    sdb: Session, space_id: int, category_id: int, payload: CategoryUpdate, operator: str
) -> B02Category:
    obj = get_category(sdb, space_id, category_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(obj, field, value)
    obj.updated_by = operator
    obj.updated_at = datetime.now()
    sdb.commit()
    sdb.refresh(obj)
    return obj


def delete_category(sdb: Session, space_id: int, category_id: int) -> None:
    obj = get_category(sdb, space_id, category_id)
    if obj.is_preset:
        raise BizError("预置分类不可删除")
    obj.deleted_at = datetime.now()
    # 分类下资料置为未分类，不删除资料
    (
        sdb.query(B02Material)
        .filter(
            B02Material.space_id == space_id,
            B02Material.category_id == category_id,
            B02Material.deleted_at.is_(None),
        )
        .update({B02Material.category_id: None})
    )
    sdb.commit()


# ── 资料 ──
def _validate_type_values(
    material_type: Optional[str],
    url: Optional[str],
    content: Optional[str],
    target_module: Optional[str],
) -> None:
    """按类型校验必填内容（创建与更新合并后统一校验）。"""
    if material_type == MATERIAL_TYPE_EXTERNAL_LINK and not url:
        raise BizError("外部链接类型必须填写链接地址")
    if material_type == MATERIAL_TYPE_MARKDOWN and not content:
        raise BizError("Markdown 类型必须填写资料内容")
    if material_type == MATERIAL_TYPE_PLATFORM_LEDGER and not target_module:
        raise BizError("平台台账类型必须选择跳转目标")


def list_materials(
    sdb: Session,
    space_id: int,
    page: int,
    page_size: int,
    keyword: Optional[str] = None,
    material_type: Optional[str] = None,
    category_id: Optional[int] = None,
) -> Tuple[List[B02Material], int]:
    """资料列表：置顶优先、更新时间倒序；不返回 content（D8）。"""
    q = sdb.query(B02Material).filter(
        B02Material.space_id == space_id, B02Material.deleted_at.is_(None)
    )
    if keyword:
        q = q.filter(B02Material.name.like(f"%{keyword}%"))
    if material_type:
        q = q.filter(B02Material.type == material_type)
    if category_id:
        q = q.filter(B02Material.category_id == category_id)
    total = q.count()
    rows = (
        q.order_by(
            B02Material.sort_no.desc(),
            B02Material.updated_at.desc(),
            B02Material.id.desc(),
        )
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return rows, total


def get_material(sdb: Session, space_id: int, material_id: int) -> B02Material:
    obj = (
        sdb.query(B02Material)
        .filter(
            B02Material.id == material_id,
            B02Material.space_id == space_id,
            B02Material.deleted_at.is_(None),
        )
        .first()
    )
    if not obj:
        raise NotFoundError(f"资料不存在: {material_id}")
    return obj


def create_material(
    sdb: Session, space_id: int, payload: MaterialCreate, operator: str
) -> B02Material:
    _validate_type_values(payload.type, payload.url, payload.content, payload.target_module)
    obj = B02Material(
        space_id=space_id,
        category_id=payload.category_id,
        name=payload.name,
        type=payload.type,
        url=payload.url,
        target_module=payload.target_module,
        content=payload.content,
        description=payload.description,
        sort_no=payload.sort_no,
        created_by=operator,
    )
    if payload.view_password:
        obj.view_password_hash = hash_password(payload.view_password)
    sdb.add(obj)
    sdb.commit()
    sdb.refresh(obj)
    return obj


def update_material(
    sdb: Session, space_id: int, material_id: int, payload: MaterialUpdate, operator: str
) -> B02Material:
    obj = get_material(sdb, space_id, material_id)
    data = payload.model_dump(exclude_unset=True)
    # 合并后的最终值做类型必填校验，避免把必填内容清空
    _validate_type_values(
        data.get("type", obj.type),
        data.get("url", obj.url),
        data.get("content", obj.content),
        data.get("target_module", obj.target_module),
    )
    if "view_password" in data:
        pwd = data.pop("view_password")
        obj.view_password_hash = hash_password(pwd) if pwd else None
        # 改密后重置失败计数与锁定
        obj.view_pwd_fail_count = 0
        obj.view_pwd_locked_until = None
    for field, value in data.items():
        setattr(obj, field, value)
    obj.updated_by = operator
    obj.updated_at = datetime.now()
    sdb.commit()
    sdb.refresh(obj)
    return obj


def delete_material(sdb: Session, space_id: int, material_id: int) -> None:
    obj = get_material(sdb, space_id, material_id)
    obj.deleted_at = datetime.now()
    sdb.commit()


# ── 查看密码 ──
def ensure_view_allowed(
    sdb: Session,
    space_id: int,
    user_id: int,
    obj: B02Material,
    view_token: Optional[str],
) -> None:
    """查看/下载准入：无密码放行；有密码要求有效 view_token。"""
    if not obj.view_password_hash:
        return
    if not view_token or not decode_view_token(view_token, obj.id, user_id, space_id):
        raise ForbiddenError("该资料已设置查看密码，请先验证密码")


def verify_material_password(
    sdb: Session, space_id: int, user_id: int, material_id: int, password: str
) -> dict:
    """校验查看密码：成功签发 view_token；失败累计，达阈值锁定。"""
    obj = get_material(sdb, space_id, material_id)
    if not obj.view_password_hash:
        raise BizError("该资料未设置查看密码")
    if obj.view_pwd_locked_until and obj.view_pwd_locked_until > datetime.now():
        remain_seconds = (obj.view_pwd_locked_until - datetime.now()).total_seconds()
        remain_minutes = max(1, math.ceil(remain_seconds / 60))
        raise BizError(f"密码错误次数过多，已锁定，请 {remain_minutes} 分钟后再试")
    if verify_password(password, obj.view_password_hash):
        obj.view_pwd_fail_count = 0
        obj.view_pwd_locked_until = None
        sdb.commit()
        return {
            "view_token": create_view_token(obj.id, user_id, space_id),
            "expires_in": settings.VIEW_TOKEN_EXPIRE_MINUTES * 60,
        }
    obj.view_pwd_fail_count += 1
    if obj.view_pwd_fail_count >= settings.VIEW_PWD_MAX_FAILS:
        obj.view_pwd_locked_until = datetime.now() + timedelta(
            minutes=settings.VIEW_PWD_LOCK_MINUTES
        )
        sdb.commit()
        raise BizError(
            f"密码连续错误 {settings.VIEW_PWD_MAX_FAILS} 次，"
            f"已锁定 {settings.VIEW_PWD_LOCK_MINUTES} 分钟"
        )
    sdb.commit()
    remaining = settings.VIEW_PWD_MAX_FAILS - obj.view_pwd_fail_count
    raise BizError(f"密码错误，还可尝试 {remaining} 次")
