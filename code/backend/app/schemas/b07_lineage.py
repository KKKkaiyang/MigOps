"""b07 血缘管理：请求/响应模型。"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class LineageOut(BaseModel):
    """血缘边输出。"""

    id: int
    workflow_name: Optional[str] = None
    task_name: Optional[str] = None
    task_type: Optional[str] = None
    project_name: Optional[str] = None
    script_name: Optional[str] = None
    input_table: str
    input_table_type: Optional[str] = None
    output_table: str
    output_table_type: Optional[str] = None
    created_by: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class LineageEdgeIn(BaseModel):
    """单条血缘边（前端解析预览后回传或后端解析后入库）。"""

    source: str = Field(..., min_length=1, description="输入表")
    target: str = Field(..., min_length=1, description="输出表")
    source_type: Optional[str] = Field(None, description="输入表类型: 正式表/临时表")
    target_type: Optional[str] = Field(None, description="输出表类型: 正式表/临时表")


class LineageParseIn(BaseModel):
    """脚本解析输入。"""

    code: Optional[str] = Field(None, description="粘贴的脚本内容")
    lang: Optional[str] = Field(None, description="显式语言: sql/pyspark；为空则自动识别")


class LineageImportIn(BaseModel):
    """按工作流入库（新增 add / 重建 rebuild）。"""

    workflow: str = Field(..., min_length=1, description="工作流名称")
    task: Optional[str] = None
    task_type: Optional[str] = None
    project: Optional[str] = None
    script_name: Optional[str] = None
    mode: str = Field("add", description="add=新增; rebuild=重建覆盖")
    default_db: Optional[str] = Field(None, description="为无库名正式表补全的默认库名")
    # 二选一：直接传解析好的边，或传脚本由后端解析
    edges: Optional[List[LineageEdgeIn]] = None
    code: Optional[str] = None
    lang: Optional[str] = None

    @field_validator("mode")
    @classmethod
    def _v_mode(cls, v: str) -> str:
        if v not in ("add", "rebuild"):
            raise ValueError("mode 必须为 add 或 rebuild")
        return v

    @field_validator("lang")
    @classmethod
    def _v_lang(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in ("sql", "pyspark"):
            raise ValueError("lang 必须为 sql 或 pyspark")
        return v


class LineageWorkflowOptionsOut(BaseModel):
    """某工作流下可选的任务/脚本/任务类型/项目（重建预填用）。"""

    workflow: str
    tasks: List[str] = []
    scripts: List[str] = []
    task_types: List[str] = []
    projects: List[str] = []


class LineageWorkflowOut(BaseModel):
    """工作流聚合（列表展示）。"""

    name: str
    count: int = 0
    focus: Optional[str] = None


class TableRef(BaseModel):
    """血缘关联表引用（含表类型）。"""

    table: str
    type: Optional[str] = None


class LineageByTaskOut(BaseModel):
    """按任务（task_uri）聚合出的输入/输出表清单（去重）。"""

    input_tables: List[TableRef] = []
    output_tables: List[TableRef] = []
