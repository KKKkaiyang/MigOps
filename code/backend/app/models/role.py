from datetime import datetime

from sqlalchemy import BigInteger, Column, DateTime, String

from app.models.base import Base

# 角色等级
ROLE_L0 = "L0"  # 系统管理员（全局）
ROLE_L1 = "L1"  # 项目管理员（按空间）
ROLE_L2 = "L2"  # 项目成员（按空间）
ROLE_LEVELS = (ROLE_L0, ROLE_L1, ROLE_L2)

ROLE_LEVEL_NAMES = {
    ROLE_L0: "系统管理员",
    ROLE_L1: "项目管理员",
    ROLE_L2: "项目成员",
}


class CommonUserRole(Base):
    """common_user_role 公共业务：用户-角色绑定。

    L0 为全局角色，space_id 为空；L1/L2 绑定到具体项目空间，
    同一用户在不同空间可拥有不同角色。
    """

    __tablename__ = "common_user_role"

    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="主键")
    user_id = Column(BigInteger, nullable=False, index=True, comment="用户ID")
    role_level = Column(String(8), nullable=False, comment="角色等级:L0|L1|L2")
    space_id = Column(BigInteger, index=True, comment="空间ID(L0为空)")

    created_by = Column(String(64), comment="创建人")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
