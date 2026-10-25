"""skill 服务（b08，平台级全局）：市场列表、上传落盘、下载计数、我的 skill、删除、上下架。"""

import secrets
import string
import time
from datetime import datetime
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from app.config import settings
from app.core.exceptions import BizError, NotFoundError
from app.models.b08_skill import (
    SKILL_PRIVATE,
    SKILL_PUBLIC,
    SKILL_STATUS_OFFSHELF,
    SKILL_STATUS_ONSHELF,
    B08Skill,
)
from app.models.user import CommonUser
from app.schemas.b08_skill import SkillCreate, SkillOut
from app.utils.skill_storage import storage

_CODE_ALPHABET = string.ascii_letters + string.digits

# 下载计数防重复： (user_id, skill_code) -> 过期时间戳（秒）
_download_dedup: Dict[tuple, float] = {}


def _now() -> datetime:
    return datetime.now()


def _gen_skill_code(db: Session) -> str:
    for _ in range(10):
        code = "sk_" + "".join(secrets.choice(_CODE_ALPHABET) for _ in range(16))
        exists = (
            db.query(B08Skill)
            .filter(B08Skill.skill_code == code, B08Skill.deleted_at.is_(None))
            .first()
        )
        if not exists:
            return code
    raise BizError("生成 skill 编码失败，请重试")


def _build_out(db: Session, skill: B08Skill) -> SkillOut:
    out = SkillOut.model_validate(skill)
    user = db.query(CommonUser).filter(CommonUser.id == skill.author_user_id).first()
    out.author_name = user.name if user else None
    return out


def list_market(
    db: Session,
    page: int,
    page_size: int,
    keyword: Optional[str] = None,
    sort: str = "heat",
) -> tuple[List[SkillOut], int]:
    """市场公开列表：is_public=1 且 status=上架 且 未删除。"""
    q = db.query(B08Skill).filter(
        B08Skill.is_public == SKILL_PUBLIC,
        B08Skill.status == SKILL_STATUS_ONSHELF,
        B08Skill.deleted_at.is_(None),
    )
    if keyword:
        like = f"%{keyword}%"
        q = q.filter(B08Skill.name.like(like) | B08Skill.intro.like(like))
    total = q.count()
    if sort == "latest":
        q = q.order_by(B08Skill.created_at.desc())
    else:  # heat
        q = q.order_by(B08Skill.download_count.desc(), B08Skill.created_at.desc())
    rows = q.offset((page - 1) * page_size).limit(page_size).all()
    return [_build_out(db, r) for r in rows], total


def my_skills(db: Session, user_id: int, page: int, page_size: int) -> tuple[List[SkillOut], int]:
    q = db.query(B08Skill).filter(
        B08Skill.author_user_id == user_id, B08Skill.deleted_at.is_(None)
    )
    total = q.count()
    rows = (
        q.order_by(B08Skill.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return [_build_out(db, r) for r in rows], total


def create_skill(
    db: Session,
    payload: SkillCreate,
    content: bytes,
    filename: str,
    author_user_id: int,
    operator: str,
) -> B08Skill:
    """创建 skill：保存元数据 + 落盘文件。"""
    if len(content) > settings.SKILL_MAX_UPLOAD_BYTES:
        raise BizError(
            f"文件超出大小上限 {settings.SKILL_MAX_UPLOAD_BYTES // (1024 * 1024)}MB"
        )
    exists = (
        db.query(B08Skill)
        .filter(B08Skill.name == payload.name, B08Skill.deleted_at.is_(None))
        .first()
    )
    if exists:
        raise BizError(f"skill 名称已存在: {payload.name}")

    code = _gen_skill_code(db)
    version = "1.0.0"
    relative_path = f"{code}/{version}.zip"
    storage.save(relative_path, content)

    obj = B08Skill(
        skill_code=code,
        name=payload.name,
        intro=payload.intro,
        author_user_id=author_user_id,
        is_public=payload.is_public,
        status=SKILL_STATUS_ONSHELF,
        download_count=0,
        file_path=relative_path,
        file_size=len(content),
        version=version,
        created_by=operator,
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def get_by_code(db: Session, skill_code: str, include_private_for: Optional[int] = None) -> B08Skill:
    """按编码获取；include_private_for 为作者本人或 L0 时可取私有。"""
    obj = (
        db.query(B08Skill)
        .filter(B08Skill.skill_code == skill_code, B08Skill.deleted_at.is_(None))
        .first()
    )
    if not obj:
        raise NotFoundError("skill 不存在")
    if obj.is_public == SKILL_PRIVATE and include_private_for is None:
        raise NotFoundError("skill 不存在")
    return obj


def ensure_downloadable(
    db: Session, skill_code: str, actor_id: int, is_actor_l0: bool
) -> B08Skill:
    """下载可见性校验：公开全员；私有仅作者本人 + L0。"""
    obj = (
        db.query(B08Skill)
        .filter(B08Skill.skill_code == skill_code, B08Skill.deleted_at.is_(None))
        .first()
    )
    if not obj:
        raise NotFoundError("skill 不存在")
    if obj.is_public == SKILL_PRIVATE and not (obj.author_user_id == actor_id or is_actor_l0):
        raise NotFoundError("无权限下载该私有 skill")
    return obj


def record_download(db: Session, skill: B08Skill, actor_id: int) -> None:
    """下载计数 +1（同一用户 5 分钟内重复下载不重复累加）。"""
    now = time.time()
    key = (actor_id, skill.skill_code)
    if key in _download_dedup and _download_dedup[key] > now:
        return
    _download_dedup[key] = now + 300
    skill.download_count = (skill.download_count or 0) + 1
    db.commit()


def soft_delete(db: Session, skill_code: str, operator: str) -> None:
    obj = (
        db.query(B08Skill)
        .filter(B08Skill.skill_code == skill_code, B08Skill.deleted_at.is_(None))
        .first()
    )
    if not obj:
        raise NotFoundError("skill 不存在")
    obj.deleted_at = _now()
    obj.updated_by = operator
    db.commit()


def set_status(db: Session, skill_code: str, status: str, operator: str) -> B08Skill:
    if status not in (SKILL_STATUS_ONSHELF, SKILL_STATUS_OFFSHELF):
        raise BizError("非法的状态值")
    obj = (
        db.query(B08Skill)
        .filter(B08Skill.skill_code == skill_code, B08Skill.deleted_at.is_(None))
        .first()
    )
    if not obj:
        raise NotFoundError("skill 不存在")
    obj.status = status
    obj.updated_by = operator
    obj.updated_at = _now()
    db.commit()
    db.refresh(obj)
    return obj
