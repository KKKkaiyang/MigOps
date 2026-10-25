"""b05 数据校验管理：数据校验结果（空间库表）。

表结构依据《数据校验-数据校验结果导入与刷新需求》V1.0：
- `b05_check_result`：按「数据日期 + 库名 + 表名」记录每次校验的源/目标端数据量与结果；
- 数据校验列表以 b03 库表清单为行，左连最新校验结果与近 7 天校验序列；
- 导入确认后按血缘输出正式表刷新 b04_task.check_result（数据校验结果）。
"""

from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    Column,
    Date,
    DateTime,
    Index,
    String,
    UniqueConstraint,
)

from app.models.space_base import SpaceBase

# 校验结果码值（与 b04_task.check_result 的通过/不通过一致；无数据视作无校验结果）
CHECK_RESULT_PASSED = "通过"
CHECK_RESULT_FAILED = "不通过"
CHECK_RESULTS = (CHECK_RESULT_PASSED, CHECK_RESULT_FAILED)

# 导入模板类型
CHECK_TEMPLATE_DEFAULT = "default"
CHECK_TEMPLATE_TENCENT = "tencent"
CHECK_TEMPLATES = (CHECK_TEMPLATE_DEFAULT, CHECK_TEMPLATE_TENCENT)


class B05CheckResult(SpaceBase):
    """数据校验结果：一张库表在一个数据日期下的校验记录。"""

    __tablename__ = "b05_check_result"
    __table_args__ = (
        UniqueConstraint("space_id", "data_date", "db_name", "table_name", name="uk_check_table_date"),
        Index("idx_check_table", "db_name", "table_name"),
        Index("idx_check_date", "data_date"),
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="主键")
    space_id = Column(BigInteger, nullable=False, comment="所属空间")
    data_date = Column(Date, nullable=False, comment="数据日期(校验结果所属日期)")
    db_name = Column(String(128), nullable=False, comment="库名")
    table_name = Column(String(128), nullable=False, comment="表名")
    src_volume = Column(BigInteger, comment="源端数据量(行数)")
    dst_volume = Column(BigInteger, comment="目标端数据量(行数)")
    result = Column(String(32), nullable=False, comment="校验结果:通过/不通过")
    created_by = Column(String(64), comment="创建人")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    updated_by = Column(String(64), comment="更新人")
    updated_at = Column(
        DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间"
    )
    deleted_at = Column(DateTime, comment="逻辑删除时间")
