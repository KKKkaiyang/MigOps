"""b08 skill 路由（平台级全局）：市场、上传、下载、我的 skill、删除、上下架。

同一套端点同时支持网页（Bearer Token）与 REST API（ak/sk HMAC 签名）。

鉴权方式（二选一）：
  - 网页端：请求头 `Authorization: Bearer <token>`
  - REST 端：请求头 `X-Access-Key` / `X-Timestamp`(毫秒) / `X-Nonce` / `X-Signature`
    其中签名串为 `METHOD\nPATH\nTIMESTAMP\nNONCE`，使用 secret_key 做 HMAC-SHA256。
    时间戳允许偏差 ±5 分钟，nonce 单次有效（防重放）。

统一响应结构：`{ "code": 0, "message": "ok", "data": ..., "trace_id": "..." }`
常见错误码：40100 鉴权失败 / 40300 无权限 / 40400 资源不存在 / 40000 业务错误。
"""

from typing import Dict

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.config import settings
from app.core.deps import get_actor, is_l0, require_self_or_l0
from app.core.response import ApiResponse, PageData, ok
from app.database import get_db
from app.models.user import CommonUser
from app.schemas.b08_skill import SkillCreate, SkillOut, SkillStatusUpdate
from app.services import b08_skill as svc
from app.utils.skill_storage import storage

router = APIRouter(prefix="/b08", tags=["b08-skill 技能管理"])

# 公共错误响应描述，复用于各端点
_ERROR_RESPONSES: Dict[int, Dict] = {
    401: {"model": ApiResponse, "description": "鉴权失败（40100）：未登录或 ak/sk 签名校验失败"},
    403: {"model": ApiResponse, "description": "无权限（40300）：删除/改状态需为作者本人或 L0 管理员"},
    404: {"model": ApiResponse, "description": "资源不存在（40400）：skill_code 不存在或已删除"},
    400: {"model": ApiResponse, "description": "业务错误（40000）：如 skill 名称已存在"},
}

_AUTH_DESC = (
    "鉴权：网页端 `Authorization: Bearer <token>`；"
    "REST 端 `X-Access-Key` / `X-Timestamp` / `X-Nonce` / `X-Signature`"
    "（签名串 `METHOD\\nPATH\\nTIMESTAMP\\nNONCE`，HMAC-SHA256）。"
)


@router.get(
    "/skills/market",
    summary="技能市场列表",
    description="分页浏览平台公开上架的 skill，支持关键词搜索与排序。\n\n"
    + _AUTH_DESC
    + "\n\n- `keyword`：按名称/简介模糊匹配（可选）。\n"
    "- `sort=heat`：按下载量降序；`sort=latest`：按创建时间降序。\n"
    "- 仅返回 `is_public=1 且 status=上架` 的 skill。",
    response_model=ApiResponse[PageData[SkillOut]],
    responses=_ERROR_RESPONSES,
)
def market(
    db: Session = Depends(get_db),
    actor: CommonUser = Depends(get_actor),
    keyword: str = Query(None, description="关键词（名称/简介模糊匹配）"),
    sort: str = Query("heat", pattern="^(heat|latest)$", description="排序：heat 下载量 / latest 最新"),
    page: int = Query(1, ge=1, description="页码，从 1 开始"),
    page_size: int = Query(settings.DEFAULT_PAGE_SIZE, ge=1, le=settings.MAX_PAGE_SIZE, description="每页条数"),
):
    rows, total = svc.list_market(db, page, page_size, keyword, sort)
    data = PageData[SkillOut](list=rows, total=total, page=page, page_size=page_size)
    return ok(data=data)


@router.get(
    "/skills/me",
    summary="我上传的 skill",
    description="分页列出当前登录用户上传的全部 skill（含私有、含下架）。\n\n" + _AUTH_DESC,
    response_model=ApiResponse[PageData[SkillOut]],
    responses=_ERROR_RESPONSES,
)
def mine(
    db: Session = Depends(get_db),
    actor: CommonUser = Depends(get_actor),
    page: int = Query(1, ge=1, description="页码，从 1 开始"),
    page_size: int = Query(settings.DEFAULT_PAGE_SIZE, ge=1, le=settings.MAX_PAGE_SIZE, description="每页条数"),
):
    rows, total = svc.my_skills(db, actor.id, page, page_size)
    data = PageData[SkillOut](list=rows, total=total, page=page, page_size=page_size)
    return ok(data=data)


@router.post(
    "/skills",
    status_code=201,
    summary="上传 skill",
    description="以 multipart/form-data 上传 skill 压缩包（.zip）并登记元数据。\n\n"
    + _AUTH_DESC
    + "\n\n- `name`：平台级唯一，1~128 字。\n"
    "- `is_public=1` 公开（所有人可下载）；`is_public=0` 私有（仅作者本人与 L0 可见/可下载）。\n"
    "- 上传成功后返回 skill_code，供后续下载/管理使用。",
    response_model=ApiResponse[SkillOut],
    responses=_ERROR_RESPONSES,
)
async def upload(
    db: Session = Depends(get_db),
    actor: CommonUser = Depends(get_actor),
    name: str = Form(..., max_length=128, description="skill 名称（平台级唯一）"),
    intro: str = Form(None, description="简介，市场截断展示，≤500 字"),
    is_public: int = Form(1, description="是否公开：1 公开 / 0 私有"),
    file: UploadFile = File(..., description="skill 压缩包（.zip），≤50MB"),
):
    payload = SkillCreate(name=name, intro=intro, is_public=is_public)
    content = await file.read()
    obj = svc.create_skill(
        db, payload, content, file.filename or "skill.zip", actor.id, operator=str(actor.id)
    )
    return ok(data=SkillOut.model_validate(obj), message="上传成功")


@router.get(
    "/skills/{skill_code}/download",
    summary="下载 skill 文件",
    description="下载指定 skill 的压缩包（流式二进制）。\n\n"
    + _AUTH_DESC
    + "\n\n- 公开 skill：任意已登录用户可下载。\n"
    "- 私有 skill：仅作者本人或 L0 管理员可下载（40300）。\n"
    "- 每次成功下载会计入下载量（同用户 5 分钟内去重，不计重复）。",
    responses={
        200: {"description": "下载成功，返回 application/zip 二进制流（Content-Disposition: attachment）"},
        401: {"model": ApiResponse, "description": "鉴权失败（40100）"},
        403: {"model": ApiResponse, "description": "无权限（40300）：私有 skill 非作者且非 L0"},
        404: {"model": ApiResponse, "description": "资源不存在（40400）：skill_code 不存在/已删除/已下架"},
    },
)
def download(
    skill_code: str,
    db: Session = Depends(get_db),
    actor: CommonUser = Depends(get_actor),
):
    skill = svc.ensure_downloadable(
        db, skill_code, actor_id=actor.id, is_actor_l0=is_l0(db, actor)
    )
    svc.record_download(db, skill, actor.id)
    return FileResponse(storage.abs_path(skill.file_path), filename=f"{skill.name}.zip")


@router.delete(
    "/skills/{skill_code}",
    summary="删除 skill",
    description="软删除指定 skill（逻辑删除）。\n\n"
    + _AUTH_DESC
    + "\n\n权限：仅作者本人或 L0 管理员可删除（40300）。",
    response_model=ApiResponse,
    responses=_ERROR_RESPONSES,
)
def delete_skill(
    skill_code: str,
    db: Session = Depends(get_db),
    actor: CommonUser = Depends(get_actor),
):
    skill = svc.get_by_code(db, skill_code)
    require_self_or_l0(db, actor, skill.author_user_id)
    svc.soft_delete(db, skill_code, operator=str(actor.id))
    return ok(message="已删除")


@router.patch(
    "/skills/{skill_code}/status",
    summary="上下架 skill",
    description="切换 skill 上架/下架状态。\n\n"
    + _AUTH_DESC
    + "\n\n- `status`：`上架` 或 `下架`。\n"
    "- 仅上架且公开的 skill 才会出现在市场列表。\n"
    "- 权限：仅作者本人或 L0 管理员（40300）。",
    response_model=ApiResponse[SkillOut],
    responses=_ERROR_RESPONSES,
)
def update_status(
    skill_code: str,
    payload: SkillStatusUpdate,
    db: Session = Depends(get_db),
    actor: CommonUser = Depends(get_actor),
):
    skill = svc.get_by_code(db, skill_code)
    require_self_or_l0(db, actor, skill.author_user_id)
    obj = svc.set_status(db, skill_code, payload.status, operator=str(actor.id))
    return ok(data=SkillOut.model_validate(obj), message="状态已更新")
