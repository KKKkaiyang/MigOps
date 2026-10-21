from fastapi import APIRouter

from app.core.response import ok

router = APIRouter(prefix="/b02/materials", tags=["b02-项目资料管理"])


@router.get("/_meta")
def meta():
    return ok(data={"module": "b02", "status": "stub"}, message="项目资料管理模块占位，待实现")
