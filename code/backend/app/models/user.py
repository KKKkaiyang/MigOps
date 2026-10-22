from datetime import datetime

from sqlalchemy import BigInteger, Column, DateTime, SmallInteger, String

from app.models.base import Base

# 账号状态
USER_STATUS_ENABLED = "enabled"  # 启用
USER_STATUS_DISABLED = "disabled"  # 停用（注销语义：可恢复）

# 用户归属（仅标签区分，无功能权限差异）
ORG_TYPE_INTERNAL = "内部"
ORG_TYPE_TENCENT = "腾讯"
ORG_TYPE_PARTNER = "其他厂商"
ORG_TYPE_CUSTOMER = "客户"
ORG_TYPES = (
    ORG_TYPE_INTERNAL,
    ORG_TYPE_TENCENT,
    ORG_TYPE_PARTNER,
    ORG_TYPE_CUSTOMER,
)


class CommonUser(Base):
    """common_user 公共业务：平台用户（认证与账号体系）。"""

    __tablename__ = "common_user"

    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="用户ID")
    username = Column(String(64), unique=True, nullable=False, comment="登录用户名")
    password = Column(String(128), nullable=False, comment="密码密文(bcrypt)")
    name = Column(String(64), nullable=False, comment="姓名")
    email = Column(String(128), comment="邮箱")
    phone = Column(String(32), comment="手机号")
    org_type = Column(String(32), comment="用户归属:内部|腾讯|其他厂商|客户")
    status = Column(
        String(32), default=USER_STATUS_ENABLED, comment="账号状态:enabled|disabled"
    )

    # 登录安全控制
    login_fail_count = Column(SmallInteger, default=0, comment="连续登录失败次数")
    locked_until = Column(DateTime, comment="账号锁定截止时间")
    last_fail_at = Column(DateTime, comment="最近一次登录失败时间")
    last_login_at = Column(DateTime, comment="最近一次登录成功时间")
    must_change_password = Column(
        SmallInteger, default=0, comment="是否强制修改密码:0否|1是"
    )

    created_by = Column(String(64), comment="创建人")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    updated_by = Column(String(64), comment="更新人")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")
    deleted_at = Column(DateTime, comment="逻辑删除时间")
