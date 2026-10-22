class BizError(Exception):
    """业务异常，由全局异常处理器统一转换为 ApiResponse。"""

    def __init__(self, message: str, code: int = 40000):
        self.message = message
        self.code = code
        super().__init__(message)


class NotFoundError(BizError):
    def __init__(self, message: str = "资源不存在"):
        super().__init__(message, code=40400)


class ForbiddenError(BizError):
    def __init__(self, message: str = "无权限操作"):
        super().__init__(message, code=40300)


class UnauthorizedError(BizError):
    """未登录 / 登录态失效。"""

    def __init__(self, message: str = "未登录或登录已失效"):
        super().__init__(message, code=40100)


class CaptchaError(BizError):
    """验证码缺失 / 错误 / 过期。"""

    def __init__(self, message: str = "验证码错误或已过期"):
        super().__init__(message, code=40001)
