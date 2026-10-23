"""b06 标签管理 Schema（Pydantic v2）。"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class TagBrief(BaseModel):
    """任务上展示用的精简标签信息。"""

    id: int
    name: str
    color: str


class TagCreate(BaseModel):
    tag_name: str = Field(..., min_length=1, max_length=64)
    tag_description: Optional[str] = Field(None, max_length=512)
    tag_category: str = Field("技术标签", max_length=16, description="标签分类: 管理标签 / 技术标签")
    color: str = Field("#1a73e8", max_length=16, description="hex 颜色，如 #1a73e8")


class TagUpdate(BaseModel):
    tag_name: Optional[str] = Field(None, min_length=1, max_length=64)
    tag_description: Optional[str] = Field(None, max_length=512)
    tag_category: Optional[str] = Field(None, max_length=16, description="标签分类: 管理标签 / 技术标签")
    color: Optional[str] = Field(None, max_length=16)


class TagOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tag_name: str
    tag_description: Optional[str] = None
    tag_category: str = "技术标签"
    color: str
    task_count: int = 0
    created_by: Optional[str] = None
    created_at: Optional[datetime] = None


class TaskTagIn(BaseModel):
    """任务标签整体替换（set）。"""

    tag_ids: List[int] = Field(..., description="该任务关联的标签ID列表（整体替换）")


class TaskBatchTagIn(BaseModel):
    """批量打标签 / 去标签。"""

    ids: List[int] = Field(..., min_length=1, description="任务ID列表")
    tag_ids: List[int] = Field(..., min_length=1, description="操作的标签ID列表")
    action: str = Field("add", description="add=批量打标签;remove=批量移除标签")
