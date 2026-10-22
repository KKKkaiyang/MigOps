"""b04 任务迁移管理：迁移场景、任务台账、排查备注、自定义台账（空间库表）。

表结构依据《项目空间业务功能需求》§6.5；状态机依据 BRD 4.2。
"""

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    Index,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.mysql import JSON

from app.models.space_base import SpaceBase

# ── 迁移状态（BRD 4.2） ──
TASK_STATUS_NOT_STARTED = "未开始"
TASK_STATUS_DEV_DONE = "改造完成"
TASK_STATUS_SCHED_SUCCESS = "调度成功"
TASK_STATUS_CHECK_PASSED = "数据校验通过"
TASK_STATUS_CHECK_FAILED = "数据校验不通过"
TASK_STATUS_ACCEPT_PASSED = "客户验收通过"
TASK_STATUS_ACCEPT_FAILED = "客户验收不通过"
TASK_STATUS_SUSPENDED = "挂起"
TASK_STATUS_DISCARDED = "废弃"
TASK_STATUSES = (
    TASK_STATUS_NOT_STARTED,
    TASK_STATUS_DEV_DONE,
    TASK_STATUS_SCHED_SUCCESS,
    TASK_STATUS_CHECK_PASSED,
    TASK_STATUS_CHECK_FAILED,
    TASK_STATUS_ACCEPT_PASSED,
    TASK_STATUS_ACCEPT_FAILED,
    TASK_STATUS_SUSPENDED,
    TASK_STATUS_DISCARDED,
)
# 允许的状态流转：正向链 + 校验/验收不通过回退 + 任意正向态可挂起/废弃 + 挂起可恢复
TASK_STATUS_TRANSITIONS = {
    TASK_STATUS_NOT_STARTED: {
        TASK_STATUS_DEV_DONE,
        TASK_STATUS_SUSPENDED,
        TASK_STATUS_DISCARDED,
    },
    TASK_STATUS_DEV_DONE: {
        TASK_STATUS_SCHED_SUCCESS,
        TASK_STATUS_SUSPENDED,
        TASK_STATUS_DISCARDED,
    },
    TASK_STATUS_SCHED_SUCCESS: {
        TASK_STATUS_CHECK_PASSED,
        TASK_STATUS_CHECK_FAILED,
        TASK_STATUS_SUSPENDED,
        TASK_STATUS_DISCARDED,
    },
    TASK_STATUS_CHECK_PASSED: {
        TASK_STATUS_ACCEPT_PASSED,
        TASK_STATUS_ACCEPT_FAILED,
        TASK_STATUS_SUSPENDED,
        TASK_STATUS_DISCARDED,
    },
    TASK_STATUS_CHECK_FAILED: {
        TASK_STATUS_CHECK_PASSED,
        TASK_STATUS_SCHED_SUCCESS,
        TASK_STATUS_SUSPENDED,
        TASK_STATUS_DISCARDED,
    },
    TASK_STATUS_ACCEPT_PASSED: {
        TASK_STATUS_SUSPENDED,
        TASK_STATUS_DISCARDED,
    },
    TASK_STATUS_ACCEPT_FAILED: {
        TASK_STATUS_CHECK_PASSED,
        TASK_STATUS_CHECK_FAILED,
        TASK_STATUS_SCHED_SUCCESS,
        TASK_STATUS_SUSPENDED,
        TASK_STATUS_DISCARDED,
    },
    TASK_STATUS_SUSPENDED: {
        TASK_STATUS_NOT_STARTED,
        TASK_STATUS_DEV_DONE,
        TASK_STATUS_SCHED_SUCCESS,
        TASK_STATUS_CHECK_PASSED,
        TASK_STATUS_CHECK_FAILED,
        TASK_STATUS_ACCEPT_FAILED,
        TASK_STATUS_DISCARDED,
    },
    TASK_STATUS_DISCARDED: set(),
}

# ── 调度状态 ──
SCHEDULE_STATUS_NOT_SUBMITTED = "未提交"
SCHEDULE_STATUS_SUBMITTED = "已提交"
SCHEDULE_STATUS_RUNNING = "调度中"
SCHEDULE_STATUS_SUCCESS = "调度成功"
SCHEDULE_STATUS_FAILED = "调度失败"
SCHEDULE_STATUSES = (
    SCHEDULE_STATUS_NOT_SUBMITTED,
    SCHEDULE_STATUS_SUBMITTED,
    SCHEDULE_STATUS_RUNNING,
    SCHEDULE_STATUS_SUCCESS,
    SCHEDULE_STATUS_FAILED,
)

# ── 数据校验状态 ──
CHECK_STATUS_NONE = "未校验"
CHECK_STATUS_RUNNING = "校验中"
CHECK_STATUS_PASSED = "校验通过"
CHECK_STATUS_FAILED = "校验不通过"
CHECK_STATUSES = (
    CHECK_STATUS_NONE,
    CHECK_STATUS_RUNNING,
    CHECK_STATUS_PASSED,
    CHECK_STATUS_FAILED,
)

# ── 排查备注类型 ──
NOTE_KIND_TROUBLESHOOT = "troubleshoot"
NOTE_KIND_CHECK_RESULT = "check_result"
NOTE_KINDS = (NOTE_KIND_TROUBLESHOOT, NOTE_KIND_CHECK_RESULT)


class B04Scenario(SpaceBase):
    """任务迁移场景。"""

    __tablename__ = "b04_scenario"

    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="主键")
    space_id = Column(BigInteger, nullable=False, comment="所属空间")
    name = Column(String(128), nullable=False, comment="场景名称(如 hive→hive)")
    remark = Column(String(512), comment="场景说明")
    created_by = Column(String(64), comment="创建人")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    updated_by = Column(String(64), comment="更新人")
    updated_at = Column(
        DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间"
    )
    deleted_at = Column(DateTime, comment="逻辑删除时间")


class B04Task(SpaceBase):
    """任务台账。"""

    __tablename__ = "b04_task"
    __table_args__ = (
        UniqueConstraint("scenario_id", "task_uri", name="uk_scenario_task_uri"),
        Index("idx_space_scenario", "space_id", "scenario_id"),
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="主键")
    space_id = Column(BigInteger, nullable=False, comment="所属空间")
    scenario_id = Column(BigInteger, nullable=False, comment="迁移场景ID")
    workflow_name = Column(String(128), nullable=False, comment="工作流名称")
    task_name = Column(String(255), nullable=False, comment="任务名称")
    script_name = Column(String(255), comment="脚本名称")
    owner = Column(String(64), comment="任务Owner")
    task_uri = Column(
        String(512), nullable=False, comment="任务URI:项目名称://任务名称@工作流名称"
    )
    migration_status = Column(
        String(32), default=TASK_STATUS_NOT_STARTED, comment="迁移状态"
    )
    schedule_status = Column(
        String(32), default=SCHEDULE_STATUS_NOT_SUBMITTED, comment="调度状态"
    )
    check_status = Column(String(32), default=CHECK_STATUS_NONE, comment="数据校验状态")
    input_tables = Column(String(1024), comment="输入表(逗号分隔)")
    output_tables = Column(String(1024), comment="输出表(逗号分隔)")
    latest_note = Column(Text, comment="最新排查备注摘要(冗余)")
    created_by = Column(String(64), comment="创建人")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    updated_by = Column(String(64), comment="更新人")
    updated_at = Column(
        DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间"
    )
    deleted_at = Column(DateTime, comment="逻辑删除时间")


class B04TaskNote(SpaceBase):
    """排查备注（时间线）。"""

    __tablename__ = "b04_task_note"
    __table_args__ = (Index("idx_task", "task_id"),)

    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="主键")
    space_id = Column(BigInteger, nullable=False, comment="所属空间")
    task_id = Column(BigInteger, nullable=False, comment="任务ID")
    note_kind = Column(String(32), nullable=False, comment="troubleshoot|check_result")
    problem_desc = Column(Text, comment="问题描述")
    cause_analysis = Column(Text, comment="原因分析")
    fix_plan = Column(Text, comment="修复方案")
    created_by = Column(String(64), comment="备注人")
    created_at = Column(DateTime, default=datetime.now, comment="备注时间")
    updated_by = Column(String(64), comment="更新人")
    updated_at = Column(
        DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间"
    )
    deleted_at = Column(DateTime, comment="逻辑删除时间")


class B04SavedView(SpaceBase):
    """自定义台账（保存的筛选视图，数据引用原任务）。"""

    __tablename__ = "b04_saved_view"

    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="主键")
    space_id = Column(BigInteger, nullable=False, comment="所属空间")
    scenario_id = Column(BigInteger, nullable=False, comment="迁移场景ID")
    name = Column(String(128), nullable=False, comment="台账名称")
    description = Column(String(512), comment="台账描述")
    filter_config = Column(JSON, nullable=False, comment="筛选条件(JSON)")
    created_by = Column(String(64), comment="创建人")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    updated_by = Column(String(64), comment="更新人")
    updated_at = Column(
        DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间"
    )
    deleted_at = Column(DateTime, comment="逻辑删除时间")
