"""b04 任务迁移管理 Schema（Pydantic v2）。"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.b04_task_migration import (
    CHECK_STATUSES,
    NOTE_KINDS,
    SCHEDULE_STATUSES,
    TASK_STATUSES,
    TASK_STATUS_TRANSITIONS,
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
    task_count: int = 0
    created_by: Optional[str] = None
    created_at: Optional[datetime] = None


# ── 任务台账 ──
class TaskUpdate(BaseModel):
    script_name: Optional[str] = Field(None, max_length=255)
    owner: Optional[str] = Field(None, max_length=64)
    schedule_status: Optional[str] = None
    check_status: Optional[str] = None
    input_tables: Optional[str] = Field(None, max_length=1024)
    output_tables: Optional[str] = Field(None, max_length=1024)

    @field_validator("schedule_status")
    @classmethod
    def _check_schedule(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in SCHEDULE_STATUSES:
            raise ValueError(f"非法的调度状态: {v}")
        return v

    @field_validator("check_status")
    @classmethod
    def _check_check(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in CHECK_STATUSES:
            raise ValueError(f"非法的校验状态: {v}")
        return v


class TaskStatusIn(BaseModel):
    status: str = Field(..., description="目标迁移状态")


class TaskBatchStatusIn(BaseModel):
    ids: List[int] = Field(..., min_length=1)
    status: str


class TaskOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    scenario_id: int
    workflow_name: str
    task_name: str
    script_name: Optional[str] = None
    owner: Optional[str] = None
    task_uri: str
    migration_status: str
    schedule_status: str
    check_status: str
    input_tables: Optional[str] = None
    output_tables: Optional[str] = None
    latest_note: Optional[str] = None
    updated_by: Optional[str] = None
    updated_at: Optional[datetime] = None


class TaskImportResult(BaseModel):
    inserted: int = 0
    updated: int = 0
    skipped: int = 0
    errors: List[dict] = []


# ── 排查备注 ──
class NoteCreate(BaseModel):
    note_kind: str = Field(..., description="troubleshoot|check_result")
    problem_desc: Optional[str] = None
    cause_analysis: Optional[str] = None
    fix_plan: Optional[str] = None

    @field_validator("note_kind")
    @classmethod
    def _check_kind(cls, v: str) -> str:
        if v not in NOTE_KINDS:
            raise ValueError(f"非法的备注类型: {v}")
        return v


class NoteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    task_id: int
    note_kind: str
    problem_desc: Optional[str] = None
    cause_analysis: Optional[str] = None
    fix_plan: Optional[str] = None
    created_by: Optional[str] = None
    created_at: Optional[datetime] = None


# ── 自定义台账 ──
class SavedViewCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    description: Optional[str] = Field(None, max_length=512)
    filter_config: dict = Field(..., description="筛选条件(属性组合)")


class SavedViewUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=128)
    description: Optional[str] = Field(None, max_length=512)
    filter_config: Optional[dict] = None


class SavedViewOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    scenario_id: int
    name: str
    description: Optional[str] = None
    filter_config: dict
    task_count: int = 0
    created_by: Optional[str] = None
    created_at: Optional[datetime] = None


def allowed_next_statuses(current: str) -> List[str]:
    """当前状态允许流转到的目标状态集合（非法流转提示用）。"""
    return sorted(TASK_STATUS_TRANSITIONS.get(current, set()))
