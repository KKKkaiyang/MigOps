"""skill 文件存储抽象（b08）。

当前提供本地磁盘实现；后续可新增对象存储（COS/OSS）实现，业务层不感知切换（决策 D5）。
"""

import os
from abc import ABC, abstractmethod

from app.config import settings


class StorageBackend(ABC):
    """存储后端抽象。"""

    @abstractmethod
    def save(self, relative_path: str, data: bytes) -> None:
        """按相对路径保存文件内容。"""

    @abstractmethod
    def exists(self, relative_path: str) -> bool:
        """相对路径文件是否存在。"""

    @abstractmethod
    def abs_path(self, relative_path: str) -> str:
        """返回用于 FileResponse 的绝对路径。"""


class LocalStorageBackend(StorageBackend):
    """本地磁盘实现：根目录为 settings.SKILL_STORAGE_DIR。"""

    def __init__(self, root: str | None = None) -> None:
        self.root = os.path.abspath(root or settings.SKILL_STORAGE_DIR)
        os.makedirs(self.root, exist_ok=True)

    def _full(self, relative_path: str) -> str:
        # 防御路径穿越：归一到 root 之内
        full = os.path.normpath(os.path.join(self.root, relative_path))
        if not full.startswith(self.root + os.sep) and full != self.root:
            raise ValueError("非法的存储路径")
        return full

    def save(self, relative_path: str, data: bytes) -> None:
        full = self._full(relative_path)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "wb") as f:
            f.write(data)

    def exists(self, relative_path: str) -> bool:
        return os.path.isfile(self._full(relative_path))

    def abs_path(self, relative_path: str) -> str:
        return self._full(relative_path)


storage: StorageBackend = LocalStorageBackend()
