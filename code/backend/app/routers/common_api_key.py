"""个人中心 API 密钥路由（ak/sk 自助管理）：生成、列表、吊销、启用/停用。

仅本人可访问自身密钥（后端按当前登录用户过滤）。所有端点须携带
`Authorization: Bearer <token>` 网页登录态（不支持 ak/sk 互相管理自身）。

统一响应结构：`{ "code": 0, "message": "ok", "data": ..., "trace_id": "..." }`
常见错误码：40100 鉴权失败 / 40400 资源不存在 / 40000 业务错误。
"""

from typing import Dict

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.config import settings
from app.core.deps import get_current_user
from app.core.response import ApiResponse, ok
from app.database import get_db
from app.models.user import CommonUser
from app.schemas.api_key import ApiKeyCreated, ApiKeyOut
from app.services import api_key as svc

router = APIRouter(prefix="/common/users/me/api-keys", tags=["common-个人中心API密钥"])

_ERROR_RESPONSES: Dict[int, Dict] = {
    401: {"model": ApiResponse, "description": "鉴权失败（40100）：未登录或登录态失效"},
    404: {"model": ApiResponse, "description": "资源不存在（40400）：密钥不存在或已吊销"},
    400: {"model": ApiResponse, "description": "业务错误（40000）：如密钥不存在"},
}

_AUTH_DESC = "鉴权：须携带 `Authorization: Bearer <token>`（网页登录态）。"


@router.post(
    "",
    status_code=201,
    summary="生成 API 密钥",
    description="为当前登录用户生成一对 ak/sk。\n\n"
    + _AUTH_DESC
    + "\n\n- 返回的 `secret_key` 为**一次性明文**，仅在此接口展示，后端以 Fernet 加密存储，后续不可再查。\n"
    "- 请提示用户立即复制保存；遗失需吊销后重新生成。",
    response_model=ApiResponse[ApiKeyCreated],
    responses=_ERROR_RESPONSES,
)
def create(
    db: Session = Depends(get_db),
    user: CommonUser = Depends(get_current_user),
):
    obj, secret = svc.create_key(db, user.id, operator=str(user.id))
    return ok(
        data=ApiKeyCreated(
            id=obj.id,
            access_key=obj.access_key,
            secret_key=secret,
            status=obj.status,
        ),
        message="密钥已生成，secret_key 仅展示一次，请妥善保存",
    )


@router.get(
    "",
    summary="密钥列表",
    description="列出当前登录用户的有效（未吊销）密钥。\n\n"
    + _AUTH_DESC
    + "\n\n- `secret_key` 一律掩码，不会返回明文；如需使用请调用生成接口重新获取。\n"
    "- 按创建时间倒序返回。",
    response_model=ApiResponse[list[ApiKeyOut]],
    responses=_ERROR_RESPONSES,
)
def list_keys(
    db: Session = Depends(get_db),
    user: CommonUser = Depends(get_current_user),
):
    rows = svc.list_keys(db, user.id)
    return ok(data=[ApiKeyOut.model_validate(r) for r in rows])


@router.delete(
    "/{key_id}",
    summary="吊销密钥",
    description="逻辑吊销指定密钥（不可恢复，须重新生成）。\n\n"
    + _AUTH_DESC
    + "\n\n- 吊销后该 ak/sk 将无法用于任何接口签名（40100）。\n"
    "- 仅能吊销本人密钥。",
    response_model=ApiResponse,
    responses=_ERROR_RESPONSES,
)
def revoke(
    key_id: int,
    db: Session = Depends(get_db),
    user: CommonUser = Depends(get_current_user),
):
    svc.revoke_key(db, user.id, key_id, operator=str(user.id))
    return ok(message="密钥已吊销")


@router.patch(
    "/{key_id}",
    summary="启用/停用密钥",
    description="切换指定密钥的启用/停用状态（软开关，非删除）。\n\n"
    + _AUTH_DESC
    + "\n\n- 停用态的密钥签名校验将失败（40100）；启用后可恢复使用。\n"
    "- 仅能操作本人密钥。",
    response_model=ApiResponse[ApiKeyOut],
    responses=_ERROR_RESPONSES,
)
def toggle(
    key_id: int,
    db: Session = Depends(get_db),
    user: CommonUser = Depends(get_current_user),
):
    obj = svc.toggle_key(db, user.id, key_id, operator=str(user.id))
    return ok(data=ApiKeyOut.model_validate(obj), message="密钥状态已更新")
