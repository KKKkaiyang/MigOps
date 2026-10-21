from fastapi import APIRouter

from app.core.response import ok

router = APIRouter(prefix="/b05/checks", tags=["b05-数据校验管理"])


@router.get("/_meta")
def meta():
    return ok(data={"module": "b05", "status": "stub"}, message="数据校验管理模块占位，待实现")
