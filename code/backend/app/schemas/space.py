from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.space import SPACE_CODE_PATTERN


class SpaceCreate(BaseModel):
    space_code: str = Field(..., min_length=2, max_length=32, description="项目简称(英文字母)")
    space_name: str = Field(..., min_length=1, max_length=128)
    customer_name: Optional[str] = None
    source_platform: Optional[str] = None
    target_platform: Optional[str] = None
    owner: Optional[str] = None
    remark: Optional[str] = None
    overall_progress: Optional[int] = Field(None, ge=0, le=100, description="整体进展(0-100)")
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

    @field_validator("space_code")
    @classmethod
    def _validate_code(cls, v: str) -> str:
        import re

        v = v.strip().lower()
        if not re.match(SPACE_CODE_PATTERN, v):
            raise ValueError("项目简称须为小写字母开头，可含小写字母/数字/下划线，长度 2~32")
        return v


class SpaceUpdate(BaseModel):
    space_name: Optional[str] = Field(None, min_length=1, max_length=128)
    customer_name: Optional[str] = None
    source_platform: Optional[str] = None
    target_platform: Optional[str] = None
    owner: Optional[str] = None
    remark: Optional[str] = None
    overall_progress: Optional[int] = Field(None, ge=0, le=100, description="整体进展(0-100)")
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


class SpaceStatusIn(BaseModel):
    status: str


class SpaceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    space_code: str
    space_name: str
    customer_name: Optional[str] = None
    source_platform: Optional[str] = None
    target_platform: Optional[str] = None
    owner: Optional[str] = None
    status: str
    overall_progress: int = 0
    remark: Optional[str] = None
    db_name: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    # 后端按当前登录用户计算其在该空间内的角色（L0 恒为 L0）
    my_role: Optional[str] = None
    # 后端聚合的空间成员数
    member_count: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class SpaceMemberIn(BaseModel):
    user_id: int
    role_level: str = Field(..., pattern="^L[12]$")


class SpaceMemberRoleIn(BaseModel):
    role_level: str = Field(..., pattern="^L[12]$")


class SpaceMemberOut(BaseModel):
    user_id: int
    username: str
    name: str
    org_type: Optional[str] = None
    role_level: str
    role_name: str


class SpaceStatsOut(BaseModel):
    """空间真实统计（供空间概览页展示，数据由各业务模块聚合）。"""

    b02_material_count: int = 0
    b02_category_count: int = 0
    b03_scenario_count: int = 0
    b03_table_total: int = 0
    b03_metadata_stats: dict = Field(default_factory=dict)
    b03_full_sync_stats: dict = Field(default_factory=dict)
    b03_incr_sync_stats: dict = Field(default_factory=dict)
    b03_record_count: int = 0
    b04_scenario_count: int = 0
    b04_task_total: int = 0
    b04_migration_stats: dict = Field(default_factory=dict)
    b04_note_count: int = 0
    b04_view_count: int = 0
    b04_fixed_view_count: int = 0
    b06_tag_count: int = 0
    b06_manage_tag_count: int = 0
    b06_tech_tag_count: int = 0
    b07_edge_count: int = 0
    b07_workflow_count: int = 0
