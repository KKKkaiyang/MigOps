"""b02 项目资料管理：资料分类与资料索引（空间库表）。

表结构依据《项目空间业务功能需求》§4.5；类型码值依据 D1（三种）。
"""

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    Integer,
    SmallInteger,
    String,
    Text,
)
from sqlalchemy.dialects.mysql import LONGTEXT

from app.models.space_base import SpaceBase

# 资料类型（需求 §4.2 / 确认决策 D1）
MATERIAL_TYPE_EXTERNAL_LINK = "external_link"
MATERIAL_TYPE_MARKDOWN = "markdown"
MATERIAL_TYPE_PLATFORM_LEDGER = "platform_ledger"
MATERIAL_TYPES = (
    MATERIAL_TYPE_EXTERNAL_LINK,
    MATERIAL_TYPE_MARKDOWN,
    MATERIAL_TYPE_PLATFORM_LEDGER,
)

# 平台台账预置跳转目标（确认决策 D14：一期仅 b03/b04，随模块扩展补充）
PLATFORM_LEDGER_TARGETS = {
    "b03": "数据迁移管理",
    "b04": "任务迁移管理",
}

# 预置资料分类（需求 §4.3 / BRD 6.2）
PRESET_CATEGORIES = [
    ("项目管理类", 1),
    ("调研资料类", 2),
    ("代码与迁移类", 3),
]


class B02Category(SpaceBase):
    """资料分类。"""

    __tablename__ = "b02_category"

    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="主键")
    space_id = Column(BigInteger, nullable=False, comment="所属空间")
    name = Column(String(64), nullable=False, comment="分类名称")
    sort_no = Column(Integer, default=0, comment="展示排序")
    is_preset = Column(SmallInteger, default=0, comment="是否预置分类(0/1)")
    created_by = Column(String(64), comment="创建人")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    updated_by = Column(String(64), comment="更新人")
    updated_at = Column(
        DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间"
    )
    deleted_at = Column(DateTime, comment="逻辑删除时间")


class B02Material(SpaceBase):
    """资料索引。"""

    __tablename__ = "b02_material"

    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="主键")
    space_id = Column(BigInteger, nullable=False, comment="所属空间")
    category_id = Column(BigInteger, comment="分类ID;NULL=未分类")
    name = Column(String(255), nullable=False, comment="资料名称")
    type = Column(
        String(32),
        nullable=False,
        comment="类型:external_link|markdown|platform_ledger",
    )
    url = Column(String(1024), comment="外部链接地址")
    target_module = Column(String(64), comment="平台台账跳转目标模块")
    content = Column(LONGTEXT, comment="Markdown原文")
    view_password_hash = Column(String(255), comment="查看/下载密码哈希;NULL=无需密码")
    view_pwd_fail_count = Column(Integer, default=0, comment="密码连续失败计数")
    view_pwd_locked_until = Column(DateTime, comment="密码验证锁定截止时间")
    description = Column(String(512), comment="描述信息")
    sort_no = Column(Integer, default=0, comment="排序;置顶设较大值")
    created_by = Column(String(64), comment="创建人")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    updated_by = Column(String(64), comment="更新人")
    updated_at = Column(
        DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间"
    )
    deleted_at = Column(DateTime, comment="逻辑删除时间")
