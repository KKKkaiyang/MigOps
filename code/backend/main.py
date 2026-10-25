import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.core.exceptions import BizError
from app.core.response import ApiResponse
from app.routers import all_routers

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("migops")

app = FastAPI(title=f"{settings.APP_NAME} API", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def bootstrap() -> None:
    """启动引导：确保公共库与表存在，并种子默认管理员账号。"""
    from app.database import SessionLocal, init_models_with_retry
    from app.models.role import CommonUserRole
    from app.models.user import USER_STATUS_ENABLED, CommonUser
    from app.core.security import hash_password

    init_models_with_retry()
    db = SessionLocal()
    try:
        # 引导：为存量空间补建空间业务表与预置数据（幂等）
        try:
            from app.services.space import ensure_existing_spaces_initialized

            ensure_existing_spaces_initialized(db)
        except Exception as exc:  # noqa: BLE001
            logger.warning("存量空间结构初始化跳过: %s", exc)

        exists = (
            db.query(CommonUser)
            .filter(
                CommonUser.username == settings.DEFAULT_ADMIN_USERNAME,
                CommonUser.deleted_at.is_(None),
            )
            .first()
        )
        if not exists:
            admin = CommonUser(
                username=settings.DEFAULT_ADMIN_USERNAME,
                password=hash_password(settings.DEFAULT_ADMIN_PASSWORD),
                name="系统管理员",
                org_type="内部",
                status=USER_STATUS_ENABLED,
                must_change_password=0,
                created_by="system",
            )
            db.add(admin)
            db.commit()
            db.refresh(admin)
            db.add(
                CommonUserRole(user_id=admin.id, role_level="L0", space_id=None, created_by="system")
            )
            db.commit()
            logger.info("已创建默认管理员账号: %s", settings.DEFAULT_ADMIN_USERNAME)
    finally:
        db.close()


@app.exception_handler(BizError)
async def biz_handler(request: Request, exc: BizError):
    return JSONResponse(
        status_code=200,
        content=ApiResponse(code=exc.code, message=exc.message).model_dump(),
    )


def _json_safe_errors(errors) -> list:
    """将校验错误转为可 JSON 序列化的结构。

    exc.errors() 的 ctx 中可能内嵌 ValueError 实例（自定义 field_validator 抛出），
    直接 json.dumps 会 500，需把其中的异常对象转为字符串。
    """
    safe = []
    for err in errors:
        item = dict(err)
        ctx = item.get("ctx")
        if isinstance(ctx, dict):
            item["ctx"] = {
                k: str(v) if isinstance(v, BaseException) else v for k, v in ctx.items()
            }
        safe.append(item)
    return safe


@app.exception_handler(RequestValidationError)
async def validation_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=200,
        content=ApiResponse(
            code=42200, message="参数校验失败", data=_json_safe_errors(exc.errors())
        ).model_dump(),
    )


for r in all_routers:
    app.include_router(r, prefix=settings.API_V1_PREFIX)


# ── OpenAPI 标注：为 b03/b04/b05/b07 补充 ak/sk 双鉴权说明（AK-02 / BRD §4.5 / §9.10 D2） ──
# 这些空间业务模块已统一改用 `get_actor`，支持「网页登录态 / REST API 签名」双鉴权；
# 与其在 ~60 个端点逐一标注，这里在生成 schema 后按 tag 统一 enrich，源头单一、易维护。
_DUAL_AUTH_TAGS = {"b03-数据迁移管理", "b04-任务迁移管理", "b05-数据校验管理", "b07-血缘管理"}
_DUAL_AUTH_NOTE = (
    "\n\n**鉴权（双鉴权）**：支持网页登录态 `Authorization: Bearer <token>` "
    "与 REST API `X-Access-Key` / `X-Timestamp`(毫秒) / `X-Nonce` / `X-Signature`"
    "（HMAC-SHA256，待签串 `METHOD\\nPATH\\nTIMESTAMP\\nNONCE`）两种调用方式，由 `get_actor` 统一判定。"
    "空间隔离业务须操作人为目标空间成员且具对应角色（详见 BRD §4.5 / §9.10 D2）。"
)
_DUAL_AUTH_HEADERS = [
    {"name": "X-Access-Key", "in": "header", "required": False, "schema": {"type": "string"}, "description": "REST API 访问标识"},
    {"name": "X-Timestamp", "in": "header", "required": False, "schema": {"type": "string"}, "description": "毫秒时间戳（与服务器偏差 ≤5 分钟）"},
    {"name": "X-Nonce", "in": "header", "required": False, "schema": {"type": "string"}, "description": "随机串（5 分钟内单次有效，防重放）"},
    {"name": "X-Signature", "in": "header", "required": False, "schema": {"type": "string"}, "description": "HMAC-SHA256 签名"},
]
_DUAL_AUTH_RESPONSES = {
    "401": {"description": "鉴权失败（40100）：未登录或 ak/sk 签名校验失败"},
    "403": {"description": "无权限（40300）：非目标空间成员 / 角色不足"},
}


def _enrich_dual_auth(schema: dict) -> dict:
    for path_item in schema.get("paths", {}).values():
        for op in path_item.values():
            if not isinstance(op, dict):
                continue
            if not set(op.get("tags", [])) & _DUAL_AUTH_TAGS:
                continue
            op["description"] = (op.get("description") or "") + _DUAL_AUTH_NOTE
            responses = op.setdefault("responses", {})
            for code, val in _DUAL_AUTH_RESPONSES.items():
                responses.setdefault(code, val)
            existing = {p["name"] for p in op.get("parameters", []) if isinstance(p, dict)}
            for h in _DUAL_AUTH_HEADERS:
                if h["name"] not in existing:
                    op.setdefault("parameters", []).append(h)
    return schema


_enriched_schema = None
_original_openapi = app.openapi


def custom_openapi():
    global _enriched_schema
    if _enriched_schema is not None:
        return _enriched_schema
    _enriched_schema = _enrich_dual_auth(_original_openapi())
    return _enriched_schema


app.openapi = custom_openapi


@app.get("/health")
def health():
    return {"status": "ok", "db_type": settings.DB_TYPE}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=settings.PORT, reload=True)
