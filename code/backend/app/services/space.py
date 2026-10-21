import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.models.space import MigSpace
from app.schemas.space import SpaceCreate, SpaceUpdate


def _gen_code() -> str:
    return "SP" + uuid.uuid4().hex[:10].upper()


def create_space(db: Session, payload: SpaceCreate, operator: str) -> MigSpace:
    obj = MigSpace(
        space_code=_gen_code(),
        space_name=payload.space_name,
        customer_name=payload.customer_name,
        source_platform=payload.source_platform,
        target_platform=payload.target_platform,
        owner=payload.owner,
        remark=payload.remark,
        created_by=operator,
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def list_spaces(db: Session, page: int, page_size: int, keyword: Optional[str] = None):
    q = db.query(MigSpace).filter(MigSpace.deleted_at.is_(None))
    if keyword:
        q = q.filter(MigSpace.space_name.like(f"%{keyword}%"))
    total = q.count()
    rows = (
        q.order_by(MigSpace.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return rows, total


def get_space(db: Session, space_id: int) -> MigSpace:
    obj = db.query(MigSpace).filter(
        MigSpace.id == space_id, MigSpace.deleted_at.is_(None)
    ).first()
    if not obj:
        raise NotFoundError(f"空间不存在: {space_id}")
    return obj


def update_space(db: Session, space_id: int, payload: SpaceUpdate, operator: str) -> MigSpace:
    obj = get_space(db, space_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(obj, field, value)
    obj.updated_by = operator
    obj.updated_at = datetime.now()
    db.commit()
    db.refresh(obj)
    return obj


def archive_space(db: Session, space_id: int, operator: str) -> MigSpace:
    obj = get_space(db, space_id)
    obj.status = "archived"
    obj.updated_by = operator
    obj.updated_at = datetime.now()
    db.commit()
    db.refresh(obj)
    return obj
