"""b04 任务迁移管理 Schema（Pydantic v2）。

依据《任务迁移-任务台账数据模型重构需求》V1.0（D1~D7）：
- 任务主体改为 15 业务字段 + 5 维独立状态（替代旧状态机）。
- 新增空间级迁移模板 schema（字段选择/必填/排序/列表展示/扩展字段定义）。
"""

from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.b04_task_migration import (
    ACCEPTANCE_STATUSES,
    ACTIVE_STATUSES,
    CHECK_RESULT_NONE,
    CHECK_RESULTS,
    CHECK_STATUSES,
    DUALRUN_STATUSES,
    MIGRATION_STATUSES,
    NOTE_KINDS,
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


# ── 任务台账（基础表 + 扩展） ──
# 5 维状态维度键集合（用于批量更新维度校验）
STATUS_DIMENSIONS = {
    "active_status": ACTIVE_STATUSES,
    "migration_status": MIGRATION_STATUSES,
    "dualrun_status": DUALRUN_STATUSES,
    "check_status": CHECK_STATUSES,
    "acceptance_status": ACCEPTANCE_STATUSES,
}


class TaskUpdate(BaseModel):
    """任务明细更新：基础字段 + 扩展字段(ext: f_n 英文名→值)。"""

    project_name: Optional[str] = Field(None, max_length=128)
    workflow_name: Optional[str] = Field(None, max_length=128)
    task_name: Optional[str] = Field(None, max_length=255)
    env: Optional[str] = Field(None, max_length=32)
    business: Optional[str] = Field(None, max_length=255)
    task_type: Optional[str] = Field(None, max_length=64)
    migration_owner: Optional[str] = Field(None, max_length=64)
    active_status: Optional[str] = None
    migration_status: Optional[str] = None
    dualrun_status: Optional[str] = None
    check_status: Optional[str] = None
    acceptance_status: Optional[str] = None
    check_result: Optional[str] = Field(None, max_length=32)
    remark: Optional[str] = Field(None, max_length=1024)
    ext: Optional[Dict[str, str]] = Field(None, description="扩展字段: f_n 英文名→值")

    @field_validator("active_status")
    @classmethod
    def _v_active(cls, v):
        if v is not None and v not in ACTIVE_STATUSES:
            raise ValueError(f"非法的任务活跃状态: {v}")
        return v

    @field_validator("migration_status")
    @classmethod
    def _v_migration(cls, v):
        if v is not None and v not in MIGRATION_STATUSES:
            raise ValueError(f"非法的迁移状态: {v}")
        return v

    @field_validator("dualrun_status")
    @classmethod
    def _v_dualrun(cls, v):
        if v is not None and v not in DUALRUN_STATUSES:
            raise ValueError(f"非法的双跑调度状态: {v}")
        return v

    @field_validator("check_status")
    @classmethod
    def _v_check(cls, v):
        if v is not None and v not in CHECK_STATUSES:
            raise ValueError(f"非法的数据校验状态: {v}")
        return v

    @field_validator("acceptance_status")
    @classmethod
    def _v_acceptance(cls, v):
        if v is not None and v not in ACCEPTANCE_STATUSES:
            raise ValueError(f"非法的客户验收状态: {v}")
        return v

    @field_validator("check_result")
    @classmethod
    def _v_check_result(cls, v):
        if v is not None and v not in CHECK_RESULTS:
            raise ValueError(f"非法的数据校验结果: {v}")
        return v


class TaskStatusIn(BaseModel):
    """5 维状态独立更新：仅传需要更新的维度即可（互不约束）。"""

    active_status: Optional[str] = None
    migration_status: Optional[str] = None
    dualrun_status: Optional[str] = None
    check_status: Optional[str] = None
    acceptance_status: Optional[str] = None

    @field_validator("active_status")
    @classmethod
    def _v_active(cls, v):
        if v is not None and v not in ACTIVE_STATUSES:
            raise ValueError(f"非法的任务活跃状态: {v}")
        return v

    @field_validator("migration_status")
    @classmethod
    def _v_migration(cls, v):
        if v is not None and v not in MIGRATION_STATUSES:
            raise ValueError(f"非法的迁移状态: {v}")
        return v

    @field_validator("dualrun_status")
    @classmethod
    def _v_dualrun(cls, v):
        if v is not None and v not in DUALRUN_STATUSES:
            raise ValueError(f"非法的双跑调度状态: {v}")
        return v

    @field_validator("check_status")
    @classmethod
    def _v_check(cls, v):
        if v is not None and v not in CHECK_STATUSES:
            raise ValueError(f"非法的数据校验状态: {v}")
        return v

    @field_validator("acceptance_status")
    @classmethod
    def _v_acceptance(cls, v):
        if v is not None and v not in ACCEPTANCE_STATUSES:
            raise ValueError(f"非法的客户验收状态: {v}")
        return v


class TaskBatchStatusIn(BaseModel):
    """批量更新某一维度的状态。"""

    ids: List[int] = Field(..., min_length=1)
    dimension: str = Field(..., description="维度键: active_status/migration_status/...")
    value: str = Field(..., description="目标取值")

    @field_validator("dimension")
    @classmethod
    def _v_dim(cls, v):
        if v not in STATUS_DIMENSIONS:
            raise ValueError(f"非法的状态维度: {v}")
        return v

    @field_validator("value")
    @classmethod
    def _v_val(cls, v, info):
        dim = info.data.get("dimension")
        if dim and v not in STATUS_DIMENSIONS[dim]:
            raise ValueError(f"维度 {dim} 的非法取值: {v}")
        return v


class TaskOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    scenario_id: int
    # 15 业务字段（B04-08：除项目名称/任务名称外均可空，导入留空落 NULL）
    project_name: str
    workflow_name: Optional[str] = None
    task_name: str
    env: Optional[str] = None
    business: Optional[str] = None
    task_type: Optional[str] = None
    migration_owner: Optional[str] = None
    active_status: Optional[str] = None
    migration_status: Optional[str] = None
    dualrun_status: Optional[str] = None
    check_status: Optional[str] = None
    acceptance_status: Optional[str] = None
    check_result: Optional[str] = None
    remark: Optional[str] = None
    task_uri: str
    # 扩展字段：f_n 英文名 → 值（由 service 组装）
    ext: Dict[str, str] = {}
    tags: List[TagBrief] = []
    updated_by: Optional[str] = None
    updated_at: Optional[datetime] = None


class TaskImportResult(BaseModel):
    inserted: int = 0
    updated: int = 0
    skipped: int = 0
    errors: List[dict] = []


# ── 空间级迁移模板 ──
# 9 个锁定必填字段（必须纳入模板且导入必须有值，D5；check_result 为数据校验结果，见数据校验需求）
REQUIRED_TEMPLATE_FIELDS = {
    "project_name",
    "task_name",
    "migration_owner",
    "active_status",
    "migration_status",
    "dualrun_status",
    "check_status",
    "acceptance_status",
    "check_result",
}


class MigrationTemplateField(BaseModel):
    field_key: str = Field(..., description="基础表字段名 或 扩展字段序号 ext_1")
    field_label: str = Field(..., description="中文显示名（扩展字段中文名在此定义）")
    field_source: str = Field(..., description="base=基础表字段;extension=扩展字段")
    is_required: bool = False
    display_in_list: bool = True
    order: int = Field(..., description="排序(升序)")
    ext_type: Optional[str] = Field(None, description="仅 extension: enum|string")
    enum_options: Optional[List[dict]] = Field(None, description="仅 enum: [{code,label}]")

    @field_validator("field_source")
    @classmethod
    def _v_source(cls, v):
        if v not in ("base", "extension"):
            raise ValueError("field_source 必须为 base 或 extension")
        return v

    @field_validator("ext_type")
    @classmethod
    def _v_ext_type(cls, v, info):
        src = info.data.get("field_source")
        if src == "extension" and v not in ("enum", "string"):
            raise ValueError("扩展字段 ext_type 必须为 enum 或 string")
        if src != "extension" and v is not None:
            raise ValueError("基础字段不应设置 ext_type")
        return v


class MigrationTemplateUpsert(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    config_json: dict = Field(..., description="字段配置: {fields: [MigrationTemplateField...]}")

    @field_validator("config_json")
    @classmethod
    def _validate_config(cls, v):
        fields = v.get("fields") if isinstance(v, dict) else None
        if not isinstance(fields, list) or not fields:
            raise ValueError("config_json.fields 不能为空")
        orders = [f.get("order") for f in fields]
        if len(set(orders)) != len(orders):
            raise ValueError("字段 order 必须唯一")
        keys = {f.get("field_key") for f in fields}
        if len(keys) != len(fields):
            raise ValueError("field_key 必须唯一")
        selected_required = {f["field_key"] for f in fields if f.get("is_required")}
        missing = REQUIRED_TEMPLATE_FIELDS - selected_required
        if missing:
            raise ValueError(f"以下必填字段必须纳入模板并勾选必填: {sorted(missing)}")
        for f in fields:
            if f.get("field_source") == "extension" and f.get("ext_type") not in (
                "enum",
                "string",
            ):
                raise ValueError(f"扩展字段必须指定 ext_type: {f.get('field_key')}")
        return v


class MigrationTemplateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    space_id: int
    name: str
    config_json: dict
    created_by: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_by: Optional[str] = None
    updated_at: Optional[datetime] = None


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
