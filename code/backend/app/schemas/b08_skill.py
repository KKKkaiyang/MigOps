from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class SkillCreate(BaseModel):
    """手工 / REST API 上传 skill 的元数据（文件单独以 multipart 传）。"""

    name: str = Field(..., min_length=1, max_length=128, description="skill 名称(平台级唯一)")
    intro: Optional[str] = Field(None, max_length=500, description="简介(市场截断展示)")
    is_public: int = Field(1, description="是否公开:1公开|0私有")


class SkillStatusUpdate(BaseModel):
    status: str = Field(..., description="状态:上架|下架")


class SkillOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    skill_code: str
    name: str
    intro: Optional[str] = None
    is_public: int
    status: str
    download_count: int
    author_user_id: int
    author_name: Optional[str] = None
    version: str
    file_size: Optional[int] = None
    created_at: Optional[datetime] = None
