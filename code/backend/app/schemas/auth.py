from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class LoginIn(BaseModel):
    """登录请求。连续失败达到阈值后 captcha_id / captcha_code 必填。"""

    username: str = Field(..., min_length=1, max_length=64)
    password: str = Field(..., min_length=1, max_length=128)
    captcha_id: Optional[str] = None
    captcha_code: Optional[str] = None


class UserBrief(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    username: str
    name: str
    org_type: Optional[str] = None


class LoginOut(BaseModel):
    token: str
    token_type: str = "Bearer"
    expires_in: int
    user: UserBrief
    must_change_password: bool


class ChangePasswordIn(BaseModel):
    old_password: str = Field(..., min_length=1, max_length=128)
    new_password: str = Field(..., min_length=1, max_length=128)


class CaptchaOut(BaseModel):
    captcha_id: str
    svg: str


class CurrentUserOut(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    username: str
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    org_type: Optional[str] = None
    status: str
    is_l0: bool
    roles: list[dict]
    last_login_at: Optional[datetime] = None
