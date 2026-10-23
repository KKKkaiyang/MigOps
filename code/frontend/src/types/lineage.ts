// 血缘管理（b07）类型定义，与后端 Pydantic Schema 对齐

/** 血缘边输出 */
export interface LineageOut {
  id: number
  workflow_name?: string | null
  task_name?: string | null
  task_type?: string | null
  project_name?: string | null
  script_name?: string | null
  input_table: string
  input_table_type?: string | null
  output_table: string
  output_table_type?: string | null
  created_by?: string | null
  created_at?: string | null
}

/** 解析预览的边（字段命名与解析器对齐） */
export interface LineageParsedEdge {
  source: string
  target: string
  sourceType?: string | null
  targetType?: string | null
}

/** 入库单条边（前端回传） */
export interface LineageEdgeIn {
  source: string
  target: string
  source_type?: string
  target_type?: string
}

/** 入库载荷 */
export interface LineageImportPayload {
  workflow: string
  task?: string
  task_type?: string
  project?: string
  script_name?: string
  mode?: 'add' | 'rebuild'
  default_db?: string
  edges?: LineageEdgeIn[]
  code?: string
  lang?: string
}

/** 工作流聚合 */
export interface LineageWorkflowOut {
  name: string
  count: number
  focus?: string | null
}

/** 工作流可选项（重建预填） */
export interface LineageWorkflowOptions {
  workflow: string
  tasks: string[]
  scripts: string[]
  task_types: string[]
  projects: string[]
}

/** 节点详情：按方向归并的任务记录 */
export interface LineageNodeTask {
  workflow?: string | null
  task?: string | null
  task_type?: string | null
  project?: string | null
  script?: string | null
  peer: string
}
