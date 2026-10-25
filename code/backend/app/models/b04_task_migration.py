"""b04 任务迁移管理：迁移场景、任务台账（基础表+扩展表）、迁移模板、排查备注、自定义台账（空间库表）。

表结构依据《任务迁移-任务台账数据模型重构需求》V1.0（决策 D1~D7）：
- `b04_task`（基础表）：15 业务字段 + 5 维独立状态，替代旧单表 + 10 态状态机。
- `b04_task_ext`（扩展表）：与基础表一对一，按空间模板动态加列 `f_1…n`（ORM 仅定义 task_id）。
- `b04_migration_template`（空间级模板）：每空间一份，`config_json` 驱动字段选择/必填/排序/列表展示/导入。
"""

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.mysql import JSON

from app.models.space_base import SpaceBase

# ── 5 维独立状态（整体替换旧 migration_status 10 态 / schedule_status / check_status，D1） ──
# 任务活跃状态
ACTIVE_STATUS_DRAFT = "草稿"
ACTIVE_STATUS_SCHEDULING = "正常调度"
ACTIVE_STATUS_OFFLINE = "下线"
ACTIVE_STATUS_FROZEN = "冻结"
ACTIVE_STATUSES = (
    ACTIVE_STATUS_DRAFT,
    ACTIVE_STATUS_SCHEDULING,
    ACTIVE_STATUS_OFFLINE,
    ACTIVE_STATUS_FROZEN,
)

# 迁移状态
MIGRATION_STATUS_NOT_STARTED = "未开始"
MIGRATION_STATUS_MIGRATING = "迁移中"
MIGRATION_STATUS_DONE = "已完成"
MIGRATION_STATUSES = (
    MIGRATION_STATUS_NOT_STARTED,
    MIGRATION_STATUS_MIGRATING,
    MIGRATION_STATUS_DONE,
)

# 双跑调度状态（替代旧 schedule_status）
DUALRUN_STATUS_NOT_SCHEDULED = "未调度"
DUALRUN_STATUS_SCHEDULING = "调度中"
DUALRUN_STATUS_DRYRUN = "空跑调度"
DUALRUN_STATUS_SUBMIT_ERROR = "提交报错"
DUALRUN_STATUSES = (
    DUALRUN_STATUS_NOT_SCHEDULED,
    DUALRUN_STATUS_SCHEDULING,
    DUALRUN_STATUS_DRYRUN,
    DUALRUN_STATUS_SUBMIT_ERROR,
)

# 数据校验状态（可空，空视作"未校验"）
CHECK_STATUS_PASSED = "校验通过"
CHECK_STATUS_FAILED = "校验不通过"
CHECK_STATUS_MINOR_GAP = "微小差距"
CHECK_STATUSES = (
    CHECK_STATUS_PASSED,
    CHECK_STATUS_FAILED,
    CHECK_STATUS_MINOR_GAP,
)

# 客户验收状态（可空，空视作"未验收"）
ACCEPTANCE_STATUS_PASSED = "通过"
ACCEPTANCE_STATUS_FAILED = "不通过"
ACCEPTANCE_STATUSES = (
    ACCEPTANCE_STATUS_PASSED,
    ACCEPTANCE_STATUS_FAILED,
)

# 数据校验结果（b05 校验结果导入后刷新到任务，见《数据校验-数据校验结果导入与刷新需求》）
CHECK_RESULT_PASSED = "通过"
CHECK_RESULT_FAILED = "不通过"
CHECK_RESULT_NONE = "无校验结果"
CHECK_RESULTS = (
    CHECK_RESULT_PASSED,
    CHECK_RESULT_FAILED,
    CHECK_RESULT_NONE,
)

# 归属环境默认取值
ENV_PROD = "生产"

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
    """任务台账（基础表）：所有项目共有的固定核心字段 + 5 维独立状态。"""

    __tablename__ = "b04_task"
    __table_args__ = (
        UniqueConstraint("scenario_id", "task_uri", name="uk_scenario_task_uri"),
        Index("idx_space_scenario", "space_id", "scenario_id"),
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="主键")
    space_id = Column(BigInteger, nullable=False, comment="所属空间")
    scenario_id = Column(BigInteger, nullable=False, comment="迁移场景ID")
    # ── 15 业务字段（D2 统一 project_name；见需求 §3.1） ──
    project_name = Column(
        String(128), nullable=False, default="default", comment="项目名称(统一自旧dw_project_space)"
    )
    workflow_name = Column(String(128), comment="工作流名称(与task_name不能全空)")
    task_name = Column(String(255), nullable=False, comment="任务名称")
    # B04-08 导入放宽：仅项目名称/任务名称必填，其余字段可留空落 NULL。
    # 注意：这些列不设默认值——SQLAlchemy 对显式 None 会触发 Python 侧默认值、
    # 对 server_default 会省略列让库默认值触发，两者都会导致无法落 NULL；
    # 任务创建仅经导入路径（显式传值/传空），无需默认值。
    env = Column(
        String(32), nullable=True, comment="归属环境:开发/测试/准生产/生产(可空,无默认值)"
    )
    business = Column(String(255), comment="归属业务")
    task_type = Column(String(64), comment="任务类型(码值:DI/HiveSQL/SparkSQL...)")
    migration_owner = Column(String(64), nullable=True, comment="迁移Owner(迁移负责人)(可空)")
    active_status = Column(
        String(32), nullable=True, comment="任务活跃状态:草稿/正常调度/下线/冻结(可空,无默认值)"
    )
    migration_status = Column(
        String(32), nullable=True, comment="迁移状态:未开始/迁移中/已完成(可空,无默认值)"
    )
    dualrun_status = Column(
        String(32), nullable=True, comment="双跑调度状态:未调度/调度中/空跑调度/提交报错(可空,无默认值)"
    )
    check_status = Column(String(32), comment="数据校验状态:校验通过/校验不通过/微小差距(空=未校验)")
    acceptance_status = Column(String(32), comment="客户验收状态:通过/不通过(空=未验收)")
    check_result = Column(
        String(32),
        nullable=True,
        comment="数据校验结果:通过/不通过/无校验结果(b05校验结果导入后按血缘输出表刷新;可空,无默认值)",
    )
    remark = Column(String(1024), comment="备注信息")
    task_uri = Column(
        String(512), nullable=False, comment="任务URI:project_name://task_name@workflow_name"
    )
    created_by = Column(String(64), comment="创建人")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    updated_by = Column(String(64), comment="更新人")
    updated_at = Column(
        DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间"
    )
    deleted_at = Column(DateTime, comment="逻辑删除时间")


class B04TaskExt(SpaceBase):
    """任务台账扩展表：与基础表一对一（task_id）。

    注意：`f_1…f_n` 扩展列**不**写为 ORM 列，由空间模板动态 ALTER 加列、
    并以动态 SQL 读写（列名白名单 `^f_[0-9]+$`，见需求 §9.4）。
    """

    __tablename__ = "b04_task_ext"
    __table_args__ = (
        Index("idx_ext_task", "task_id"),
    )

    task_id = Column(
        BigInteger,
        ForeignKey("b04_task.id", ondelete="CASCADE"),
        primary_key=True,
        comment="任务ID(一对一,外键级联)",
    )


class B04MigrationTemplate(SpaceBase):
    """空间级迁移模板：每空间一份，config_json 驱动字段选择/必填/排序/列表展示/导入。"""

    __tablename__ = "b04_migration_template"
    __table_args__ = (
        UniqueConstraint("space_id", name="uk_space_template"),
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="主键")
    space_id = Column(BigInteger, nullable=False, comment="所属空间(每空间一份)")
    name = Column(String(128), nullable=False, comment="模板名称")
    config_json = Column(JSON, nullable=False, comment="字段配置(有序):字段选择/必填/排序/列表展示/扩展字段定义")
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
    view_mode = Column(String(16), nullable=False, default="dynamic", comment="dynamic=动态引用;fixed=固化台账(锁定成员)")
    created_by = Column(String(64), comment="创建人")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    updated_by = Column(String(64), comment="更新人")
    updated_at = Column(
        DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间"
    )
    deleted_at = Column(DateTime, comment="逻辑删除时间")


class B04SavedViewMember(SpaceBase):
    """固化台账成员（仅固化模式写入，锁定命中任务ID）。"""

    __tablename__ = "b04_saved_view_member"
    __table_args__ = (
        UniqueConstraint("view_id", "task_id", name="uk_view_task"),
        Index("idx_view", "view_id"),
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="主键")
    space_id = Column(BigInteger, nullable=False, comment="所属空间")
    view_id = Column(BigInteger, nullable=False, comment="台账ID")
    task_id = Column(BigInteger, nullable=False, comment="任务ID（快照成员）")
    created_by = Column(String(64), comment="创建人")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    updated_by = Column(String(64), comment="更新人")
    updated_at = Column(
        DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间"
    )
    deleted_at = Column(DateTime, comment="逻辑删除时间")
