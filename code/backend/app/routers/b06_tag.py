"""b06 标签管理接口。

标签主表（b06_tag）与标签查看归属本模块；任务打标签（跨模块关联 b04 任务）由 b04 接口调用
app.services.b06_tag 完成，本模块仅提供标签自身的维护与查看。
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_space_db, require_space_member
from app.core.response import ok
from app.database import get_db
from app.models.user import CommonUser
from app.schemas.b06_tag import TagCreate, TagOut, TagUpdate
from app.services import b06_tag as svc

router = APIRouter(prefix="/b06", tags=["b06-标签管理"])


# ── 标签管理（空间级） ──
@router.get("/tags")
def list_tags(
    space_id: int,
    db: Session = Depends(get_db),
    sdb: Session = Depends(get_space_db),
    user: CommonUser = Depends(get_current_user),
):
    require_space_member(db, user, space_id)
    return ok(data=svc.list_tags(sdb, space_id))


@router.post("/tags", status_code=201)
def create_tag(
    space_id: int,
    payload: TagCreate,
    db: Session = Depends(get_db),
    sdb: Session = Depends(get_space_db),
    user: CommonUser = Depends(get_current_user),
):
    require_space_member(db, user, space_id)
    obj = svc.create_tag(sdb, space_id, payload, operator=str(user.id))
    return ok(data=TagOut.model_validate(obj), message="标签已创建")


@router.get("/tags/{tag_id}")
def get_tag(
    space_id: int,
    tag_id: int,
    db: Session = Depends(get_db),
    sdb: Session = Depends(get_space_db),
    user: CommonUser = Depends(get_current_user),
):
    require_space_member(db, user, space_id)
    return ok(data=TagOut.model_validate(svc.get_tag(sdb, space_id, tag_id)))


@router.put("/tags/{tag_id}")
def update_tag(
    space_id: int,
    tag_id: int,
    payload: TagUpdate,
    db: Session = Depends(get_db),
    sdb: Session = Depends(get_space_db),
    user: CommonUser = Depends(get_current_user),
):
    require_space_member(db, user, space_id)
    svc.update_tag(sdb, space_id, tag_id, payload, operator=str(user.id))
    return ok(message="更新成功")


@router.delete("/tags/{tag_id}")
def delete_tag(
    space_id: int,
    tag_id: int,
    db: Session = Depends(get_db),
    sdb: Session = Depends(get_space_db),
    user: CommonUser = Depends(get_current_user),
):
    require_space_member(db, user, space_id)
    svc.delete_tag(sdb, space_id, tag_id)
    return ok(message="标签已删除")
