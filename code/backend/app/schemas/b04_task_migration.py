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
from app.schemas.b06_tag import TagBrief


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
    tags: List[TagBrief] = []
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
    filter_config: dict = Field(default_factory=dict, description="筛选条件(属性组合 + 标签维度)")
    view_mode: str = Field("dynamic", description="dynamic=动态引用;fixed=固化台账(锁定命中ID)")
    # R3：勾选具体任务创建台账 → 直接以所选任务 ID 落为固化成员（强制 fixed）
    member_ids: Optional[List[int]] = Field(
        None, description="R3 勾选任务创建台账：直接固化为成员(强制 fixed)，与 filter_config 互斥"
    )

    @field_validator("view_mode")
    @classmethod
    def _check_mode(cls, v: str) -> str:
        if v not in ("dynamic", "fixed"):
            raise ValueError("view_mode 必须为 dynamic 或 fixed")
        return v


class SavedViewRemoveMembers(BaseModel):
    """R4：从台账移除任务（批量）。"""

    task_ids: List[int] = Field(..., min_length=1, description="要移除的任务 ID 列表")


class SavedViewAddMembers(BaseModel):
    """补充需求：向台账补充新增任务（批量加入成员；动态引用台账将自动固化为成员集合）。"""

    task_ids: List[int] = Field(..., min_length=1, description="要加入台账的任务 ID 列表")


class SavedViewUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=128)
    description: Optional[str] = Field(None, max_length=512)
    filter_config: Optional[dict] = None
    view_mode: Optional[str] = None

    @field_validator("view_mode")
    @classmethod
    def _check_mode(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in ("dynamic", "fixed"):
            raise ValueError("view_mode 必须为 dynamic 或 fixed")
        return v


class SavedViewOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    scenario_id: int
    name: str
    description: Optional[str] = None
    filter_config: dict
    view_mode: str = "dynamic"
    task_count: int = 0
    created_by: Optional[str] = None
    created_at: Optional[datetime] = None


# ── 标签管理（标签主表与 CRUD 见 b06_tag schema；此处仅任务侧引用 TagBrief） ──


def allowed_next_statuses(current: str) -> List[str]:
    """当前状态允许流转到的目标状态集合（非法流转提示用）。"""
    return sorted(TASK_STATUS_TRANSITIONS.get(current, set()))
