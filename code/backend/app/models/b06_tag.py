"""b06 标签管理：标签维护、标签查看、任务标签关联（空间库表）。

表结构依据《任务迁移-标签管理与标签化台账需求》§4；标签主表与标签查看归属本模块，
任务↔标签的关联为跨模块关联（标签来自 b06，任务来自 b04）。
"""

from datetime import datetime

from sqlalchemy import BigInteger, Column, DateTime, Index, String, UniqueConstraint

from app.models.space_base import SpaceBase


class B06Tag(SpaceBase):
    """空间级标签（标签管理：标签ID / 名称 / 描述 / 颜色）。"""

    __tablename__ = "b06_tag"
    __table_args__ = (
        UniqueConstraint("space_id", "tag_name", name="uk_space_tag_name"),
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="标签ID")
    space_id = Column(BigInteger, nullable=False, comment="所属空间")
    tag_name = Column(String(64), nullable=False, comment="标签名称(空间内唯一)")
    tag_description = Column(String(512), comment="标签描述")
    tag_category = Column(
        String(16),
        nullable=False,
        default="技术标签",
        comment="标签分类: 管理标签 / 技术标签",
    )
    color = Column(String(16), nullable=False, default="#1a73e8", comment="标签颜色(hex)")
    created_by = Column(String(64), comment="创建人")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    updated_by = Column(String(64), comment="更新人")
    updated_at = Column(
        DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间"
    )
    deleted_at = Column(DateTime, comment="逻辑删除时间")


class B06TaskTag(SpaceBase):
    """任务-标签关联（多对多，关联 b04_task）。"""

    __tablename__ = "b06_task_tag"
    __table_args__ = (
        UniqueConstraint("task_id", "tag_id", name="uk_task_tag"),
        Index("idx_space_tag", "space_id", "tag_id"),
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="主键")
    space_id = Column(BigInteger, nullable=False, comment="所属空间")
    task_id = Column(BigInteger, nullable=False, comment="任务ID(b04_task)")
    tag_id = Column(BigInteger, nullable=False, comment="标签ID(b06_tag)")
    created_by = Column(String(64), comment="创建人")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    updated_by = Column(String(64), comment="更新人")
    updated_at = Column(
        DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间"
    )
    deleted_at = Column(DateTime, comment="逻辑删除时间")
