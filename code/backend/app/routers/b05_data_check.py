"""b05 数据校验管理接口：校验概览（最新/近7天）、双模板导入、导入模板下载。

依据《数据校验-数据校验结果导入与刷新需求》V1.0：
- `GET /b05/checks`：数据校验列表（b03 库表清单为行 + 最新校验结果 + 近7天序列）；
- `POST /b05/checks/import`：导入校验结果（默认模板 / 腾讯数据校验工具模板），
  按 data_date 批量 upsert 后自动刷新任务数据校验结果；
- `GET /b05/checks/import-template`：下载导入模板。

空间业务表位于空间库（mig_<space_code>_db），经 get_space_db 路由；
权限校验经 get_db（common_user_role 位于公共库）。
鉴权：统一 `get_actor` 依赖，支持网页登录态（Bearer）与 REST API（ak/sk HMAC 签名）
双鉴权；空间隔离业务经 `require_space_member` 校验成员/角色。
"""

from datetime import date
from typing import List, Optional, Tuple
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Query, Response, UploadFile
from sqlalchemy.orm import Session

from app.core.deps import get_actor, get_space_db, require_space_member
from app.core.response import PageData, ok
from app.database import get_db
from app.models.b05_data_check import CHECK_TEMPLATE_DEFAULT, CHECK_TEMPLATE_TENCENT
from app.models.user import CommonUser
from app.schemas.b05_data_check import (
    CheckOverviewOut,
    CheckRefreshResult,
    CheckResultByTable,
    CheckResultImportResult,
    CheckResultsByTablesOut,
)
from app.services import b05_data_check as svc
from app.utils.excel import XLSX_MEDIA_TYPE

router = APIRouter(prefix="/b05/checks", tags=["b05-数据校验管理"])


def _xlsx_response(content: bytes, filename: str) -> Response:
    return Response(
        content=content,
        media_type=XLSX_MEDIA_TYPE,
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"
        },
    )


@router.get("")
def list_checks(
    space_id: int,
    db: Session = Depends(get_db),
    sdb: Session = Depends(get_space_db),
    user: CommonUser = Depends(get_actor),
    scenario_id: Optional[int] = Query(None, description="b03 迁移场景ID（为空=空间内全部场景）"),
    keyword: Optional[str] = Query(None, description="关键词：库名/表名/目标库表模糊匹配"),
    result: Optional[str] = Query(None, description="按最新校验结果过滤：通过/不通过/无校验结果"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
):
    """数据校验列表：数据迁移清单全部库表 + 最新校验结果 + 近7天校验结果（D2/D8）。"""
    require_space_member(db, user, space_id)
    rows, total = svc.list_checks(
        sdb, space_id, scenario_id, keyword, result, page, page_size
    )
    data = PageData[CheckOverviewOut](
        list=[CheckOverviewOut(**r) for r in rows],
        total=total,
        page=page,
        page_size=page_size,
    )
    return ok(data=data)


@router.post("/import")
def import_checks(
    space_id: int,
    db: Session = Depends(get_db),
    sdb: Session = Depends(get_space_db),
    user: CommonUser = Depends(get_actor),
    file: UploadFile = File(...),
    data_date: date = Query(..., description="校验结果所属日期（批量写入本次导入，不晚于今天）"),
    template: str = Query("default", description="导入模板: default=默认模板; tencent=腾讯数据校验工具模板"),
    scenario_id: Optional[int] = Query(None, description="当前 b03 迁移场景ID（用于清单外库表统计）"),
):
    """导入数据校验结果（xls/csv/xlsx）：按数据日期 upsert，并自动刷新任务数据校验结果。"""
    require_space_member(db, user, space_id)
    result = svc.import_check_results(
        sdb, space_id, file, data_date, template, operator=str(user.id), scenario_id=scenario_id
    )
    return ok(data=CheckResultImportResult(**result), message="导入完成")


@router.get("/import-template")
def import_template(
    space_id: int,
    db: Session = Depends(get_db),
    sdb: Session = Depends(get_space_db),
    user: CommonUser = Depends(get_actor),
    template: str = Query("default", description="default=默认模板; tencent=腾讯数据校验工具模板"),
):
    """下载校验结果导入模板（默认模板 / 腾讯数据校验工具模板）。"""
    require_space_member(db, user, space_id)
    if template not in ("default", "tencent"):
        from app.core.exceptions import BizError

        raise BizError(f"非法的导入模板: {template}")
    if template == CHECK_TEMPLATE_DEFAULT:
        content = svc.check_template_xlsx("default")
        filename = "数据校验结果导入模板.xlsx"
    else:
        content = svc.check_template_xlsx(CHECK_TEMPLATE_TENCENT)
        filename = "腾讯数据校验工具模板.xlsx"
    return _xlsx_response(content, filename)


@router.post("/refresh")
def refresh_checks(
    space_id: int,
    db: Session = Depends(get_db),
    sdb: Session = Depends(get_space_db),
    user: CommonUser = Depends(get_actor),
):
    """全空间重跑任务级数据校验结果刷新（B05-04：前端「刷新任务状态」按钮）。

    按血缘正式输出表重新判定空间内全部任务的 check_result，覆盖增量刷新未触及的任务。
    """
    require_space_member(db, user, space_id)
    refreshed = svc.refresh_all_task_check_results(sdb, space_id, operator=str(user.id))
    return ok(data=CheckRefreshResult(refreshed_tasks=refreshed), message=f"已刷新 {refreshed} 个任务")


@router.get("/by-tables")
def checks_by_tables(
    space_id: int,
    tables: Optional[str] = Query(
        None, description="逗号分隔的 db.table 列表；省略时返回本空间全部表的最近 N 天结果（避免整图超长 URL）"
    ),
    days: int = Query(7, ge=1, le=30, description="取最近 N 天窗口（T-1 起，不含今天）"),
    db: Session = Depends(get_db),
    sdb: Session = Depends(get_space_db),
    user: CommonUser = Depends(get_actor),
):
    """按表批量取最近 N 天校验结果，供血缘节点校验□渲染（D4）。"""
    require_space_member(db, user, space_id)
    parsed: List[Tuple[str, str]] = []
    if tables:
        for item in tables.split(","):
            item = item.strip()
            if not item:
                continue
            db_name, _, table_name = item.partition(".")
            if db_name and table_name:
                parsed.append((db_name, table_name))
    rows_map = svc.get_check_results_by_tables(sdb, space_id, parsed or None, days)
    out: Dict[str, list] = {}
    for (db_name, table_name), recs in rows_map.items():
        out[f"{db_name}.{table_name}"] = [
            CheckResultByTable(
                data_date=r.data_date,
                result=r.result,
                src_volume=r.src_volume,
                dst_volume=r.dst_volume,
            ).model_dump()
            for r in recs
        ]
    return ok(data=CheckResultsByTablesOut(tables=out))
