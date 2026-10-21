from fastapi import APIRouter

from app.core.response import ok

router = APIRouter(prefix="/b03/data-migrations", tags=["b03-数据迁移管理"])


@router.get("/_meta")
def meta():
    return ok(data={"module": "b03", "status": "stub"}, message="数据迁移管理模块占位，待实现")
