from datetime import datetime

from sqlalchemy import BigInteger, Column, DateTime, String

from app.models.base import Base

# API 密钥状态
API_KEY_STATUS_ENABLED = "启用"
API_KEY_STATUS_DISABLED = "停用"


class CommonUserApiKey(Base):
    """common_user_api_key 用户 API 密钥（mig_common_db）。

    用于 REST API 的 ak/sk HMAC 签名鉴权；secret_key 加密存储，仅生成时明文展示一次。
    """

    __tablename__ = "common_user_api_key"

    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="密钥 ID")
    user_id = Column(BigInteger, nullable=False, comment="关联 common_user.id")
    access_key = Column(String(64), unique=True, nullable=False, comment="访问标识(明文)")
    secret_key_enc = Column(String(512), nullable=False, comment="密钥(加密存储,可逆)")
    status = Column(String(16), default=API_KEY_STATUS_ENABLED, comment="状态:启用|停用")
    last_used_at = Column(DateTime, comment="最近使用时间")

    created_by = Column(String(64), comment="创建人")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    updated_by = Column(String(64), comment="更新人")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")
    deleted_at = Column(DateTime, comment="逻辑删除时间")
