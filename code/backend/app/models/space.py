from datetime import datetime

from sqlalchemy import BigInteger, Column, DateTime, SmallInteger, String, Text

from app.models.base import Base

# 项目空间状态机：初始化 → 交付中 → 已验收
SPACE_STATUS_INIT = "初始化"
SPACE_STATUS_DELIVERING = "交付中"
SPACE_STATUS_ACCEPTED = "已验收"
# 物理删除后的归档状态（空间业务库已销毁，公共库元数据逻辑保留，便于审计追溯）
SPACE_STATUS_DELETED = "已删除"
SPACE_STATUSES = (
    SPACE_STATUS_INIT,
    SPACE_STATUS_DELIVERING,
    SPACE_STATUS_ACCEPTED,
)
# 允许的状态流转（目标状态集合）
SPACE_STATUS_TRANSITIONS = {
    SPACE_STATUS_INIT: {SPACE_STATUS_DELIVERING},
    SPACE_STATUS_DELIVERING: {SPACE_STATUS_ACCEPTED},
    SPACE_STATUS_ACCEPTED: set(),
}

# 项目简称（space_code）约束：小写字母开头，可含小写字母/数字/下划线
SPACE_CODE_PATTERN = r"^[a-z][a-z0-9_]{1,30}$"


class MigSpace(Base):
    """b01_ 项目空间管理：迁移空间（项目隔离单元）。"""

    __tablename__ = "b01_space"

    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="主键")
    space_code = Column(String(64), unique=True, nullable=False, comment="空间编码(项目简称)")
    space_name = Column(String(128), nullable=False, comment="项目名称")
    customer_name = Column(String(128), comment="客户名称")
    source_platform = Column(String(64), comment="源端平台(华为云/阿里云/私有云/火山云)")
    target_platform = Column(String(64), comment="目标平台(腾讯云/AWS/Azure)")
    start_date = Column(DateTime, comment="项目周期开始")
    end_date = Column(DateTime, comment="项目周期结束")
    owner = Column(String(64), comment="负责人")
    status = Column(
        String(32), default=SPACE_STATUS_INIT, comment="空间状态:初始化|交付中|已验收"
    )
    overall_progress = Column(
        SmallInteger, default=0, nullable=False, comment="整体进展(0-100,手工维护)"
    )
    remark = Column(Text, comment="项目空间说明")
    db_name = Column(String(128), unique=True, comment="绑定数据库名:mig_<space_code>_db")

    created_by = Column(String(64), comment="创建人")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    updated_by = Column(String(64), comment="更新人")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")
    deleted_at = Column(DateTime, comment="逻辑删除时间")


class SpaceDeleteLog(Base):
    """空间物理删除审计日志。

    空间业务库（mig_<space_code>_db）被 DROP 后不可恢复，故删除动作须落审计于公共库，
    留存操作人、被删空间标识与被删库名快照，满足可追溯要求。
    """

    __tablename__ = "b01_space_delete_log"

    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="主键")
    space_id = Column(BigInteger, comment="原空间 ID")
    space_name = Column(String(128), comment="空间名称（删除时快照）")
    space_code = Column(String(64), comment="空间编码（删除时快照）")
    db_name = Column(String(128), comment="被删除的数据库名（删除时快照）")
    operator = Column(String(64), comment="操作人（用户 ID / 用户名）")
    created_at = Column(DateTime, default=datetime.now, comment="删除时间")
