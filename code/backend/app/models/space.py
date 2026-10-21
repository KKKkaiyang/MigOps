from datetime import datetime

from sqlalchemy import BigInteger, Column, DateTime, String, Text

from app.models.base import Base


class MigSpace(Base):
    """b01_ 项目空间管理：迁移空间（项目隔离单元）。"""

    __tablename__ = "b01_space"

    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="主键")
    space_code = Column(String(64), unique=True, nullable=False, comment="空间编码")
    space_name = Column(String(128), nullable=False, comment="项目名称")
    customer_name = Column(String(128), comment="客户名称")
    source_platform = Column(String(64), comment="源端平台(华为云/阿里云/私有云/火山云)")
    target_platform = Column(String(64), comment="目标平台(腾讯云/AWS/Azure)")
    start_date = Column(DateTime, comment="项目周期开始")
    end_date = Column(DateTime, comment="项目周期结束")
    owner = Column(String(64), comment="负责人")
    status = Column(String(32), default="active", comment="active|archived")
    remark = Column(Text, comment="备注")

    created_by = Column(String(64), comment="创建人")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    updated_by = Column(String(64), comment="更新人")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")
    deleted_at = Column(DateTime, comment="逻辑删除时间")
