"""b03 数据迁移管理接口。

空间业务表位于空间库（mig_<space_code>_db），经 get_space_db 路由；
权限校验经 get_db（common_user_role 位于公共库）。

鉴权：统一 `get_actor` 依赖，支持网页登录态（Bearer）与 REST API（ak/sk HMAC 签名）
双鉴权（需求 AK-02 / BRD §4.5）；空间隔离业务经 `require_space_member` 校验成员/角色，
ak/sk 操作人 = 密钥持有用户，须为目标空间成员（D2）。
"""

from typing import Optional
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Query, Response, UploadFile
from sqlalchemy.orm import Session

from app.core.deps import get_actor, get_space_db, require_space_member
from app.core.response import PageData, ok
from app.database import get_db
from app.models.user import CommonUser
from app.schemas.b03_data_migration import (
    BatchStatusIn,
    RecordCreate,
    RecordOut,
    RecordUpdate,
    ScenarioCreate,
    ScenarioUpdate,
    TableItemCreate,
    TableItemOut,
    TableItemUpdate,
)
from app.services import b03_data_migration as svc
from app.utils.excel import XLSX_MEDIA_TYPE

router = APIRouter(prefix="/b03", tags=["b03-数据迁移管理"])


def _xlsx_response(content: bytes, filename: str) -> Response:
    return Response(
        content=content,
        media_type=XLSX_MEDIA_TYPE,
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"
        },
    )


# ── 迁移场景 ──
@router.get("/scenarios")
def list_scenarios(
    space_id: int,
    db: Session = Depends(get_db),
    sdb: Session = Depends(get_space_db),
    user: CommonUser = Depends(get_actor),
):
    require_space_member(db, user, space_id)
    return ok(data=svc.list_scenarios(sdb, space_id))


@router.post("/scenarios", status_code=201)
def create_scenario(
    space_id: int,
    payload: ScenarioCreate,
    db: Session = Depends(get_db),
    sdb: Session = Depends(get_space_db),
    user: CommonUser = Depends(get_actor),
):
    require_space_member(db, user, space_id)
    obj = svc.create_scenario(sdb, space_id, payload, operator=str(user.id))
    return ok(data={"id": obj.id, "name": obj.name}, message="创建成功")


@router.put("/scenarios/{scenario_id}")
def update_scenario(
    space_id: int,
    scenario_id: int,
    payload: ScenarioUpdate,
    db: Session = Depends(get_db),
    sdb: Session = Depends(get_space_db),
    user: CommonUser = Depends(get_actor),
):
    require_space_member(db, user, space_id)
    svc.update_scenario(sdb, space_id, scenario_id, payload, operator=str(user.id))
    return ok(message="更新成功")


@router.delete("/scenarios/{scenario_id}")
def delete_scenario(
    space_id: int,
    scenario_id: int,
    db: Session = Depends(get_db),
    sdb: Session = Depends(get_space_db),
    user: CommonUser = Depends(get_actor),
):
    require_space_member(db, user, space_id)
    svc.delete_scenario(sdb, space_id, scenario_id)
    return ok(message="删除成功")


# ── 库表清单 ──
@router.get("/scenarios/{scenario_id}/table-items")
def list_table_items(
    space_id: int,
    scenario_id: int,
    db: Session = Depends(get_db),
    sdb: Session = Depends(get_space_db),
    user: CommonUser = Depends(get_actor),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    keyword: str = Query(None),
    table_type: str = Query(None),
    metadata_status: str = Query(None),
    full_sync_status: str = Query(None),
    incr_sync_status: str = Query(None),
):
    require_space_member(db, user, space_id)
    rows, total = svc.list_table_items(
        sdb,
        space_id,
        scenario_id,
        page,
        page_size,
        keyword,
        table_type,
        metadata_status,
        full_sync_status,
        incr_sync_status,
    )
    counts = svc.count_records_by_items(sdb, space_id, [r.id for r in rows])
    data = PageData[TableItemOut](
        list=[_table_item_out(r, counts.get(r.id, 0)) for r in rows],
        total=total,
        page=page,
        page_size=page_size,
    )
    return ok(data=data)


def _table_item_out(obj, record_count: int) -> TableItemOut:
    out = TableItemOut.model_validate(obj)
    out.record_count = record_count
    return out


@router.post("/scenarios/{scenario_id}/table-items", status_code=201)
def create_table_item(
    space_id: int,
    scenario_id: int,
    payload: TableItemCreate,
    db: Session = Depends(get_db),
    sdb: Session = Depends(get_space_db),
    user: CommonUser = Depends(get_actor),
):
    require_space_member(db, user, space_id)
    obj = svc.create_table_item(sdb, space_id, scenario_id, payload, operator=str(user.id))
    return ok(data=_table_item_out(obj, 0), message="创建成功")


@router.put("/table-items/{item_id}")
def update_table_item(
    space_id: int,
    item_id: int,
    payload: TableItemUpdate,
    db: Session = Depends(get_db),
    sdb: Session = Depends(get_space_db),
    user: CommonUser = Depends(get_actor),
):
    require_space_member(db, user, space_id)
    obj = svc.update_table_item(sdb, space_id, item_id, payload, operator=str(user.id))
    counts = svc.count_records_by_items(sdb, space_id, [obj.id])
    return ok(data=_table_item_out(obj, counts.get(obj.id, 0)), message="更新成功")


@router.delete("/table-items/{item_id}")
def delete_table_item(
    space_id: int,
    item_id: int,
    db: Session = Depends(get_db),
    sdb: Session = Depends(get_space_db),
    user: CommonUser = Depends(get_actor),
):
    require_space_member(db, user, space_id)
    svc.delete_table_item(sdb, space_id, item_id)
    return ok(message="删除成功")


@router.post("/scenarios/{scenario_id}/table-items/batch-status")
def batch_update_status(
    space_id: int,
    scenario_id: int,
    payload: BatchStatusIn,
    db: Session = Depends(get_db),
    sdb: Session = Depends(get_space_db),
    user: CommonUser = Depends(get_actor),
):
    require_space_member(db, user, space_id)
    svc.get_scenario(sdb, space_id, scenario_id)
    affected = svc.batch_update_status(sdb, space_id, payload, operator=str(user.id))
    return ok(data={"affected": affected}, message=f"已更新 {affected} 条")


@router.post("/scenarios/{scenario_id}/table-items/import")
def import_table_items(
    space_id: int,
    scenario_id: int,
    db: Session = Depends(get_db),
    sdb: Session = Depends(get_space_db),
    user: CommonUser = Depends(get_actor),
    file: UploadFile = File(...),
):
    require_space_member(db, user, space_id)
    result = svc.import_table_items(sdb, space_id, scenario_id, file, operator=str(user.id))
    return ok(data=result, message="导入完成")


@router.get("/scenarios/{scenario_id}/table-items/template")
def table_item_template(
    space_id: int,
    scenario_id: int,
    db: Session = Depends(get_db),
    sdb: Session = Depends(get_space_db),
    user: CommonUser = Depends(get_actor),
):
    require_space_member(db, user, space_id)
    return _xlsx_response(svc.table_item_template(), "库表清单导入模板.xlsx")


@router.get("/scenarios/{scenario_id}/table-items/export")
def export_table_items(
    space_id: int,
    scenario_id: int,
    db: Session = Depends(get_db),
    sdb: Session = Depends(get_space_db),
    user: CommonUser = Depends(get_actor),
    keyword: str = Query(None),
    table_type: str = Query(None),
    metadata_status: str = Query(None),
    full_sync_status: str = Query(None),
    incr_sync_status: str = Query(None),
):
    require_space_member(db, user, space_id)
    content = svc.export_table_items(
        sdb,
        space_id,
        scenario_id,
        keyword,
        table_type,
        metadata_status,
        full_sync_status,
        incr_sync_status,
    )
    return _xlsx_response(content, "库表清单.xlsx")


# ── 迁移过程记录 ──
@router.get("/table-items/{item_id}/records")
def list_records(
    space_id: int,
    item_id: int,
    db: Session = Depends(get_db),
    sdb: Session = Depends(get_space_db),
    user: CommonUser = Depends(get_actor),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
):
    require_space_member(db, user, space_id)
    rows, total = svc.list_records(sdb, space_id, item_id, page, page_size)
    data = PageData[RecordOut](list=rows, total=total, page=page, page_size=page_size)
    return ok(data=data)


@router.post("/table-items/{item_id}/records", status_code=201)
def create_record(
    space_id: int,
    item_id: int,
    payload: RecordCreate,
    db: Session = Depends(get_db),
    sdb: Session = Depends(get_space_db),
    user: CommonUser = Depends(get_actor),
):
    require_space_member(db, user, space_id)
    obj = svc.create_record(sdb, space_id, item_id, payload, operator=str(user.id))
    return ok(data=RecordOut.model_validate(obj), message="创建成功")


@router.put("/records/{record_id}")
def update_record(
    space_id: int,
    record_id: int,
    payload: RecordUpdate,
    db: Session = Depends(get_db),
    sdb: Session = Depends(get_space_db),
    user: CommonUser = Depends(get_actor),
):
    require_space_member(db, user, space_id)
    obj = svc.update_record(sdb, space_id, record_id, payload, operator=str(user.id))
    return ok(data=RecordOut.model_validate(obj), message="更新成功")


@router.delete("/records/{record_id}")
def delete_record(
    space_id: int,
    record_id: int,
    db: Session = Depends(get_db),
    sdb: Session = Depends(get_space_db),
    user: CommonUser = Depends(get_actor),
):
    require_space_member(db, user, space_id)
    svc.delete_record(sdb, space_id, record_id)
    return ok(message="删除成功")


@router.post("/scenarios/{scenario_id}/records/import")
def import_records(
    space_id: int,
    scenario_id: int,
    db: Session = Depends(get_db),
    sdb: Session = Depends(get_space_db),
    user: CommonUser = Depends(get_actor),
    file: UploadFile = File(...),
):
    require_space_member(db, user, space_id)
    result = svc.import_records(sdb, space_id, scenario_id, file, operator=str(user.id))
    return ok(data=result, message="导入完成")


@router.get("/scenarios/{scenario_id}/records/template")
def record_template(
    space_id: int,
    scenario_id: int,
    db: Session = Depends(get_db),
    sdb: Session = Depends(get_space_db),
    user: CommonUser = Depends(get_actor),
):
    require_space_member(db, user, space_id)
    return _xlsx_response(svc.record_template(), "迁移记录导入模板.xlsx")
