from fastapi import APIRouter

from app.core.response import ok

router = APIRouter(prefix="/b04/tasks", tags=["b04-任务迁移管理"])


@router.get("/_meta")
def meta():
    return ok(data={"module": "b04", "status": "stub"}, message="任务迁移管理模块占位，待实现")
