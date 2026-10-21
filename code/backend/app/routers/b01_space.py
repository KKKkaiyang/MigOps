from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.config import settings
from app.core.response import PageData, ok
from app.database import get_db
from app.schemas.space import SpaceCreate, SpaceOut, SpaceUpdate
from app.services import space as svc

router = APIRouter(prefix="/b01/spaces", tags=["b01-项目空间管理"])


@router.post("", status_code=201)
def create_space(payload: SpaceCreate, db: Session = Depends(get_db)):
    obj = svc.create_space(db, payload, operator="system")
    return ok(data=SpaceOut.model_validate(obj), message="创建成功")


@router.get("")
def list_spaces(
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(settings.DEFAULT_PAGE_SIZE, ge=1, le=settings.MAX_PAGE_SIZE),
    keyword: str = Query(None),
):
    rows, total = svc.list_spaces(db, page, page_size, keyword)
    data = PageData[SpaceOut](
        list=[SpaceOut.model_validate(r) for r in rows],
        total=total,
        page=page,
        page_size=page_size,
    )
    return ok(data=data)


@router.get("/{space_id}")
def get_space(space_id: int, db: Session = Depends(get_db)):
    obj = svc.get_space(db, space_id)
    return ok(data=SpaceOut.model_validate(obj))


@router.put("/{space_id}")
def update_space(space_id: int, payload: SpaceUpdate, db: Session = Depends(get_db)):
    obj = svc.update_space(db, space_id, payload, operator="system")
    return ok(data=SpaceOut.model_validate(obj), message="更新成功")


@router.post("/{space_id}/archive")
def archive_space(space_id: int, db: Session = Depends(get_db)):
    obj = svc.archive_space(db, space_id, operator="system")
    return ok(data=SpaceOut.model_validate(obj), message="已归档")
