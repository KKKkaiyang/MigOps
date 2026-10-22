from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class UserCreate(BaseModel):
    username: str = Field(..., min_length=1, max_length=64)
    name: str = Field(..., min_length=1, max_length=64)
    org_type: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    # 不传则由系统生成满足复杂度策略的临时密码
    password: Optional[str] = None


class UserUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=64)
    org_type: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None


class RoleItem(BaseModel):
    role_level: str = Field(..., pattern="^L[012]$")
    space_id: Optional[int] = None


class RoleSetIn(BaseModel):
    roles: List[RoleItem]


class UserOut(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    username: str
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    org_type: Optional[str] = None
    status: str
    last_login_at: Optional[datetime] = None
    created_at: Optional[datetime] = None


class UserRoleOut(BaseModel):
    id: int
    role_level: str
    role_name: str
    space_id: Optional[int] = None
    space_name: Optional[str] = None


class ResetPasswordOut(BaseModel):
    temp_password: str
