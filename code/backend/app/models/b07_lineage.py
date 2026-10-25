"""b07 血缘管理：数据血缘边（空间库表）。

表结构参考 data_lineage_hr.lineage；按项目规范补充 space_id 与审计/逻辑删除字段。
一条记录即一条「输入表 -> 输出表」的血缘边，数据由 input_table 流向 output_table。
"""

from datetime import datetime

from sqlalchemy import BigInteger, Column, DateTime, Index, String

from app.models.space_base import SpaceBase

# 表类型枚举（展示着色见 §6.4.2 设计令牌）
TABLE_TYPE_FORMAL = "正式表"
TABLE_TYPE_TEMP = "临时表"
TABLE_TYPES = (TABLE_TYPE_FORMAL, TABLE_TYPE_TEMP)


class B07Lineage(SpaceBase):
    """数据血缘边。"""

    __tablename__ = "b07_lineage"

    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="主键")
    space_id = Column(BigInteger, nullable=False, comment="所属空间")
    workflow_name = Column(String(255), comment="工作流名称")
    task_name = Column(String(255), comment="任务名")
    task_type = Column(String(64), comment="任务类型(SQL/PySpark/导出等)")
    project_name = Column(String(255), comment="所属项目")
    script_name = Column(String(512), comment="脚本路径/名称")
    input_table = Column(String(512), nullable=False, comment="输入表(源)")
    input_table_type = Column(String(32), comment="输入表类型: 正式表/临时表")
    output_table = Column(String(512), nullable=False, comment="输出表(目标)")
    output_table_type = Column(String(32), comment="输出表类型: 正式表/临时表")
    created_by = Column(String(64), comment="创建人")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    updated_by = Column(String(64), comment="更新人")
    updated_at = Column(
        DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间"
    )
    deleted_at = Column(DateTime, comment="逻辑删除时间")

    __table_args__ = (
        # 空间作用域复合索引：所有查询均以 space_id 起手，前缀 space_id 可避免全表扫描，
        # 并在按 表名称/工作流名称/任务名称 检索与 D5 任务详情关联时命中对应列。
        Index("idx_b07_space_workflow", "space_id", "workflow_name"),
        Index("idx_b07_space_task", "space_id", "task_name"),
        Index("idx_b07_space_proj_task", "space_id", "project_name", "task_name"),
        Index("idx_b07_space_input", "space_id", "input_table"),
        Index("idx_b07_space_output", "space_id", "output_table"),
    )
