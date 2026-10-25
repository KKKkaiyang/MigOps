from datetime import datetime

from sqlalchemy import BigInteger, Column, DateTime, Integer, String

from app.models.base import Base

# skill 状态
SKILL_STATUS_ONSHELF = "上架"  # 上架（公开且上架才在市场可见）
SKILL_STATUS_OFFSHELF = "下架"  # 下架（作者可管理，但不出现在市场）

# 可见性
SKILL_PUBLIC = 1  # 公开
SKILL_PRIVATE = 0  # 私有


class B08Skill(Base):
    """b08_skill 平台级 skill 主表（mig_common_db）。

    市场可见条件：is_public=1 且 status=上架 且 deleted_at IS NULL（决策 D6）。
    """

    __tablename__ = "b08_skill"

    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="skill ID")
    skill_code = Column(String(64), unique=True, nullable=False, comment="skill 编码(平台级唯一)")
    name = Column(String(128), unique=True, nullable=False, comment="skill 名称(平台级唯一)")
    intro = Column(String(500), comment="简介(市场截断展示)")
    author_user_id = Column(BigInteger, nullable=False, comment="上传者,关联 common_user.id")
    is_public = Column(Integer, default=SKILL_PUBLIC, comment="是否公开:1公开|0私有")
    status = Column(String(16), default=SKILL_STATUS_ONSHELF, comment="状态:上架|下架")
    download_count = Column(Integer, default=0, comment="使用热度(累计下载次数)")
    file_path = Column(String(512), nullable=False, comment="文件相对存储路径")
    file_size = Column(BigInteger, comment="文件大小(字节)")
    version = Column(String(32), default="1.0.0", comment="版本")

    created_by = Column(String(64), comment="创建人")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    updated_by = Column(String(64), comment="更新人")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")
    deleted_at = Column(DateTime, comment="逻辑删除时间")
