"""b03 数据迁移管理：迁移场景、库表清单、迁移过程记录（空间库表）。

表结构依据《项目空间业务功能需求》§5.3；状态枚举与 BRD 6.3 对齐。
"""

from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    Column,
    Date,
    DateTime,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)

from app.models.space_base import SpaceBase

# 表类型
TABLE_TYPE_INTERNAL = "内部表"
TABLE_TYPE_EXTERNAL = "外部表"
TABLE_TYPE_VIEW = "视图"
TABLE_TYPE_PARTITION = "分区表"
TABLE_TYPES = (
    TABLE_TYPE_INTERNAL,
    TABLE_TYPE_EXTERNAL,
    TABLE_TYPE_VIEW,
    TABLE_TYPE_PARTITION,
)

# 元数据迁移状态 / 全量迁移状态
MIGRATION_STATUS_PENDING = "未迁移"
MIGRATION_STATUS_RUNNING = "迁移中"
MIGRATION_STATUS_DONE = "已完成"
MIGRATION_STATUS_ERROR = "异常"
METADATA_STATUSES = FULL_SYNC_STATUSES = (
    MIGRATION_STATUS_PENDING,
    MIGRATION_STATUS_RUNNING,
    MIGRATION_STATUS_DONE,
    MIGRATION_STATUS_ERROR,
)

# 增量迁移状态
INCR_STATUS_NOT_STARTED = "未开始"
INCR_STATUS_RUNNING = "进行中"
INCR_STATUS_STOPPED = "已停止"
INCR_STATUS_ERROR = "异常"
INCR_SYNC_STATUSES = (
    INCR_STATUS_NOT_STARTED,
    INCR_STATUS_RUNNING,
    INCR_STATUS_STOPPED,
    INCR_STATUS_ERROR,
)

# 迁移过程记录
MIGRATION_TYPE_FULL = "全量历史迁移"
MIGRATION_TYPE_INCR = "增量迁移"
MIGRATION_TYPES = (MIGRATION_TYPE_FULL, MIGRATION_TYPE_INCR)
RECORD_STATUS_SUCCESS = "成功"
RECORD_STATUS_FAILED = "失败"
RECORD_STATUS_PARTIAL = "部分成功"
RECORD_STATUSES = (RECORD_STATUS_SUCCESS, RECORD_STATUS_FAILED, RECORD_STATUS_PARTIAL)


class B03Scenario(SpaceBase):
    """数据迁移场景。"""

    __tablename__ = "b03_scenario"

    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="主键")
    space_id = Column(BigInteger, nullable=False, comment="所属空间")
    name = Column(String(128), nullable=False, comment="场景名称")
    remark = Column(String(512), comment="场景说明")
    created_by = Column(String(64), comment="创建人")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    updated_by = Column(String(64), comment="更新人")
    updated_at = Column(
        DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间"
    )
    deleted_at = Column(DateTime, comment="逻辑删除时间")


class B03TableItem(SpaceBase):
    """库表清单。"""

    __tablename__ = "b03_table_item"
    __table_args__ = (
        UniqueConstraint("scenario_id", "db_name", "table_name", name="uk_scenario_table"),
        Index("idx_space_scenario", "space_id", "scenario_id"),
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="主键")
    space_id = Column(BigInteger, nullable=False, comment="所属空间")
    scenario_id = Column(BigInteger, nullable=False, comment="迁移场景ID")
    db_name = Column(String(128), nullable=False, comment="源库名")
    table_name = Column(String(128), nullable=False, comment="源表名")
    target_db_name = Column(String(128), comment="目标库名")
    target_table_name = Column(String(128), comment="目标表名")
    table_type = Column(String(32), comment="表类型:内部表|外部表|视图|分区表")
    data_volume = Column(BigInteger, comment="预估数据量(行数)")
    partition_count = Column(Integer, comment="分区数")
    metadata_status = Column(
        String(32), default=MIGRATION_STATUS_PENDING, comment="元数据迁移状态"
    )
    full_sync_status = Column(
        String(32), default=MIGRATION_STATUS_PENDING, comment="全量迁移状态"
    )
    full_sync_cutoff_date = Column(Date, comment="全量迁移数据截止日期")
    incr_sync_status = Column(
        String(32), default=INCR_STATUS_NOT_STARTED, comment="增量迁移状态"
    )
    incr_sync_latest_at = Column(DateTime, comment="增量最新同步时间点")
    remark = Column(String(1024), comment="备注")
    created_by = Column(String(64), comment="创建人")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    updated_by = Column(String(64), comment="更新人")
    updated_at = Column(
        DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间"
    )
    deleted_at = Column(DateTime, comment="逻辑删除时间")


class B03MigrationRecord(SpaceBase):
    """迁移过程记录。"""

    __tablename__ = "b03_migration_record"
    __table_args__ = (Index("idx_table_item", "table_item_id"),)

    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="主键")
    space_id = Column(BigInteger, nullable=False, comment="所属空间")
    scenario_id = Column(BigInteger, nullable=False, comment="迁移场景ID")
    table_item_id = Column(BigInteger, nullable=False, comment="库表清单ID")
    migration_type = Column(String(32), nullable=False, comment="全量历史迁移|增量迁移")
    started_at = Column(DateTime, comment="开始时间")
    finished_at = Column(DateTime, comment="结束时间")
    data_volume = Column(BigInteger, comment="本次迁移数据量(行数)")
    method = Column(String(64), comment="迁移方式(DistCp/DataX/Sqoop/自研工具等)")
    data_cutoff_date = Column(Date, comment="本次数据截止日期")
    status = Column(String(32), nullable=False, comment="成功|失败|部分成功")
    remark = Column(String(1024), comment="异常说明或备注")
    created_by = Column(String(64), comment="操作人")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    updated_by = Column(String(64), comment="更新人")
    updated_at = Column(
        DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间"
    )
    deleted_at = Column(DateTime, comment="逻辑删除时间")
