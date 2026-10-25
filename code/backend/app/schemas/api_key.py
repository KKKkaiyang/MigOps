from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class ApiKeyOut(BaseModel):
    """密钥列表项：secret 掩码，不返回明文。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    access_key: str
    status: str
    last_used_at: Optional[datetime] = None
    created_at: Optional[datetime] = None


class ApiKeyCreated(BaseModel):
    """生成密钥的返回：secret_key 仅此一次明文，需提示用户保存。"""

    id: int
    access_key: str
    secret_key: str
    status: str
