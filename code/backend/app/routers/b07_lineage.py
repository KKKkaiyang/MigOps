"""b07 血缘管理接口。

空间业务表位于空间库（mig_<space_code>_db），经 get_space_db 路由；
权限校验经 get_db（common_user_role 位于公共库）。
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_space_db, require_space_member
from app.core.response import ok
from app.database import get_db
from app.models.user import CommonUser
from app.schemas.b07_lineage import (
    LineageImportIn,
    LineageOut,
    LineageParseIn,
    LineageWorkflowOptionsOut,
    LineageWorkflowOut,
)
from app.services import b07_lineage as svc

router = APIRouter(prefix="/b07", tags=["b07-血缘管理"])


def _dump(rows) -> List[dict]:
    return [LineageOut.model_validate(r).model_dump() for r in rows]


@router.get("/lineages")
def list_lineages(
    space_id: int,
    workflow: Optional[str] = Query(None, description="按工作流筛选"),
    keyword: Optional[str] = Query(None, description="表名模糊(输入/输出)"),
    table_type: Optional[str] = Query(None, description="表类型: 正式表/临时表"),
    db: Session = Depends(get_db),
    sdb: Session = Depends(get_space_db),
    user: CommonUser = Depends(get_current_user),
):
    """血缘边列表（含筛选）；临时表一并返回，由前端按图例开关控制展示。"""
    require_space_member(db, user, space_id)
    rows = svc.list_lineages(sdb, space_id, workflow=workflow, keyword=keyword, table_type=table_type)
    return ok(data=_dump(rows))


@router.post("/lineages/parse")
def parse_lineage(
    payload: LineageParseIn,
    space_id: int,
    db: Session = Depends(get_db),
    sdb: Session = Depends(get_space_db),
    user: CommonUser = Depends(get_current_user),
):
    """解析脚本为血缘边预览（不落库）。支持 SQL / PySpark。"""
    require_space_member(db, user, space_id)
    if not payload.code or not payload.code.strip():
        return ok(data=[])
    edges = svc.parse_script(payload.code, payload.lang)
    return ok(data=edges)


@router.post("/lineages/import")
def import_lineage(
    payload: LineageImportIn,
    space_id: int,
    db: Session = Depends(get_db),
    sdb: Session = Depends(get_space_db),
    user: CommonUser = Depends(get_current_user),
):
    """按工作流入库：add=仅插入；rebuild=逻辑删除该工作流旧边后重入。"""
    require_space_member(db, user, space_id)
    result = svc.import_lineages(sdb, space_id, payload, operator=str(user.id))
    return ok(data=result, message=f"已{payload.mode}工作流「{payload.workflow}」")


@router.get("/lineages/workflows")
def list_workflows(
    space_id: int,
    db: Session = Depends(get_db),
    sdb: Session = Depends(get_space_db),
    user: CommonUser = Depends(get_current_user),
):
    """工作流聚合列表（名称/涉及表数/入口表）。"""
    require_space_member(db, user, space_id)
    data = [LineageWorkflowOut(**w).model_dump() for w in svc.list_workflows(sdb, space_id)]
    return ok(data=data)


@router.get("/lineages/workflows/{workflow}/options")
def workflow_options(
    workflow: str,
    space_id: int,
    db: Session = Depends(get_db),
    sdb: Session = Depends(get_space_db),
    user: CommonUser = Depends(get_current_user),
):
    """某工作流下可选的任务/脚本/任务类型/项目（重建预填）。"""
    require_space_member(db, user, space_id)
    opt = svc.get_workflow_options(sdb, space_id, workflow)
    return ok(data=LineageWorkflowOptionsOut(**opt).model_dump())


@router.delete("/lineages/{lineage_id}")
def delete_lineage(
    lineage_id: int,
    space_id: int,
    db: Session = Depends(get_db),
    sdb: Session = Depends(get_space_db),
    user: CommonUser = Depends(get_current_user),
):
    """逻辑删除单条血缘边（修正误录）。"""
    require_space_member(db, user, space_id)
    svc.delete_lineage(sdb, space_id, lineage_id, operator=str(user.id))
    return ok(message="已删除该血缘边")


@router.delete("/lineages/workflows/{workflow}")
def delete_workflow_lineages(
    workflow: str,
    space_id: int,
    db: Session = Depends(get_db),
    sdb: Session = Depends(get_space_db),
    user: CommonUser = Depends(get_current_user),
):
    """逻辑删除某工作流的全部血缘边（批量，避免逐条删除的 N+1 请求）。"""
    require_space_member(db, user, space_id)
    deleted = svc.delete_workflow_lineages(sdb, space_id, workflow, operator=str(user.id))
    return ok(data={"workflow": workflow, "deleted": deleted}, message=f"已删除工作流「{workflow}」共 {deleted} 条")
