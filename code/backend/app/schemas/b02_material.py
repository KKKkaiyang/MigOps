"""b02 项目资料管理 Schema（Pydantic v2）。"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.b02_material import MATERIAL_TYPES, PLATFORM_LEDGER_TARGETS


class CategoryCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=64, description="分类名称")
    sort_no: int = 0


class CategoryUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=64)
    sort_no: Optional[int] = None


class CategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    sort_no: int
    is_preset: int
    material_count: int = 0


class MaterialCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="资料名称")
    type: str = Field(..., description="external_link|markdown|platform_ledger")
    category_id: Optional[int] = None
    url: Optional[str] = Field(None, max_length=1024)
    target_module: Optional[str] = None
    content: Optional[str] = None
    description: Optional[str] = Field(None, max_length=512)
    sort_no: int = 0
    view_password: Optional[str] = Field(
        None, max_length=64, description="查看/下载密码;不传=无需密码"
    )

    @field_validator("type")
    @classmethod
    def _check_type(cls, v: str) -> str:
        if v not in MATERIAL_TYPES:
            raise ValueError(f"非法的资料类型: {v}")
        return v

    @field_validator("target_module")
    @classmethod
    def _check_target(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in PLATFORM_LEDGER_TARGETS:
            raise ValueError(f"非法的平台台账跳转目标: {v}")
        return v


class MaterialUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    type: Optional[str] = None
    category_id: Optional[int] = None
    url: Optional[str] = Field(None, max_length=1024)
    target_module: Optional[str] = None
    content: Optional[str] = None
    description: Optional[str] = Field(None, max_length=512)
    sort_no: Optional[int] = None
    # view_password: 不传=不修改；空串=清除密码；非空=设置新密码
    view_password: Optional[str] = Field(None, max_length=64)

    @field_validator("type")
    @classmethod
    def _check_type(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in MATERIAL_TYPES:
            raise ValueError(f"非法的资料类型: {v}")
        return v

    @field_validator("target_module")
    @classmethod
    def _check_target(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in PLATFORM_LEDGER_TARGETS:
            raise ValueError(f"非法的平台台账跳转目标: {v}")
        return v


class MaterialOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    space_id: int
    category_id: Optional[int] = None
    name: str
    type: str
    url: Optional[str] = None
    target_module: Optional[str] = None
    # 仅详情端点在密码校验通过后返回; 列表恒为 None
    content: Optional[str] = None
    description: Optional[str] = None
    sort_no: int = 0
    # 是否设置了查看密码（不返回哈希本身）
    has_password: bool = False
    created_by: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_by: Optional[str] = None
    updated_at: Optional[datetime] = None


class VerifyPasswordIn(BaseModel):
    password: str = Field(..., min_length=1, max_length=64)


class VerifyPasswordOut(BaseModel):
    view_token: str
    expires_in: int
