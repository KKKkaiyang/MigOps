"""b03 数据迁移管理 Schema（Pydantic v2）。"""

from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.b03_data_migration import (
    FULL_SYNC_STATUSES,
    INCR_SYNC_STATUSES,
    METADATA_STATUSES,
    MIGRATION_TYPES,
    RECORD_STATUSES,
    TABLE_TYPES,
)


# ── 迁移场景 ──
class ScenarioCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    remark: Optional[str] = Field(None, max_length=512)


class ScenarioUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=128)
    remark: Optional[str] = Field(None, max_length=512)


class ScenarioOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    remark: Optional[str] = None
    table_count: int = 0
    created_by: Optional[str] = None
    created_at: Optional[datetime] = None


# ── 库表清单 ──
class TableItemCreate(BaseModel):
    db_name: str = Field(..., min_length=1, max_length=128)
    table_name: str = Field(..., min_length=1, max_length=128)
    target_db_name: Optional[str] = Field(None, max_length=128)
    target_table_name: Optional[str] = Field(None, max_length=128)
    table_type: Optional[str] = None
    data_volume: Optional[int] = Field(None, ge=0)
    partition_count: Optional[int] = Field(None, ge=0)
    remark: Optional[str] = Field(None, max_length=1024)

    @field_validator("table_type")
    @classmethod
    def _check_table_type(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in TABLE_TYPES:
            raise ValueError(f"非法的表类型: {v}")
        return v


class TableItemUpdate(BaseModel):
    target_db_name: Optional[str] = Field(None, max_length=128)
    target_table_name: Optional[str] = Field(None, max_length=128)
    table_type: Optional[str] = None
    data_volume: Optional[int] = Field(None, ge=0)
    partition_count: Optional[int] = Field(None, ge=0)
    remark: Optional[str] = Field(None, max_length=1024)

    @field_validator("table_type")
    @classmethod
    def _check_table_type(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in TABLE_TYPES:
            raise ValueError(f"非法的表类型: {v}")
        return v


class TableItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    scenario_id: int
    db_name: str
    table_name: str
    target_db_name: Optional[str] = None
    target_table_name: Optional[str] = None
    table_type: Optional[str] = None
    data_volume: Optional[int] = None
    partition_count: Optional[int] = None
    metadata_status: str
    full_sync_status: str
    full_sync_cutoff_date: Optional[date] = None
    incr_sync_status: str
    incr_sync_latest_at: Optional[datetime] = None
    remark: Optional[str] = None
    # 后端聚合的迁移记录数
    record_count: int = 0
    updated_by: Optional[str] = None
    updated_at: Optional[datetime] = None


class BatchStatusIn(BaseModel):
    ids: List[int] = Field(..., min_length=1)
    metadata_status: Optional[str] = None
    full_sync_status: Optional[str] = None
    full_sync_cutoff_date: Optional[date] = None
    incr_sync_status: Optional[str] = None
    incr_sync_latest_at: Optional[datetime] = None

    @field_validator("metadata_status", "full_sync_status")
    @classmethod
    def _check_migration_status(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in METADATA_STATUSES + FULL_SYNC_STATUSES:
            raise ValueError(f"非法的迁移状态: {v}")
        return v

    @field_validator("incr_sync_status")
    @classmethod
    def _check_incr_status(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in INCR_SYNC_STATUSES:
            raise ValueError(f"非法的增量状态: {v}")
        return v


# ── 迁移过程记录 ──
class RecordCreate(BaseModel):
    migration_type: str
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    data_volume: Optional[int] = Field(None, ge=0)
    method: Optional[str] = Field(None, max_length=64)
    data_cutoff_date: Optional[date] = None
    status: str
    remark: Optional[str] = Field(None, max_length=1024)

    @field_validator("migration_type")
    @classmethod
    def _check_type(cls, v: str) -> str:
        if v not in MIGRATION_TYPES:
            raise ValueError(f"非法的迁移类型: {v}")
        return v

    @field_validator("status")
    @classmethod
    def _check_status(cls, v: str) -> str:
        if v not in RECORD_STATUSES:
            raise ValueError(f"非法的记录状态: {v}")
        return v


class RecordUpdate(BaseModel):
    migration_type: Optional[str] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    data_volume: Optional[int] = Field(None, ge=0)
    method: Optional[str] = Field(None, max_length=64)
    data_cutoff_date: Optional[date] = None
    status: Optional[str] = None
    remark: Optional[str] = Field(None, max_length=1024)

    @field_validator("migration_type")
    @classmethod
    def _check_type(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in MIGRATION_TYPES:
            raise ValueError(f"非法的迁移类型: {v}")
        return v

    @field_validator("status")
    @classmethod
    def _check_status(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in RECORD_STATUSES:
            raise ValueError(f"非法的记录状态: {v}")
        return v


class RecordOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    table_item_id: int
    migration_type: str
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    data_volume: Optional[int] = None
    method: Optional[str] = None
    data_cutoff_date: Optional[date] = None
    status: str
    remark: Optional[str] = None
    created_by: Optional[str] = None
    created_at: Optional[datetime] = None


class ImportErrorItem(BaseModel):
    row: int
    message: str


class ImportResult(BaseModel):
    inserted: int = 0
    updated: int = 0
    skipped: int = 0
    errors: List[ImportErrorItem] = []
