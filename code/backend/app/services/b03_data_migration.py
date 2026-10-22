"""b03 数据迁移管理服务：场景、库表清单、迁移过程记录与导入导出。"""

from datetime import datetime
from typing import List, Optional, Tuple

from fastapi import UploadFile
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.core.exceptions import BizError, NotFoundError
from app.models.b03_data_migration import (
    MIGRATION_TYPE_FULL,
    MIGRATION_TYPES,
    RECORD_STATUSES,
    TABLE_TYPES,
    B03MigrationRecord,
    B03Scenario,
    B03TableItem,
)
from app.schemas.b03_data_migration import (
    BatchStatusIn,
    RecordCreate,
    RecordUpdate,
    ScenarioCreate,
    ScenarioUpdate,
    TableItemCreate,
    TableItemUpdate,
)
from app.utils import excel as xl

# 导入模板列（库表清单）
TABLE_ITEM_IMPORT_HEADERS = [
    "库名",
    "表名",
    "目标库名",
    "目标表名",
    "表类型",
    "预估数据量",
    "分区数",
]
# 导入模板列（迁移过程记录）
RECORD_IMPORT_HEADERS = [
    "库名",
    "表名",
    "迁移类型",
    "开始时间",
    "结束时间",
    "数据量",
    "迁移方式",
    "数据截止日期",
    "状态",
    "备注",
]
# 导出列（库表清单）
TABLE_ITEM_EXPORT_HEADERS = [
    "库名",
    "表名",
    "目标库名",
    "目标表名",
    "表类型",
    "预估数据量",
    "分区数",
    "元数据迁移状态",
    "全量迁移状态",
    "全量迁移截止日期",
    "增量迁移状态",
    "增量最新同步时间",
    "迁移记录数",
    "备注",
]


# ── 场景 ──
def get_scenario(sdb: Session, space_id: int, scenario_id: int) -> B03Scenario:
    obj = (
        sdb.query(B03Scenario)
        .filter(
            B03Scenario.id == scenario_id,
            B03Scenario.space_id == space_id,
            B03Scenario.deleted_at.is_(None),
        )
        .first()
    )
    if not obj:
        raise NotFoundError(f"迁移场景不存在: {scenario_id}")
    return obj


def list_scenarios(sdb: Session, space_id: int) -> List[dict]:
    rows = (
        sdb.query(B03Scenario)
        .filter(B03Scenario.space_id == space_id, B03Scenario.deleted_at.is_(None))
        .order_by(B03Scenario.id.desc())
        .all()
    )
    counts = dict(
        sdb.query(B03TableItem.scenario_id, func.count(B03TableItem.id))
        .filter(B03TableItem.space_id == space_id, B03TableItem.deleted_at.is_(None))
        .group_by(B03TableItem.scenario_id)
        .all()
    )
    return [
        {
            "id": r.id,
            "name": r.name,
            "remark": r.remark,
            "table_count": counts.get(r.id, 0),
            "created_by": r.created_by,
            "created_at": r.created_at,
        }
        for r in rows
    ]


def create_scenario(
    sdb: Session, space_id: int, payload: ScenarioCreate, operator: str
) -> B03Scenario:
    if (
        sdb.query(B03Scenario)
        .filter(
            B03Scenario.space_id == space_id,
            B03Scenario.name == payload.name,
            B03Scenario.deleted_at.is_(None),
        )
        .first()
    ):
        raise BizError(f"场景名称已存在: {payload.name}")
    obj = B03Scenario(space_id=space_id, name=payload.name, remark=payload.remark, created_by=operator)
    sdb.add(obj)
    sdb.commit()
    sdb.refresh(obj)
    return obj


def update_scenario(
    sdb: Session, space_id: int, scenario_id: int, payload: ScenarioUpdate, operator: str
) -> B03Scenario:
    obj = get_scenario(sdb, space_id, scenario_id)
    data = payload.model_dump(exclude_unset=True)
    if "name" in data and data["name"] != obj.name:
        if (
            sdb.query(B03Scenario)
            .filter(
                B03Scenario.space_id == space_id,
                B03Scenario.name == data["name"],
                B03Scenario.id != scenario_id,
                B03Scenario.deleted_at.is_(None),
            )
            .first()
        ):
            raise BizError(f"场景名称已存在: {data['name']}")
    for field, value in data.items():
        setattr(obj, field, value)
    obj.updated_by = operator
    obj.updated_at = datetime.now()
    sdb.commit()
    sdb.refresh(obj)
    return obj


def delete_scenario(sdb: Session, space_id: int, scenario_id: int) -> None:
    """删除场景：级联逻辑删除其下库表清单与迁移记录。"""
    obj = get_scenario(sdb, space_id, scenario_id)
    now = datetime.now()
    obj.deleted_at = now
    sdb.query(B03TableItem).filter(
        B03TableItem.space_id == space_id,
        B03TableItem.scenario_id == scenario_id,
        B03TableItem.deleted_at.is_(None),
    ).update({B03TableItem.deleted_at: now})
    sdb.query(B03MigrationRecord).filter(
        B03MigrationRecord.space_id == space_id,
        B03MigrationRecord.scenario_id == scenario_id,
        B03MigrationRecord.deleted_at.is_(None),
    ).update({B03MigrationRecord.deleted_at: now})
    sdb.commit()


# ── 库表清单 ──
def get_table_item(sdb: Session, space_id: int, item_id: int) -> B03TableItem:
    obj = (
        sdb.query(B03TableItem)
        .filter(
            B03TableItem.id == item_id,
            B03TableItem.space_id == space_id,
            B03TableItem.deleted_at.is_(None),
        )
        .first()
    )
    if not obj:
        raise NotFoundError(f"库表不存在: {item_id}")
    return obj


def count_records_by_items(sdb: Session, space_id: int, item_ids: List[int]) -> dict:
    if not item_ids:
        return {}
    rows = (
        sdb.query(B03MigrationRecord.table_item_id, func.count(B03MigrationRecord.id))
        .filter(
            B03MigrationRecord.space_id == space_id,
            B03MigrationRecord.table_item_id.in_(item_ids),
            B03MigrationRecord.deleted_at.is_(None),
        )
        .group_by(B03MigrationRecord.table_item_id)
        .all()
    )
    return {item_id: cnt for item_id, cnt in rows}


def list_table_items(
    sdb: Session,
    space_id: int,
    scenario_id: int,
    page: int,
    page_size: int,
    keyword: Optional[str] = None,
    table_type: Optional[str] = None,
    metadata_status: Optional[str] = None,
    full_sync_status: Optional[str] = None,
    incr_sync_status: Optional[str] = None,
) -> Tuple[List[B03TableItem], int]:
    get_scenario(sdb, space_id, scenario_id)
    q = sdb.query(B03TableItem).filter(
        B03TableItem.space_id == space_id,
        B03TableItem.scenario_id == scenario_id,
        B03TableItem.deleted_at.is_(None),
    )
    if keyword:
        like = f"%{keyword}%"
        q = q.filter(
            or_(
                B03TableItem.db_name.like(like),
                B03TableItem.table_name.like(like),
            )
        )
    if table_type:
        q = q.filter(B03TableItem.table_type == table_type)
    if metadata_status:
        q = q.filter(B03TableItem.metadata_status == metadata_status)
    if full_sync_status:
        q = q.filter(B03TableItem.full_sync_status == full_sync_status)
    if incr_sync_status:
        q = q.filter(B03TableItem.incr_sync_status == incr_sync_status)
    total = q.count()
    rows = q.order_by(B03TableItem.id.asc()).offset((page - 1) * page_size).limit(page_size).all()
    return rows, total


def _query_all_for_export(
    sdb: Session,
    space_id: int,
    scenario_id: int,
    keyword: Optional[str] = None,
    table_type: Optional[str] = None,
    metadata_status: Optional[str] = None,
    full_sync_status: Optional[str] = None,
    incr_sync_status: Optional[str] = None,
) -> List[B03TableItem]:
    q = sdb.query(B03TableItem).filter(
        B03TableItem.space_id == space_id,
        B03TableItem.scenario_id == scenario_id,
        B03TableItem.deleted_at.is_(None),
    )
    if keyword:
        like = f"%{keyword}%"
        q = q.filter(or_(B03TableItem.db_name.like(like), B03TableItem.table_name.like(like)))
    if table_type:
        q = q.filter(B03TableItem.table_type == table_type)
    if metadata_status:
        q = q.filter(B03TableItem.metadata_status == metadata_status)
    if full_sync_status:
        q = q.filter(B03TableItem.full_sync_status == full_sync_status)
    if incr_sync_status:
        q = q.filter(B03TableItem.incr_sync_status == incr_sync_status)
    return q.order_by(B03TableItem.id.asc()).all()


def create_table_item(
    sdb: Session, space_id: int, scenario_id: int, payload: TableItemCreate, operator: str
) -> B03TableItem:
    get_scenario(sdb, space_id, scenario_id)
    _check_dup(sdb, scenario_id, payload.db_name, payload.table_name)
    obj = B03TableItem(
        space_id=space_id,
        scenario_id=scenario_id,
        **payload.model_dump(),
        created_by=operator,
    )
    sdb.add(obj)
    sdb.commit()
    sdb.refresh(obj)
    return obj


def update_table_item(
    sdb: Session, space_id: int, item_id: int, payload: TableItemUpdate, operator: str
) -> B03TableItem:
    obj = get_table_item(sdb, space_id, item_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(obj, field, value)
    obj.updated_by = operator
    obj.updated_at = datetime.now()
    sdb.commit()
    sdb.refresh(obj)
    return obj


def delete_table_item(sdb: Session, space_id: int, item_id: int) -> None:
    obj = get_table_item(sdb, space_id, item_id)
    obj.deleted_at = datetime.now()
    sdb.commit()


def _check_dup(sdb: Session, scenario_id: int, db_name: str, table_name: str, exclude_id: Optional[int] = None) -> None:
    q = sdb.query(B03TableItem).filter(
        B03TableItem.scenario_id == scenario_id,
        B03TableItem.db_name == db_name,
        B03TableItem.table_name == table_name,
        B03TableItem.deleted_at.is_(None),
    )
    if exclude_id is not None:
        q = q.filter(B03TableItem.id != exclude_id)
    if q.first():
        raise BizError(f"库表已存在: {db_name}.{table_name}")


def batch_update_status(
    sdb: Session, space_id: int, payload: BatchStatusIn, operator: str
) -> int:
    """批量更新迁移状态；仅设置提供的字段，返回受影响行数。"""
    fields = payload.model_dump(exclude_unset=True)
    ids = fields.pop("ids")
    if not fields:
        raise BizError("未提供需要更新的状态字段")
    rows = (
        sdb.query(B03TableItem)
        .filter(
            B03TableItem.space_id == space_id,
            B03TableItem.id.in_(ids),
            B03TableItem.deleted_at.is_(None),
        )
        .all()
    )
    now = datetime.now()
    for row in rows:
        for field, value in fields.items():
            setattr(row, field, value)
        row.updated_by = operator
        row.updated_at = now
    sdb.commit()
    return len(rows)


# ── 导入 / 导出 ──
def import_table_items(
    sdb: Session, space_id: int, scenario_id: int, file: UploadFile, operator: str
) -> dict:
    get_scenario(sdb, space_id, scenario_id)
    xl.check_import_file(file.filename)
    content = file.file.read()
    headers, rows, line_nos = xl.read_tabular(content, file.filename or "")
    if len(rows) > xl.MAX_IMPORT_ROWS:
        raise BizError(f"单次导入不得超过 {xl.MAX_IMPORT_ROWS} 行")
    missing = [h for h in ("库名", "表名") if h not in headers]
    if missing:
        raise BizError(f"导入文件缺少必需列: {', '.join(missing)}")

    inserted = updated = 0
    errors = []
    for row, line_no in zip(rows, line_nos):
        try:
            db_name = xl._to_str(row.get("库名"))
            table_name = xl._to_str(row.get("表名"))
            if not db_name or not table_name:
                raise ValueError("库名/表名不能为空")
            table_type = xl._to_str(row.get("表类型")) or None
            if table_type and table_type not in TABLE_TYPES:
                raise ValueError(f"非法的表类型: {table_type}")
            values = {
                "target_db_name": xl._to_str(row.get("目标库名")) or None,
                "target_table_name": xl._to_str(row.get("目标表名")) or None,
                "table_type": table_type,
                "data_volume": xl._to_int(row.get("预估数据量")),
                "partition_count": xl._to_int(row.get("分区数")),
            }
            existing = (
                sdb.query(B03TableItem)
                .filter(
                    B03TableItem.scenario_id == scenario_id,
                    B03TableItem.db_name == db_name,
                    B03TableItem.table_name == table_name,
                    B03TableItem.deleted_at.is_(None),
                )
                .first()
            )
            if existing:
                for field, value in values.items():
                    setattr(existing, field, value)
                existing.updated_by = operator
                existing.updated_at = datetime.now()
                updated += 1
            else:
                sdb.add(
                    B03TableItem(
                        space_id=space_id,
                        scenario_id=scenario_id,
                        db_name=db_name,
                        table_name=table_name,
                        created_by=operator,
                        **values,
                    )
                )
                inserted += 1
        except ValueError as exc:
            errors.append({"row": line_no, "message": str(exc)})
    sdb.commit()
    return {"inserted": inserted, "updated": updated, "skipped": 0, "errors": errors}


def export_table_items(
    sdb: Session,
    space_id: int,
    scenario_id: int,
    keyword: Optional[str] = None,
    table_type: Optional[str] = None,
    metadata_status: Optional[str] = None,
    full_sync_status: Optional[str] = None,
    incr_sync_status: Optional[str] = None,
) -> bytes:
    rows = _query_all_for_export(
        sdb, space_id, scenario_id, keyword, table_type, metadata_status, full_sync_status, incr_sync_status
    )
    counts = count_records_by_items(sdb, space_id, [r.id for r in rows])
    data = [
        [
            r.db_name,
            r.table_name,
            r.target_db_name or "",
            r.target_table_name or "",
            r.table_type or "",
            r.data_volume if r.data_volume is not None else "",
            r.partition_count if r.partition_count is not None else "",
            r.metadata_status,
            r.full_sync_status,
            r.full_sync_cutoff_date.strftime("%Y-%m-%d") if r.full_sync_cutoff_date else "",
            r.incr_sync_status,
            r.incr_sync_latest_at.strftime("%Y-%m-%d %H:%M:%S") if r.incr_sync_latest_at else "",
            counts.get(r.id, 0),
            r.remark or "",
        ]
        for r in rows
    ]
    return xl.make_xlsx(
        TABLE_ITEM_EXPORT_HEADERS,
        data,
        widths=[16, 24, 16, 24, 10, 14, 10, 14, 14, 16, 12, 18, 12, 24],
    )


def table_item_template() -> bytes:
    return xl.make_xlsx(
        TABLE_ITEM_IMPORT_HEADERS,
        [["ods", "ods_order_di", "ods", "ods_order_di", "分区表", 230000000, 30]],
        widths=[16, 24, 16, 24, 10, 14, 10],
    )


# ── 迁移过程记录 ──
def list_records(
    sdb: Session, space_id: int, item_id: int, page: int, page_size: int
) -> Tuple[List[B03MigrationRecord], int]:
    get_table_item(sdb, space_id, item_id)
    q = sdb.query(B03MigrationRecord).filter(
        B03MigrationRecord.space_id == space_id,
        B03MigrationRecord.table_item_id == item_id,
        B03MigrationRecord.deleted_at.is_(None),
    )
    total = q.count()
    rows = q.order_by(B03MigrationRecord.id.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return rows, total


def create_record(
    sdb: Session, space_id: int, item_id: int, payload: RecordCreate, operator: str
) -> B03MigrationRecord:
    item = get_table_item(sdb, space_id, item_id)
    obj = B03MigrationRecord(
        space_id=space_id,
        scenario_id=item.scenario_id,
        table_item_id=item_id,
        **payload.model_dump(),
        created_by=operator,
    )
    sdb.add(obj)
    sdb.commit()
    sdb.refresh(obj)
    return obj


def update_record(
    sdb: Session, space_id: int, record_id: int, payload: RecordUpdate, operator: str
) -> B03MigrationRecord:
    obj = (
        sdb.query(B03MigrationRecord)
        .filter(
            B03MigrationRecord.id == record_id,
            B03MigrationRecord.space_id == space_id,
            B03MigrationRecord.deleted_at.is_(None),
        )
        .first()
    )
    if not obj:
        raise NotFoundError(f"迁移记录不存在: {record_id}")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(obj, field, value)
    obj.updated_by = operator
    obj.updated_at = datetime.now()
    sdb.commit()
    sdb.refresh(obj)
    return obj


def delete_record(sdb: Session, space_id: int, record_id: int) -> None:
    obj = (
        sdb.query(B03MigrationRecord)
        .filter(
            B03MigrationRecord.id == record_id,
            B03MigrationRecord.space_id == space_id,
            B03MigrationRecord.deleted_at.is_(None),
        )
        .first()
    )
    if not obj:
        raise NotFoundError(f"迁移记录不存在: {record_id}")
    obj.deleted_at = datetime.now()
    sdb.commit()


def import_records(
    sdb: Session, space_id: int, scenario_id: int, file: UploadFile, operator: str
) -> dict:
    get_scenario(sdb, space_id, scenario_id)
    xl.check_import_file(file.filename)
    content = file.file.read()
    headers, rows, line_nos = xl.read_tabular(content, file.filename or "")
    if len(rows) > xl.MAX_IMPORT_ROWS:
        raise BizError(f"单次导入不得超过 {xl.MAX_IMPORT_ROWS} 行")
    missing = [h for h in ("库名", "表名", "迁移类型", "状态") if h not in headers]
    if missing:
        raise BizError(f"导入文件缺少必需列: {', '.join(missing)}")

    inserted = 0
    errors = []
    for row, line_no in zip(rows, line_nos):
        try:
            db_name = xl._to_str(row.get("库名"))
            table_name = xl._to_str(row.get("表名"))
            migration_type = xl._to_str(row.get("迁移类型"))
            status = xl._to_str(row.get("状态"))
            if not db_name or not table_name:
                raise ValueError("库名/表名不能为空")
            if migration_type not in MIGRATION_TYPES:
                raise ValueError(f"非法的迁移类型: {migration_type}")
            if status not in RECORD_STATUSES:
                raise ValueError(f"非法的记录状态: {status}")
            item = (
                sdb.query(B03TableItem)
                .filter(
                    B03TableItem.scenario_id == scenario_id,
                    B03TableItem.db_name == db_name,
                    B03TableItem.table_name == table_name,
                    B03TableItem.deleted_at.is_(None),
                )
                .first()
            )
            if not item:
                raise ValueError(f"库表不存在于当前场景: {db_name}.{table_name}")
            sdb.add(
                B03MigrationRecord(
                    space_id=space_id,
                    scenario_id=scenario_id,
                    table_item_id=item.id,
                    migration_type=migration_type,
                    started_at=xl._to_datetime(row.get("开始时间")),
                    finished_at=xl._to_datetime(row.get("结束时间")),
                    data_volume=xl._to_int(row.get("数据量")),
                    method=xl._to_str(row.get("迁移方式")) or None,
                    data_cutoff_date=xl._to_date(row.get("数据截止日期")),
                    status=status,
                    remark=xl._to_str(row.get("备注")) or None,
                    created_by=operator,
                )
            )
            inserted += 1
        except ValueError as exc:
            errors.append({"row": line_no, "message": str(exc)})
    sdb.commit()
    return {"inserted": inserted, "updated": 0, "skipped": 0, "errors": errors}


def record_template() -> bytes:
    return xl.make_xlsx(
        RECORD_IMPORT_HEADERS,
        [
            [
                "ods",
                "ods_order_di",
                MIGRATION_TYPE_FULL,
                "2026-09-28 10:00:00",
                "2026-09-28 14:30:00",
                230000000,
                "DistCp",
                "2026-09-27",
                "成功",
                "",
            ]
        ],
        widths=[16, 24, 14, 20, 20, 14, 12, 14, 10, 24],
    )
