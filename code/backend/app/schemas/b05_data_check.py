"""b05 数据校验管理 Schema（Pydantic v2）。

依据《数据校验-数据校验结果导入与刷新需求》V1.0：
- 校验列表以 b03 库表清单为行，附加最新校验结果与近 7 天校验序列；
- 导入支持「默认模板」与「腾讯数据校验工具模板」两种列格式，落库时按前端选择的数据日期批量写入；
- 导入确认后按血缘输出正式表刷新 b04_task.check_result。
"""

from datetime import date
from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, field_validator

from app.models.b05_data_check import CHECK_RESULTS

# 近 7 天校验序列天数
RECENT_DAYS = 7


class CheckResultDay(BaseModel):
    """近 7 天中的一天：日期 + 当日校验结果（无数据为 None）。"""

    data_date: date
    result: Optional[str] = None
    src_volume: Optional[int] = None
    dst_volume: Optional[int] = None


class CheckOverviewOut(BaseModel):
    """数据校验列表行：库表清单 + 最新校验结果 + 近 7 天序列。"""

    model_config = ConfigDict(from_attributes=True)

    item_id: int
    scenario_id: int
    db_name: str
    table_name: str
    target_db_name: Optional[str] = None
    target_table_name: Optional[str] = None
    table_type: Optional[str] = None
    # 最新校验结果（无数据为 None，前端展示「无校验结果」）
    latest_result: Optional[str] = None
    latest_date: Optional[date] = None
    latest_src_volume: Optional[int] = None
    latest_dst_volume: Optional[int] = None
    # 近 7 天校验序列（按日期降序：索引 0 = 昨天 T-1，索引 6 = T-7；长度 RECENT_DAYS）
    recent_days: List[CheckResultDay] = []


class CheckResultImportResult(BaseModel):
    inserted: int = 0
    updated: int = 0
    skipped: int = 0
    errors: List[dict] = []
    # 本次导入刷新「任务迁移-基础表数据模型」数据校验结果的任务数（实际发生变更）
    refreshed_tasks: int = 0
    # 本次导入中不在（当前）迁移场景库表清单内的库表条数（D6：正常入库，仅提示）
    not_in_list: int = 0


class CheckRefreshResult(BaseModel):
    """全空间重跑任务级数据校验结果刷新结果（B05-04）。"""

    # 实际发生变更（含置为「无校验结果」）的任务数
    refreshed_tasks: int = 0


class CheckResultByTable(BaseModel):
    """单表单日校验结果（供血缘节点□渲染）。"""

    data_date: date
    result: Optional[str] = None
    src_volume: Optional[int] = None
    dst_volume: Optional[int] = None


class CheckResultsByTablesOut(BaseModel):
    """按表批量校验结果（key 为 `db.table`）。"""

    tables: Dict[str, List[CheckResultByTable]] = {}


class CheckResultRow(BaseModel):
    """解析后的单行校验结果（两种模板统一结构）。"""

    db_name: str
    table_name: str
    src_volume: Optional[int] = None
    dst_volume: Optional[int] = None
    result: str

    @field_validator("result")
    @classmethod
    def _v_result(cls, v):
        if v not in CHECK_RESULTS:
            raise ValueError(f"非法的校验结果: {v}")
        return v
