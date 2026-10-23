// 血缘图构建与辅助函数（移植自 tools/hrwx_lineage/src/utils/graph.js，TypeScript 化）
//
// 边含义：source(输入表) -> target(输出表)，数据由 source 流向 target。
// 因此 target 是 source 的下游(down)，source 是 target 的上游(up)。
//
// 同一对 (source,target) 可能对应多条血缘记录（来自不同工作流/任务），
// 因此 up/down 的每个"邻接表项"保存的是记录数组（而非单条）。

/** 单条血缘记录（节点邻接携带的元信息） */
export interface LineageRec {
  type: string
  script: string
  workflow: string
  task: string
  taskType: string
  project: string
}

/** 构图输入边（对应后端 LineageOut / LineageParsedEdge） */
export interface BuildEdge {
  source: string
  target: string
  sourceType?: string | null
  targetType?: string | null
  workflow?: string | null
  task?: string | null
  taskType?: string | null
  project?: string | null
  script?: string | null
}

/** 构建后的血缘图结构 */
export interface LineageGraphData {
  up: Map<string, Map<string, LineageRec[]>>
  down: Map<string, Map<string, LineageRec[]>>
  // 临时表专用邻接表：table -> wsKey -> neighbor -> 记录数组
  // wsKey = workflow + '\u0001' + script，临时表只在同 workflow+script 下关联上下游
  tempUp: Map<string, Map<string, Map<string, LineageRec[]>>>
  tempDown: Map<string, Map<string, Map<string, LineageRec[]>>>
  typeMap: Map<string, string>
  tables: Set<string>
  projectMap: Map<string, Set<string>>
  taskTypeMap: Map<string, Set<string>>
}

/** 临时表上下文分隔符 */
const WS_SEP = ''

export function buildGraph(edges: BuildEdge[]): LineageGraphData {
  const up = new Map<string, Map<string, LineageRec[]>>()
  const down = new Map<string, Map<string, LineageRec[]>>()
  const tempUp = new Map<string, Map<string, Map<string, LineageRec[]>>>()
  const tempDown = new Map<string, Map<string, Map<string, LineageRec[]>>>()
  const typeMap = new Map<string, string>()
  const tables = new Set<string>()
  const projectMap = new Map<string, Set<string>>()
  const taskTypeMap = new Map<string, Set<string>>()

  const setType = (t: string, ty?: string | null) => {
    if (!t) return
    // 临时表优先（更具体）；若已记录正式表，遇到临时表则覆盖
    if (!typeMap.has(t) || ty === '临时表') typeMap.set(t, ty || typeMap.get(t) || '正式表')
  }

  const addPair = (map: Map<string, Map<string, LineageRec[]>>, from: string, to: string, rec: LineageRec) => {
    if (!map.has(from)) map.set(from, new Map())
    const m = map.get(from)!
    if (!m.has(to)) m.set(to, [])
    m.get(to)!.push(rec)
  }

  const addTempPair = (
    map: Map<string, Map<string, Map<string, LineageRec[]>>>,
    from: string,
    wsKey: string,
    to: string,
    rec: LineageRec
  ) => {
    if (!map.has(from)) map.set(from, new Map())
    const wsMap = map.get(from)!
    if (!wsMap.has(wsKey)) wsMap.set(wsKey, new Map())
    const nbrMap = wsMap.get(wsKey)!
    if (!nbrMap.has(to)) nbrMap.set(to, [])
    nbrMap.get(to)!.push(rec)
  }

  const makeRec = (type: string, e: BuildEdge): LineageRec => ({
    type: type || '',
    script: e.script || '',
    workflow: e.workflow || '',
    task: e.task || '',
    taskType: e.taskType || '',
    project: e.project || '',
  })

  for (const e of edges) {
    const s = e.source
    const t = e.target
    if (s) {
      tables.add(s)
      setType(s, e.sourceType)
      if (e.project) {
        if (!projectMap.has(s)) projectMap.set(s, new Set())
        projectMap.get(s)!.add(e.project)
      }
      if (e.taskType) {
        if (!taskTypeMap.has(s)) taskTypeMap.set(s, new Set())
        taskTypeMap.get(s)!.add(e.taskType)
      }
    }
    if (t) {
      tables.add(t)
      setType(t, e.targetType)
      if (e.project) {
        if (!projectMap.has(t)) projectMap.set(t, new Set())
        projectMap.get(t)!.add(e.project)
      }
      if (e.taskType) {
        if (!taskTypeMap.has(t)) taskTypeMap.set(t, new Set())
        taskTypeMap.get(t)!.add(e.taskType)
      }
    }
    if (!s || !t) continue

    const sIsTemp = typeMap.get(s) === '临时表'
    const tIsTemp = typeMap.get(t) === '临时表'
    const wsKey = (e.workflow || '') + WS_SEP + (e.script || '')

    // down: source -> target
    if (sIsTemp) addTempPair(tempDown, s, wsKey, t, makeRec(e.targetType || '', e))
    else addPair(down, s, t, makeRec(e.targetType || '', e))
    // up: target -> source
    if (tIsTemp) addTempPair(tempUp, t, wsKey, s, makeRec(e.sourceType || '', e))
    else addPair(up, t, s, makeRec(e.sourceType || '', e))
  }

  return { up, down, tempUp, tempDown, typeMap, tables, projectMap, taskTypeMap }
}

/** 取表名最后一段（去掉库名/schema）用于搜索建议展示 */
export function shortName(full?: string | null): string {
  if (!full) return ''
  const i = full.lastIndexOf('.')
  return i >= 0 ? full.slice(i + 1) : full
}

/** 节点展示名：保留「库名.表名」，去掉中间的 schema 段 */
export function displayName(full?: string | null): string {
  if (!full) return ''
  const parts = full.split('.')
  if (parts.length <= 2) return full
  return parts[0] + '.' + parts[parts.length - 1]
}

/** 将完整表名拆成库名 / 表名两行（用于节点换行显示） */
export function splitName(full?: string | null): { db: string; tbl: string } {
  const parts = (full || '').split('.')
  if (parts.length <= 1) return { db: '', tbl: full || '' }
  if (parts.length === 2) return { db: parts[0], tbl: parts[1] }
  return { db: parts[1], tbl: parts[parts.length - 1] }
}

let _ctx: CanvasRenderingContext2D | null | undefined = undefined
function measureCtx(): CanvasRenderingContext2D | null {
  if (_ctx !== undefined) return _ctx
  if (typeof document === 'undefined') {
    _ctx = null
    return null
  }
  try {
    _ctx = document.createElement('canvas').getContext('2d')
  } catch {
    _ctx = null
  }
  return _ctx
}

function textWidth(text: string, fontSize: number, fontFamily?: string): number {
  const c = measureCtx()
  if (c) {
    c.font = `${fontSize}px ${fontFamily || 'Arial, sans-serif'}`
    return c.measureText(text).width
  }
  let w = 0
  for (const ch of text) w += ch.charCodeAt(0) > 255 ? fontSize : fontSize * 0.56
  return w
}

/** 按宽度截断并追加省略号（展示不下则省略，hover 显示完整） */
export function fitLine(text: string, fontSize: number, maxWidth: number, fontFamily?: string): string {
  if (!text) return ''
  if (textWidth(text, fontSize, fontFamily) <= maxWidth) return text
  let s = text
  while (s.length > 1 && textWidth(s + '…', fontSize, fontFamily) > maxWidth) {
    s = s.slice(0, -1)
  }
  return s + '…'
}
