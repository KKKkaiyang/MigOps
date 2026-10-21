from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class SpaceCreate(BaseModel):
    space_name: str
    customer_name: Optional[str] = None
    source_platform: Optional[str] = None
    target_platform: Optional[str] = None
    owner: Optional[str] = None
    remark: Optional[str] = None


class SpaceUpdate(BaseModel):
    space_name: Optional[str] = None
    customer_name: Optional[str] = None
    source_platform: Optional[str] = None
    target_platform: Optional[str] = None
    owner: Optional[str] = None
    remark: Optional[str] = None


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
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
