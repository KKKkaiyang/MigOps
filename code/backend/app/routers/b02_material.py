"""b02 项目资料管理接口。

空间业务表位于空间库（mig_<space_code>_db），经 get_space_db 路由；
权限校验经 get_db（common_user_role 位于公共库）。
"""

import re
from typing import Optional
from urllib.parse import quote

from fastapi import APIRouter, Depends, Header, Query, Response
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_space_db, require_space_member
from app.core.exceptions import BizError
from app.core.response import PageData, ok
from app.database import get_db
from app.models.b02_material import MATERIAL_TYPE_MARKDOWN
from app.models.user import CommonUser
from app.schemas.b02_material import (
    CategoryCreate,
    CategoryUpdate,
    MaterialCreate,
    MaterialUpdate,
    VerifyPasswordIn,
)
from app.services import b02_material as svc

router = APIRouter(prefix="/b02", tags=["b02-项目资料管理"])

# 下载文件名净化：仅保留中英文、数字与 . _ -，其余替换为下划线
_SAFE_FILENAME_RE = re.compile(r"[^0-9A-Za-z._\-\u4e00-\u9fff]+")


def _safe_download_name(name: str) -> str:
    cleaned = _SAFE_FILENAME_RE.sub("_", name).strip("._-")
    return f"{cleaned[:80] or 'material'}.md"


# ── 资料索引 ──
@router.get("/materials")
def list_materials(
    space_id: int,
    db: Session = Depends(get_db),
    sdb: Session = Depends(get_space_db),
    user: CommonUser = Depends(get_current_user),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    keyword: str = Query(None),
    type: str = Query(None),
    category_id: int = Query(None),
):
    require_space_member(db, user, space_id)
    rows, total = svc.list_materials(sdb, space_id, page, page_size, keyword, type, category_id)
    data = PageData[svc.MaterialOut](
        # 列表不返回 content（确认决策 D8）
        list=[svc.material_out(r) for r in rows],
        total=total,
        page=page,
        page_size=page_size,
    )
    return ok(data=data)


@router.post("/materials", status_code=201)
def create_material(
    space_id: int,
    payload: MaterialCreate,
    db: Session = Depends(get_db),
    sdb: Session = Depends(get_space_db),
    user: CommonUser = Depends(get_current_user),
):
    require_space_member(db, user, space_id)
    obj = svc.create_material(sdb, space_id, payload, operator=str(user.id))
    return ok(data=svc.material_out(obj), message="创建成功")


@router.get("/materials/{material_id}")
def get_material(
    space_id: int,
    material_id: int,
    db: Session = Depends(get_db),
    sdb: Session = Depends(get_space_db),
    user: CommonUser = Depends(get_current_user),
    x_view_token: Optional[str] = Header(None),
):
    """资料详情：markdown 有密码时需携带有效 view_token（X-View-Token）。"""
    require_space_member(db, user, space_id)
    obj = svc.get_material(sdb, space_id, material_id)
    svc.ensure_view_allowed(sdb, space_id, user.id, obj, x_view_token)
    return ok(data=svc.material_out(obj, include_content=True))


@router.put("/materials/{material_id}")
def update_material(
    space_id: int,
    material_id: int,
    payload: MaterialUpdate,
    db: Session = Depends(get_db),
    sdb: Session = Depends(get_space_db),
    user: CommonUser = Depends(get_current_user),
):
    # 编辑免密（确认决策 D4）
    require_space_member(db, user, space_id)
    obj = svc.update_material(sdb, space_id, material_id, payload, operator=str(user.id))
    return ok(data=svc.material_out(obj), message="更新成功")


@router.delete("/materials/{material_id}")
def delete_material(
    space_id: int,
    material_id: int,
    db: Session = Depends(get_db),
    sdb: Session = Depends(get_space_db),
    user: CommonUser = Depends(get_current_user),
):
    require_space_member(db, user, space_id)
    svc.delete_material(sdb, space_id, material_id)
    return ok(message="删除成功")


@router.post("/materials/{material_id}/verify-password")
def verify_password(
    space_id: int,
    material_id: int,
    payload: VerifyPasswordIn,
    db: Session = Depends(get_db),
    sdb: Session = Depends(get_space_db),
    user: CommonUser = Depends(get_current_user),
):
    require_space_member(db, user, space_id)
    result = svc.verify_material_password(
        sdb, space_id, user.id, material_id, payload.password
    )
    return ok(data=result, message="验证成功")


@router.get("/materials/{material_id}/download")
def download_material(
    space_id: int,
    material_id: int,
    db: Session = Depends(get_db),
    sdb: Session = Depends(get_space_db),
    user: CommonUser = Depends(get_current_user),
    view_token: str = Query(None),
):
    """下载 markdown 原文（.md）；有密码时需有效 view_token。"""
    require_space_member(db, user, space_id)
    obj = svc.get_material(sdb, space_id, material_id)
    if obj.type != MATERIAL_TYPE_MARKDOWN:
        raise BizError("仅 Markdown 资料支持下载")
    svc.ensure_view_allowed(sdb, space_id, user.id, obj, view_token)
    filename = _safe_download_name(obj.name)
    return Response(
        content=obj.content or "",
        media_type="text/markdown; charset=utf-8",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"
        },
    )


# ── 资料分类 ──
@router.get("/categories")
def list_categories(
    space_id: int,
    db: Session = Depends(get_db),
    sdb: Session = Depends(get_space_db),
    user: CommonUser = Depends(get_current_user),
):
    require_space_member(db, user, space_id)
    rows = svc.list_categories(sdb, space_id)
    counts = svc.count_materials_by_category(sdb, space_id)
    data = [svc.category_out(r, counts.get(r.id, 0)) for r in rows]
    return ok(data=data)


@router.post("/categories", status_code=201)
def create_category(
    space_id: int,
    payload: CategoryCreate,
    db: Session = Depends(get_db),
    sdb: Session = Depends(get_space_db),
    user: CommonUser = Depends(get_current_user),
):
    require_space_member(db, user, space_id)
    obj = svc.create_category(sdb, space_id, payload, operator=str(user.id))
    return ok(data=svc.category_out(obj), message="创建成功")


@router.put("/categories/{category_id}")
def update_category(
    space_id: int,
    category_id: int,
    payload: CategoryUpdate,
    db: Session = Depends(get_db),
    sdb: Session = Depends(get_space_db),
    user: CommonUser = Depends(get_current_user),
):
    require_space_member(db, user, space_id)
    obj = svc.update_category(sdb, space_id, category_id, payload, operator=str(user.id))
    return ok(data=svc.category_out(obj), message="更新成功")


@router.delete("/categories/{category_id}")
def delete_category(
    space_id: int,
    category_id: int,
    db: Session = Depends(get_db),
    sdb: Session = Depends(get_space_db),
    user: CommonUser = Depends(get_current_user),
):
    require_space_member(db, user, space_id)
    svc.delete_category(sdb, space_id, category_id)
    return ok(message="删除成功")
