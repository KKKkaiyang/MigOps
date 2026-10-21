from typing import Generic, Optional, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    """统一响应结构。code=0 表示成功。"""

    code: int = 0
    message: str = "ok"
    data: Optional[T] = None
    trace_id: Optional[str] = None


def ok(data=None, message: str = "ok"):
    return ApiResponse(code=0, message=message, data=data)


def fail(code: int = 1, message: str = "error", data=None):
    return ApiResponse(code=code, message=message, data=data)


class PageData(BaseModel, Generic[T]):
    """分页数据结构。"""

    list: list[T]
    total: int
    page: int
    page_size: int
