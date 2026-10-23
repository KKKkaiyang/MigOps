<template>
  <div class="graph-root" ref="root" @click="closeMenu">
    <!-- 缩放/适应 控制 -->
    <div class="zoom-controls">
      <button @click="zoomBy(0.2)" title="放大">+</button>
      <button @click="zoomBy(-0.2)" title="缩小">−</button>
      <button @click="fitView" title="适应屏幕">⤢</button>
      <button @click="resetView" title="重置视图">⟳</button>
      <button @click="exportPng" title="导出 PNG">⤓</button>
    </div>

    <!-- 图例（D6：仅颜色图例，不含任何开关） -->
    <div class="legend">
      <div class="legend-item"><span class="dot formal"></span>正式表</div>
      <div class="legend-item"><span class="dot temp"></span>临时表</div>
      <div class="legend-item"><span class="dot focus"></span>当前表</div>
      <div class="legend-hint">+/- 展开一度 · 右键节点可一直下钻到底</div>
    </div>

    <svg
      ref="svg"
      class="graph-svg"
      :width="svgW"
      :height="svgH"
      @wheel.prevent="onWheel"
      @mousedown="onDown"
      @mousemove="onMove"
      @mouseup="onUp"
      @mouseleave="onUp"
    >
      <g
        class="graph-layer"
        :class="{ animating }"
        :transform="`translate(${tx},${ty}) scale(${scale})`"
      >
        <!-- 连线 -->
        <g
          v-for="(l, i) in links"
          :key="'l' + i"
          class="edge-g"
          :class="{ dim: highlightActive && !l.hot, hot: l.hot, hover: hoverEdgeIdx === i }"
        >
          <path
            :d="l.d"
            class="edge-hit"
            @mouseenter="hoverEdgeIdx = i"
            @mouseleave="hoverEdgeIdx = -1"
            @contextmenu.prevent="openEdgeMenu(l, $event)"
          ></path>
          <path
            :d="l.d"
            class="edge"
            :class="l.cls"
            :marker-end="l.cls === 'up' ? 'url(#arrowUp)' : 'url(#arrowDown)'"
          />
        </g>

        <!-- 节点（每个路径实例唯一，可重复展示同一张表） -->
        <g
          v-for="n in nodes"
          :key="n.key"
          class="node"
          :class="{ focus: n.focus }"
          @contextmenu.prevent="openMenu(n, $event)"
        >
          <!-- 上游展开按钮（仅可达到方向为 up/both 的节点显示） -->
          <g
            v-if="n.canUp && n.upCount > 0"
            class="toggle up"
            :class="{ on: n.upOn }"
            :transform="`translate(${n.x - NODE_W / 2 - 16},${n.y})`"
            @click.stop="toggleInstance(n.key, 'up')"
          >
            <circle :r="10"></circle>
            <text class="toggle-ico" text-anchor="middle" dy="3.5">{{ n.upOn ? '−' : '+' }}</text>
            <text class="toggle-badge" text-anchor="middle" :x="11" :y="-8">{{ n.upCount }}</text>
            <title>{{ n.upOn ? '收起上游一度血缘' : '展开上游一度血缘' }}</title>
          </g>

          <!-- 下游展开按钮（仅可达到方向为 down/both 的节点显示） -->
          <g
            v-if="n.canDown && n.downCount > 0"
            class="toggle down"
            :class="{ on: n.downOn }"
            :transform="`translate(${n.x + NODE_W / 2 + 16},${n.y})`"
            @click.stop="toggleInstance(n.key, 'down')"
          >
            <circle :r="10"></circle>
            <text class="toggle-ico" text-anchor="middle" dy="3.5">{{ n.downOn ? '−' : '+' }}</text>
            <text class="toggle-badge" text-anchor="middle" :x="11" :y="-8">{{ n.downCount }}</text>
            <title>{{ n.downOn ? '收起下游一度血缘' : '展开下游一度血缘' }}</title>
          </g>

          <!-- 节点主体 -->
          <g
            :transform="`translate(${n.x - NODE_W / 2},${n.y - NODE_H / 2})`"
            @mouseenter="onNodeEnter(n)"
            @mouseleave="onNodeLeave"
          >
            <rect
              :width="NODE_W"
              :height="NODE_H"
              rx="8"
              class="node-rect"
              :class="[n.temp ? 'temp' : 'formal', { dim: highlightActive && !n.hot, hot: n.hot }]"
            ></rect>

            <text
              v-if="n.hasDb"
              class="node-db"
              :x="NODE_W / 2"
              :y="n.dbY"
              text-anchor="middle"
            >{{ n.dbLine }}</text>
            <text
              class="node-tbl"
              :x="NODE_W / 2"
              :y="n.tblY"
              text-anchor="middle"
            >{{ n.tblLine }}</text>
            <title>{{ n.tooltip }}</title>

            <!-- 复制完整名 小图标（右上角） -->
            <g
              class="copy-ico"
              :transform="`translate(${NODE_W - 14},14)`"
              @click.stop="copyName(n.table, $event)"
            >
              <circle :r="11" :class="{ done: copied === n.table }"></circle>
              <text text-anchor="middle" dy="3.5" class="copy-glyph">⧉</text>
            </g>
          </g>
        </g>
      </g>

      <defs>
        <marker id="arrowDown" markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto" markerUnits="userSpaceOnUse">
          <path d="M0,0 L8,3 L0,6 Z" fill="#9aa7b5"></path>
        </marker>
        <marker id="arrowUp" markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto" markerUnits="userSpaceOnUse">
          <path d="M0,0 L8,3 L0,6 Z" fill="#c2a36b"></path>
        </marker>
      </defs>
    </svg>

    <!-- 右键菜单：按单表一直下钻 / 收起 / 查看详情 -->
    <div
      v-if="menu"
      class="ctx-menu"
      :style="{ left: menu.x + 'px', top: menu.y + 'px' }"
      @click.stop
    >
      <div class="ctx-title">{{ displayName(menu.table) }}</div>
      <button @click="menuDetail">查看详情</button>
      <template v-if="menu.canUp">
        <button @click="menuAction('up', true)">展开上游全部</button>
        <button @click="menuAction('up', false)">收起上游</button>
      </template>
      <template v-if="menu.canDown">
        <button @click="menuAction('down', true)">展开下游全部</button>
        <button @click="menuAction('down', false)">收起下游</button>
      </template>
    </div>

    <!-- 表详情面板（写入/读取任务以选项卡切换；按工作流分组，可展开查看任务） -->
    <div v-if="detail" class="detail-panel" @click.stop>
      <div class="detail-head">
        <span class="detail-title">{{ displayName(detail.table) }}</span>
        <button class="detail-close" title="关闭" @click="detail = null">×</button>
      </div>
      <div class="detail-full" :title="detail.table">{{ detail.table }}</div>

      <div class="detail-tabs">
        <div class="detail-tab" :class="{ active: detailTab === 'write' }" @click="detailTab = 'write'">
          写入任务{{ wfSummary(detail.write).records ? '（' + wfSummary(detail.write).records + '）' : '' }}
        </div>
        <div class="detail-tab" :class="{ active: detailTab === 'read' }" @click="detailTab = 'read'">
          读取任务{{ wfSummary(detail.read).records ? '（' + wfSummary(detail.read).records + '）' : '' }}
        </div>
      </div>

      <div v-show="detailTab === 'write'">
        <div class="detail-sec" v-if="wfSummary(detail.write).groups">
          <div class="detail-sec-title">写入任务（{{ wfSummary(detail.write).groups }} 个工作流 / {{ wfSummary(detail.write).records }} 条）</div>
          <div v-for="g in visibleGroups(detail.write)" :key="'w_' + g.workflow + '' + g.script" class="wf-group">
            <div class="wf-name wf-collapsible" @click="toggleWf(detail, g.workflow + '' + g.script)">
              <span class="wf-caret">{{ isWfOpen(detail, g.workflow + '' + g.script) ? '▾' : '▸' }}</span>
              <span class="wf-title" @click.stop>{{ g.workflow }}<template v-if="g.script"> · {{ scriptBase(g.script) }}</template></span>
              <span class="wf-copy" title="复制工作流名称" @click.stop="copyText(g.workflow)">⧉</span>
            </div>
            <ul v-show="isWfOpen(detail, g.workflow + '' + g.script)">
              <li v-for="(it, i) in g.items" :key="i" class="task-item">
                <div class="ti-detail">
                  <div><span class="ti-label">任务</span>{{ it.task || '（未知任务）' }}</div>
                  <div><span class="ti-label">项目</span>{{ it.project || '（未知）' }}</div>
                  <div><span class="ti-label">任务类型</span>{{ it.taskType || '（未知）' }}</div>
                  <div><span class="ti-label">脚本</span><span :title="it.script" @click.stop="copyText(it.script || '')" class="ti-copy">{{ scriptBase(it.script) || '（未知脚本）' }}</span></div>
                  <div><span class="ti-label">表名</span>{{ it.peers.join('、') || '（未知表）' }}</div>
                </div>
              </li>
            </ul>
          </div>
        </div>
        <div class="detail-empty" v-else>暂无写入任务</div>
      </div>

      <div v-show="detailTab === 'read'">
        <div class="detail-sec" v-if="wfSummary(detail.read).groups">
          <div class="detail-sec-title">读取任务（{{ wfSummary(detail.read).groups }} 个工作流 / {{ wfSummary(detail.read).records }} 条）</div>
          <div v-for="g in visibleGroups(detail.read)" :key="'r_' + g.workflow + '' + g.script" class="wf-group">
            <div class="wf-name wf-collapsible" @click="toggleWf(detail, g.workflow + '' + g.script)">
              <span class="wf-caret">{{ isWfOpen(detail, g.workflow + '' + g.script) ? '▾' : '▸' }}</span>
              <span class="wf-title" @click.stop>{{ g.workflow }}<template v-if="g.script"> · {{ scriptBase(g.script) }}</template></span>
              <span class="wf-copy" title="复制工作流名称" @click.stop="copyText(g.workflow)">⧉</span>
            </div>
            <ul v-show="isWfOpen(detail, g.workflow + '' + g.script)">
              <li v-for="(it, i) in g.items" :key="i" class="task-item">
                <div class="ti-detail">
                  <div><span class="ti-label">任务</span>{{ it.task || '（未知任务）' }}</div>
                  <div><span class="ti-label">项目</span>{{ it.project || '（未知）' }}</div>
                  <div><span class="ti-label">任务类型</span>{{ it.taskType || '（未知）' }}</div>
                  <div><span class="ti-label">脚本</span><span :title="it.script" @click.stop="copyText(it.script || '')" class="ti-copy">{{ scriptBase(it.script) || '（未知脚本）' }}</span></div>
                  <div><span class="ti-label">表名</span>{{ it.peers.join('、') || '（未知表）' }}</div>
                </div>
              </li>
            </ul>
          </div>
        </div>
        <div class="detail-empty" v-else>暂无读取任务</div>
      </div>
    </div>

    <!-- 血缘线详情浮层（右键连线弹出，显示读写关系与来源任务） -->
    <div
      v-if="edgeDetail"
      class="detail-panel edge-detail"
      :style="{ position: 'fixed', left: edgeDetail.x + 'px', top: edgeDetail.y + 'px' }"
      @click.stop
    >
      <div class="detail-head">
        <span class="detail-title">血缘线详情</span>
        <button class="detail-close" title="关闭" @click="edgeDetail = null">×</button>
      </div>

      <div class="detail-sec">
        <div class="detail-sec-title">读写关系（{{ edgeDetail.dir === 'down' ? '下游写入' : '上游写入' }}）</div>
        <div class="edge-rel">
          <span class="er-label read">读取</span>
          <span class="er-name">{{ displayName(edgeDetail.from) }}</span>
          <span class="er-arrow">→</span>
          <span class="er-label write">写入</span>
          <span class="er-name">{{ displayName(edgeDetail.to) }}</span>
        </div>
        <div class="edge-full" :title="edgeDetail.from">{{ edgeDetail.from }}</div>
        <div class="edge-full" :title="edgeDetail.to">{{ edgeDetail.to }}</div>
      </div>

      <div class="detail-sec">
        <div class="detail-sec-title">来源任务（{{ wfSummary(edgeDetail.groups).groups }} 个工作流 / {{ wfSummary(edgeDetail.groups).records }} 条）</div>
        <div v-for="g in visibleGroups(edgeDetail.groups)" :key="g.workflow" class="wf-group">
          <div class="wf-name wf-collapsible" @click="toggleWf(edgeDetail, g.workflow)">
            <span class="wf-caret">{{ isWfOpen(edgeDetail, g.workflow) ? '▾' : '▸' }}</span>
            <span class="wf-title" @click.stop>{{ g.workflow }}</span>
            <span class="wf-copy" title="复制工作流名称" @click.stop="copyText(g.workflow)">⧉</span>
          </div>
          <ul v-show="isWfOpen(edgeDetail, g.workflow)">
            <li v-for="(it, i) in g.items" :key="i" class="task-item">
              <div class="ti-detail">
                <div><span class="ti-label">任务</span>{{ it.task || '（未知任务）' }}</div>
                <div><span class="ti-label">项目</span>{{ it.project || '（未知）' }}</div>
                <div><span class="ti-label">任务类型</span>{{ it.taskType || '（未知）' }}</div>
                <div><span class="ti-label">脚本</span><span :title="it.script" @click.stop="copyText(it.script || '')" class="ti-copy">{{ scriptBase(it.script) || '（未知脚本）' }}</span></div>
                <div v-if="it.peers.length"><span class="ti-label">表名</span>{{ it.peers.join('、') }}</div>
              </div>
            </li>
          </ul>
        </div>
      </div>
    </div>

    <div v-if="!nodes.length" class="empty-hint">
      请输入表名进行血缘检索
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import {
  type LineageGraphData,
  type LineageRec,
  displayName,
  splitName,
  fitLine,
} from '@/utils/lineage-graph'

const NODE_W = 184
const NODE_H = 50
const LEVEL_W = 280
const NODE_V = 64
const MARGIN = 80
const LBL_FONT = 10
const DB_FONT = 8
const MAXW = NODE_W - 18
const WS_SEP = ''

const props = defineProps<{
  focusTable: string
  graph: LineageGraphData
}>()

interface LNode {
  key: string
  table: string
  x: number
  y: number
  temp: boolean
  focus: boolean
  upCount: number
  downCount: number
  upOn: boolean
  downOn: boolean
  canUp: boolean
  canDown: boolean
  hot: boolean
  dbLine: string
  tblLine: string
  hasDb: boolean
  dbY: number
  tblY: number
  tooltip: string
}
interface LLink {
  d: string
  cls: 'up' | 'down'
  edges: LineageRec[]
  from: string
  to: string
  mx: number
  my: number
  hot: boolean
}
interface Inst {
  key: string
  table: string
  depth: number
  parentKey: string | null
  temp: boolean
  focus: boolean
  inDir: 'up' | 'down' | 'both'
  upCount: number
  downCount: number
  upOn: boolean
  downOn: boolean
}
interface WfGroupItem {
  task: string
  script: string
  peers: string[]
  taskType: string
  project: string
}
interface WfGroup {
  workflow: string
  script: string
  items: WfGroupItem[]
}
interface DetailData {
  table: string
  write: WfGroup[]
  read: WfGroup[]
  writeCount: number
  readCount: number
  wfOpen: Record<string, boolean>
}
interface EdgeDetailData {
  from: string
  to: string
  dir: 'up' | 'down'
  groups: WfGroup[]
  count: number
  wfOpen: Record<string, boolean>
  x: number
  y: number
}
interface MenuData {
  x: number
  y: number
  key: string
  table: string
  focus: boolean
  canUp: boolean
  canDown: boolean
}
interface PendingCenter {
  type: 'expand' | 'collapse'
  key?: string
  dir?: 'up' | 'down'
}

const root = ref<HTMLElement | null>(null)
const svg = ref<SVGSVGElement | null>(null)

const scale = ref(1)
const tx = ref(0)
const ty = ref(0)
const animating = ref(false)
const hoverEdgeIdx = ref(-1)
const dragging = ref(false)
const lastX = ref(0)
const lastY = ref(0)
const svgW = ref(1000)
const svgH = ref(600)
const copied = ref<string | null>(null)
const highlightActive = ref(false)
const hotNodes = ref(new Set<string>())
const openUpSet = ref(new Set<string>())
const openDownSet = ref(new Set<string>())
const menu = ref<MenuData | null>(null)
const detail = ref<DetailData | null>(null)
const detailTab = ref<'write' | 'read'>('write')
const edgeDetail = ref<EdgeDetailData | null>(null)
const pendingCenter = ref<PendingCenter | null>(null)

let animTimer: number | undefined

const isTemp = (t: string) => props.graph.typeMap.get(t) === '临时表'

const model = computed<{ nodes: LNode[]; links: LLink[]; bounds: { w: number; h: number; focusX: number; focusY: number } | null }>(() => {
  const { up, down, tempUp, tempDown, typeMap } = props.graph
  const focus = props.focusTable
  if (!focus) return { nodes: [], links: [], bounds: null }

  const openUp = openUpSet.value
  const openDown = openDownSet.value

  const instances = new Map<string, Inst>()
  const childrenOf = new Map<string, { childKey: string; dir: 'up' | 'down'; edges: LineageRec[]; table: string }[]>()

  const tempNeighborCount = (map: Map<string, Map<string, Map<string, LineageRec[]>>>, table: string) => {
    const wsMap = map.get(table)
    if (!wsMap) return 0
    const all = new Set<string>()
    for (const nbrMap of wsMap.values()) for (const nb of nbrMap.keys()) all.add(nb)
    return all.size
  }

  const makeInst = (key: string, table: string, depth: number, parentKey: string | null, inDir: 'up' | 'down' | 'both'): Inst => {
    const temp = typeMap.get(table) === '临时表'
    const inst: Inst = {
      key,
      table,
      depth,
      parentKey,
      temp,
      focus: table === focus,
      inDir,
      upCount: temp ? tempNeighborCount(tempUp, table) : up.get(table)?.size || 0,
      downCount: temp ? tempNeighborCount(tempDown, table) : down.get(table)?.size || 0,
      upOn: openUp.has(key),
      downOn: openDown.has(key),
    }
    instances.set(key, inst)
    return inst
  }

  // 获取当前表在指定方向上的邻居列表：[neighborTable, rec[]]
  const getNeighbors = (table: string, dir: 'up' | 'down', wsCtx: { workflow: string; script: string } | null): [string, LineageRec[]][] => {
    if (isTemp(table)) {
      const wsMap = (dir === 'up' ? tempUp : tempDown).get(table)
      if (!wsMap) return []
      const wsKey = wsCtx ? (wsCtx.workflow || '') + WS_SEP + (wsCtx.script || '') : null
      if (wsKey !== null) {
        const nbrMap = wsMap.get(wsKey)
        if (!nbrMap) return []
        return [...nbrMap.entries()]
      }
      const merged = new Map<string, LineageRec[]>()
      for (const nbrMap of wsMap.values()) {
        for (const [nb, recs] of nbrMap) {
          if (!merged.has(nb)) merged.set(nb, [])
          merged.get(nb)!.push(...recs)
        }
      }
      return [...merged.entries()]
    }
    const adj = dir === 'up' ? up.get(table) : down.get(table)
    if (!adj) return []
    return [...adj.entries()]
  }

  const expand = (
    key: string,
    table: string,
    depth: number,
    parentKey: string | null,
    inDir: 'up' | 'down' | 'both',
    pathSet: Set<string>,
    wsContext: { workflow: string; script: string } | null
  ) => {
    makeInst(key, table, depth, parentKey, inDir)
    if (openUp.has(key)) {
      for (const [nb, info] of getNeighbors(table, 'up', wsContext)) {
        if (pathSet.has(nb)) continue
        const childKey = `${key}::up::${nb}`
        const childWs = isTemp(nb)
          ? wsContext || (info[0] && { workflow: info[0].workflow, script: info[0].script }) || null
          : null
        if (!childrenOf.has(key)) childrenOf.set(key, [])
        childrenOf.get(key)!.push({ childKey, dir: 'up', edges: info, table: nb })
        const np = new Set(pathSet)
        np.add(nb)
        expand(childKey, nb, depth - 1, key, 'up', np, childWs)
      }
    }
    if (openDown.has(key)) {
      for (const [nb, info] of getNeighbors(table, 'down', wsContext)) {
        if (pathSet.has(nb)) continue
        const childKey = `${key}::down::${nb}`
        const childWs = isTemp(nb)
          ? wsContext || (info[0] && { workflow: info[0].workflow, script: info[0].script }) || null
          : null
        if (!childrenOf.has(key)) childrenOf.set(key, [])
        childrenOf.get(key)!.push({ childKey, dir: 'down', edges: info, table: nb })
        const np = new Set(pathSet)
        np.add(nb)
        expand(childKey, nb, depth + 1, key, 'down', np, childWs)
      }
    }
  }

  // focus 节点展开：临时表入口时 wsContext 为空，getNeighbors 会合并所有 wsKey
  expand(focus, focus, 0, null, 'both', new Set([focus]), null)

  // 树形 y 布局（叶子顺序递增）
  const ypos: Record<string, number> = {}
  let leaf = 0
  const layout = (key: string): number => {
    const kids = childrenOf.get(key) || []
    if (!kids.length) {
      ypos[key] = leaf * NODE_V
      leaf++
      return ypos[key]
    }
    const ys = kids.map((c) => layout(c.childKey))
    ypos[key] = (Math.min(...ys) + Math.max(...ys)) / 2
    return ypos[key]
  }
  layout(focus)

  let minDepth = 0
  let maxDepth = 0
  let minY = Infinity
  let maxY = -Infinity
  for (const [, inst] of instances) {
    minDepth = Math.min(minDepth, inst.depth)
    maxDepth = Math.max(maxDepth, inst.depth)
    minY = Math.min(minY, ypos[inst.key])
    maxY = Math.max(maxY, ypos[inst.key])
  }
  const shiftX = -minDepth * LEVEL_W + MARGIN
  const shiftY = -minY + MARGIN

  const pos = new Map<string, { x: number; y: number }>()
  const nodes: LNode[] = []
  for (const [key, inst] of instances) {
    const x = inst.depth * LEVEL_W + shiftX
    const y = ypos[key] + shiftY
    pos.set(key, { x, y })

    const { db, tbl } = splitName(inst.table)
    let dbLine = ''
    let tblLine = ''
    let hasDb = false
    let dbY = 0
    let tblY = NODE_H / 2 + 4
    if (db) {
      dbLine = fitLine(db, DB_FONT, MAXW)
      hasDb = true
    }
    tblLine = fitLine(tbl, LBL_FONT, MAXW)
    if (hasDb) {
      dbY = 20
      tblY = 33
    } else {
      dbY = 0
      tblY = 30
    }

    const canUp = inst.focus || inst.inDir === 'up' || inst.inDir === 'both'
    const canDown = inst.focus || inst.inDir === 'down' || inst.inDir === 'both'

    nodes.push({
      key,
      table: inst.table,
      x,
      y,
      temp: inst.temp,
      focus: inst.focus,
      upCount: inst.upCount,
      downCount: inst.downCount,
      upOn: inst.upOn,
      downOn: inst.downOn,
      canUp,
      canDown,
      hot: hotNodes.value.has(key),
      dbLine,
      tblLine,
      hasDb,
      dbY,
      tblY,
      tooltip: inst.table,
    })
  }

  // 连线：方向始终指向数据流向（源 -> 目标）
  const hot = hotNodes.value
  const links: LLink[] = []
  for (const [pk, kids] of childrenOf) {
    const p = pos.get(pk)!
    const pInst = instances.get(pk)!
    for (const c of kids) {
      const ch = pos.get(c.childKey)!
      const chInst = instances.get(c.childKey)!
      let x1: number, y1: number, x2: number, y2: number
      if (c.dir === 'down') {
        x1 = p.x + NODE_W / 2
        y1 = p.y
        x2 = ch.x - NODE_W / 2
        y2 = ch.y
      } else {
        x1 = ch.x + NODE_W / 2
        y1 = ch.y
        x2 = p.x - NODE_W / 2
        y2 = p.y
      }
      const mx = (x1 + x2) / 2
      const fromTable = c.dir === 'down' ? pInst.table : chInst.table
      const toTable = c.dir === 'down' ? chInst.table : pInst.table
      links.push({
        d: `M${x1},${y1} L${mx},${y1} L${mx},${y2} L${x2},${y2}`,
        cls: c.dir,
        edges: c.edges,
        from: fromTable,
        to: toTable,
        mx,
        my: (y1 + y2) / 2,
        hot: hot.has(pk) && hot.has(c.childKey),
      })
    }
  }

  const bounds = {
    w: (maxDepth - minDepth) * LEVEL_W + NODE_W + MARGIN * 2,
    h: maxY - minY + NODE_H + MARGIN * 2,
    focusX: 0 * LEVEL_W + shiftX,
    focusY: ypos[focus] + shiftY,
  }
  return { nodes, links, bounds }
})

const nodes = computed(() => model.value.nodes)
const links = computed(() => model.value.links)

watch(
  () => props.focusTable,
  (v) => {
    openUpSet.value = new Set(v ? [v] : [])
    openDownSet.value = new Set()
    menu.value = null
    detail.value = null
    edgeDetail.value = null
    nextTick(fitView)
  }
)
watch(openUpSet, () => {
  nextTick(() => {
    if (pendingCenter.value && pendingCenter.value.type === 'expand' && pendingCenter.value.dir === 'up') centerOnExpansion(pendingCenter.value)
    else if (pendingCenter.value && pendingCenter.value.type === 'collapse') centerOnAll()
    else fitView()
    pendingCenter.value = null
  })
})
watch(openDownSet, () => {
  nextTick(() => {
    if (pendingCenter.value && pendingCenter.value.type === 'expand' && pendingCenter.value.dir === 'down') centerOnExpansion(pendingCenter.value)
    else if (pendingCenter.value && pendingCenter.value.type === 'collapse') centerOnAll()
    else fitView()
    pendingCenter.value = null
  })
})

onMounted(() => {
  resize()
  window.addEventListener('resize', resize)
  if (props.focusTable) nextTick(fitView)
})
onBeforeUnmount(() => {
  window.removeEventListener('resize', resize)
})

function resize() {
  const el = root.value
  if (!el) return
  svgW.value = el.clientWidth
  svgH.value = el.clientHeight
}

function scriptBase(p?: string | null): string {
  if (!p) return ''
  const i = Math.max(p.lastIndexOf('/'), p.lastIndexOf('\\'))
  return i >= 0 ? p.slice(i + 1) : p
}

function computeHot(table: string) {
  const { up, down, tempUp, tempDown } = props.graph
  const set = new Set<string>()
  for (const inst of model.value.nodes) {
    if (inst.table === table) set.add(inst.key)
  }
  const addNeighbors = (t: string) => {
    if (isTemp(t)) {
      const tu = tempUp.get(t)
      if (tu) for (const nbrMap of tu.values()) for (const k of nbrMap.keys()) for (const inst of model.value.nodes) if (inst.table === k) set.add(inst.key)
      const td = tempDown.get(t)
      if (td) for (const nbrMap of td.values()) for (const k of nbrMap.keys()) for (const inst of model.value.nodes) if (inst.table === k) set.add(inst.key)
    } else {
      const u = up.get(t)
      if (u) for (const k of u.keys()) for (const inst of model.value.nodes) if (inst.table === k) set.add(inst.key)
      const d = down.get(t)
      if (d) for (const k of d.keys()) for (const inst of model.value.nodes) if (inst.table === k) set.add(inst.key)
    }
  }
  addNeighbors(table)
  hotNodes.value = set
  highlightActive.value = true
}
function onNodeEnter(n: LNode) {
  computeHot(n.table)
}
function onNodeLeave() {
  highlightActive.value = false
  hotNodes.value = new Set()
}

// 单节点一度展开/收起
function toggleInstance(key: string, dir: 'up' | 'down') {
  const set = dir === 'up' ? openUpSet : openDownSet
  const next = new Set(set.value)
  const opening = !next.has(key)
  if (opening) next.add(key)
  else next.delete(key)
  pendingCenter.value = { type: opening ? 'expand' : 'collapse', key, dir }
  if (dir === 'up') openUpSet.value = next
  else openDownSet.value = next
}

function openMenu(n: LNode, ev: MouseEvent) {
  menu.value = { x: ev.clientX, y: ev.clientY, key: n.key, table: n.table, focus: n.focus, canUp: n.canUp, canDown: n.canDown }
  edgeDetail.value = null
}
function closeMenu() {
  menu.value = null
  edgeDetail.value = null
}

function openEdgeMenu(l: LLink, ev: MouseEvent) {
  menu.value = null
  detail.value = null
  const edges = l.edges || []
  edgeDetail.value = {
    from: l.from,
    to: l.to,
    dir: l.cls,
    groups: groupByWf(edges, null, false),
    count: edges.length,
    wfOpen: {},
    x: ev.clientX,
    y: ev.clientY,
  }
}

function menuDetail() {
  if (!menu.value) return
  showDetail(menu.value.table)
  menu.value = null
  edgeDetail.value = null
}

function showDetail(table: string) {
  const { up, down, tempUp, tempDown } = props.graph
  const isT = isTemp(table)
  const write: { from: string; workflow: string; task: string; script: string | null; taskType: string; project: string }[] = []
  if (isT) {
    const tu = tempUp.get(table)
    if (tu) for (const nbrMap of tu.values()) for (const [nb, recs] of nbrMap) for (const r of recs) write.push({ from: nb, workflow: r.workflow, task: r.task, script: r.script || '', taskType: r.taskType, project: r.project })
  } else {
    const w = up.get(table)
    if (w) for (const [nb, recs] of w) for (const r of recs) write.push({ from: nb, workflow: r.workflow, task: r.task, script: r.script || '', taskType: r.taskType, project: r.project })
  }
  const read: { to: string; workflow: string; task: string; script: string | null; taskType: string; project: string }[] = []
  if (isT) {
    const td = tempDown.get(table)
    if (td) for (const nbrMap of td.values()) for (const [nb, recs] of nbrMap) for (const r of recs) read.push({ to: nb, workflow: r.workflow, task: r.task, script: r.script || '', taskType: r.taskType, project: r.project })
  } else {
    const d = down.get(table)
    if (d) for (const [nb, recs] of d) for (const r of recs) read.push({ to: nb, workflow: r.workflow, task: r.task, script: r.script || '', taskType: r.taskType, project: r.project })
  }
  detailTab.value = 'write'
  detail.value = {
    table,
    write: groupByWf(write, 'from', isT),
    read: groupByWf(read, 'to', isT),
    writeCount: write.length,
    readCount: read.length,
    wfOpen: {},
  }
}

// 按工作流分组，再按"任务 + 脚本"去重聚合，同一任务/脚本下的多张对侧表用顿号隔开。
const UNKNOWN_WF = '（未命名工作流）'
function groupByWf(
  records: { workflow?: string | null; task?: string | null; script?: string | null; taskType?: string | null; project?: string | null; from?: string; to?: string }[],
  peerKey: 'from' | 'to' | null,
  groupByScript: boolean
): WfGroup[] {
  const wfMap = new Map<string, { workflow: string; script: string; items: Map<string, WfGroupItem> }>()
  for (const r of records) {
    const raw = r.workflow == null ? '' : String(r.workflow).trim()
    const wf = raw === '' || raw === '未知' ? UNKNOWN_WF : (r.workflow as string)
    const groupKey = groupByScript ? wf + WS_SEP + (r.script || '') : wf
    if (!wfMap.has(groupKey)) wfMap.set(groupKey, { workflow: wf, script: groupByScript ? (r.script || '') : '', items: new Map() })
    const wfItems = wfMap.get(groupKey)!.items
    const taskKey = (r.task || '') + WS_SEP + (r.script || '')
    if (!wfItems.has(taskKey)) {
      wfItems.set(taskKey, { task: r.task || '（未知任务）', script: r.script || '', peers: [], taskType: r.taskType || '', project: r.project || '' })
    }
    const it = wfItems.get(taskKey)!
    const peer = peerKey ? (r[peerKey] as string) : undefined
    if (peer && !it.peers.includes(peer)) it.peers.push(peer)
    if (r.taskType && !it.taskType.split('、').includes(r.taskType)) it.taskType = it.taskType ? it.taskType + '、' + r.taskType : r.taskType
    if (r.project && !it.project.split('、').includes(r.project)) it.project = it.project ? it.project + '、' + r.project : r.project
  }
  return [...wfMap.entries()]
    .sort((a, b) => (a[0] < b[0] ? -1 : a[0] > b[0] ? 1 : 0))
    .map(([, val]) => ({ workflow: val.workflow, script: val.script, items: [...val.items.values()] }))
}

// D6：未知工作流分组始终隐藏（不再提供全局开关）
function visibleGroups(groups: WfGroup[]): WfGroup[] {
  return groups.filter((g) => g.workflow !== UNKNOWN_WF)
}
function wfSummary(groups: WfGroup[]): { groups: number; records: number } {
  const g = visibleGroups(groups)
  let records = 0
  for (const x of g) records += x.items.length
  return { groups: g.length, records }
}
function isWfOpen(obj: DetailData | EdgeDetailData, key: string): boolean {
  return !!(obj.wfOpen && obj.wfOpen[key])
}
function toggleWf(obj: DetailData | EdgeDetailData, key: string) {
  const cur = obj.wfOpen || {}
  obj.wfOpen = { ...cur, [key]: !cur[key] }
}

function copyText(text: string) {
  if (!text) return
  const done = () => {
    copied.value = text
    setTimeout(() => {
      if (copied.value === text) copied.value = null
    }, 1200)
  }
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(text).then(done).catch(() => fallbackCopy(text, done))
  } else {
    fallbackCopy(text, done)
  }
}
function copyName(full: string, _ev: MouseEvent) {
  copyText(full)
}
function fallbackCopy(text: string, done: () => void) {
  const ta = document.createElement('textarea')
  ta.value = text
  ta.style.position = 'fixed'
  ta.style.opacity = '0'
  document.body.appendChild(ta)
  ta.select()
  try {
    document.execCommand('copy')
  } catch {
    /* ignore */
  }
  document.body.removeChild(ta)
  done()
}

function menuAction(dir: 'up' | 'down', expand: boolean) {
  if (!menu.value) return
  const { key, table } = menu.value
  if (expand) expandAll(key, dir, table)
  else collapseAll(key, dir, table)
  menu.value = null
}

function collectAll(key: string, dir: 'up' | 'down', table: string, pathSet: Set<string>, next: Set<string>) {
  next.add(key)
  if (isTemp(table)) {
    const wsMap = (dir === 'up' ? props.graph.tempUp : props.graph.tempDown).get(table)
    if (!wsMap) return
    const allNb = new Set<string>()
    for (const nbrMap of wsMap.values()) for (const nb of nbrMap.keys()) allNb.add(nb)
    for (const nb of allNb) {
      if (pathSet.has(nb)) continue
      const childKey = `${key}::${dir}::${nb}`
      const np = new Set(pathSet)
      np.add(nb)
      collectAll(childKey, dir, nb, np, next)
    }
  } else {
    const adj = dir === 'up' ? props.graph.up : props.graph.down
    if (!adj.has(table)) return
    for (const [nb] of adj.get(table)!) {
      if (pathSet.has(nb)) continue
      const childKey = `${key}::${dir}::${nb}`
      const np = new Set(pathSet)
      np.add(nb)
      collectAll(childKey, dir, nb, np, next)
    }
  }
}
function expandAll(key: string, dir: 'up' | 'down', table: string) {
  const set = dir === 'up' ? openUpSet : openDownSet
  const next = new Set(set.value)
  const pathSet = new Set([table])
  collectAll(key, dir, table, pathSet, next)
  pendingCenter.value = { type: 'expand', key, dir }
  if (dir === 'up') openUpSet.value = next
  else openDownSet.value = next
}
function removeDescendants(key: string, dir: 'up' | 'down', table: string, pathSet: Set<string>, next: Set<string>) {
  if (isTemp(table)) {
    const wsMap = (dir === 'up' ? props.graph.tempUp : props.graph.tempDown).get(table)
    if (!wsMap) return
    const allNb = new Set<string>()
    for (const nbrMap of wsMap.values()) for (const nb of nbrMap.keys()) allNb.add(nb)
    for (const nb of allNb) {
      if (pathSet.has(nb)) continue
      const childKey = `${key}::${dir}::${nb}`
      next.delete(childKey)
      const np = new Set(pathSet)
      np.add(nb)
      removeDescendants(childKey, dir, nb, np, next)
    }
  } else {
    const adj = dir === 'up' ? props.graph.up : props.graph.down
    if (!adj.has(table)) return
    for (const [nb] of adj.get(table)!) {
      if (pathSet.has(nb)) continue
      const childKey = `${key}::${dir}::${nb}`
      next.delete(childKey)
      const np = new Set(pathSet)
      np.add(nb)
      removeDescendants(childKey, dir, nb, np, next)
    }
  }
}
function collapseAll(key: string, dir: 'up' | 'down', table: string) {
  const set = dir === 'up' ? openUpSet : openDownSet
  const next = new Set(set.value)
  next.delete(key)
  removeDescendants(key, dir, table, new Set([table]), next)
  pendingCenter.value = { type: 'collapse', key, dir }
  if (dir === 'up') openUpSet.value = next
  else openDownSet.value = next
}

function zoomBy(delta: number) {
  const el = root.value
  if (!el) return
  const cx = el.clientWidth / 2
  const cy = el.clientHeight / 2
  const factor = 1 + delta
  const ns = Math.min(2.5, Math.max(0.2, scale.value * factor))
  tx.value = cx - (cx - tx.value) * (ns / scale.value)
  ty.value = cy - (cy - ty.value) * (ns / scale.value)
  scale.value = ns
}
function onWheel(e: WheelEvent) {
  const rect = root.value!.getBoundingClientRect()
  const cx = e.clientX - rect.left
  const cy = e.clientY - rect.top
  const factor = e.deltaY < 0 ? 1.1 : 1 / 1.1
  const ns = Math.min(2.5, Math.max(0.2, scale.value * factor))
  tx.value = cx - (cx - tx.value) * (ns / scale.value)
  ty.value = cy - (cy - ty.value) * (ns / scale.value)
  scale.value = ns
}
function onDown(e: MouseEvent) {
  dragging.value = true
  animating.value = false
  clearTimeout(animTimer)
  lastX.value = e.clientX
  lastY.value = e.clientY
}
function onMove(e: MouseEvent) {
  if (!dragging.value) return
  tx.value += e.clientX - lastX.value
  ty.value += e.clientY - lastY.value
  lastX.value = e.clientX
  lastY.value = e.clientY
}
function onUp() {
  dragging.value = false
}
function animateTo() {
  animating.value = true
  clearTimeout(animTimer)
  animTimer = window.setTimeout(() => {
    animating.value = false
  }, 420)
}
function fitView() {
  const b = model.value.bounds
  if (!b) return
  const el = root.value
  if (!el) return
  const cw = el.clientWidth
  const ch = el.clientHeight
  const pad = 40
  const s = Math.min((cw - pad * 2) / b.w, (ch - pad * 2) / b.h, 1.4)
  scale.value = Math.max(0.2, s)
  tx.value = (cw - b.w * scale.value) / 2
  ty.value = (ch - b.h * scale.value) / 2
  animateTo()
}
function centerOnExpansion(p: PendingCenter) {
  if (!p.key || !p.dir) return
  const prefix = `${p.key}::${p.dir}::`
  const sel = model.value.nodes.filter((n) => n.key === p.key || n.key.startsWith(prefix))
  if (!sel.length) return
  let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity
  for (const n of sel) {
    minX = Math.min(minX, n.x - NODE_W / 2)
    maxX = Math.max(maxX, n.x + NODE_W / 2)
    minY = Math.min(minY, n.y - NODE_H / 2)
    maxY = Math.max(maxY, n.y + NODE_H / 2)
  }
  const cx = (minX + maxX) / 2
  const cy = (minY + maxY) / 2
  const el = root.value!
  tx.value = el.clientWidth / 2 - cx * scale.value
  ty.value = el.clientHeight / 2 - cy * scale.value
  animateTo()
}
function centerOnAll() {
  const ns = model.value.nodes
  if (!ns.length) return
  let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity
  for (const n of ns) {
    minX = Math.min(minX, n.x - NODE_W / 2)
    maxX = Math.max(maxX, n.x + NODE_W / 2)
    minY = Math.min(minY, n.y - NODE_H / 2)
    maxY = Math.max(maxY, n.y + NODE_H / 2)
  }
  const cx = (minX + maxX) / 2
  const cy = (minY + maxY) / 2
  const el = root.value!
  tx.value = el.clientWidth / 2 - cx * scale.value
  ty.value = el.clientHeight / 2 - cy * scale.value
  animateTo()
}
function resetView() {
  scale.value = 1
  tx.value = 0
  ty.value = 0
  animateTo()
  fitView()
}
async function exportPng() {
  const svgEl = svg.value
  if (!svgEl) return
  const clone = svgEl.cloneNode(true) as SVGSVGElement
  clone.setAttribute('width', String(svgW.value))
  clone.setAttribute('height', String(svgH.value))
  clone.setAttribute('xmlns', 'http://www.w3.org/2000/svg')
  const xml = new XMLSerializer().serializeToString(clone)
  const svg64 = 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(xml)
  const img = new Image()
  img.onload = () => {
    const canvas = document.createElement('canvas')
    const ratio = window.devicePixelRatio || 1
    canvas.width = svgW.value * ratio
    canvas.height = svgH.value * ratio
    const ctx = canvas.getContext('2d')!
    ctx.fillStyle = '#eef2f7'
    ctx.fillRect(0, 0, canvas.width, canvas.height)
    ctx.scale(ratio, ratio)
    ctx.drawImage(img, 0, 0)
    canvas.toBlob((blob) => {
      if (!blob) return
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `lineage_${displayName(props.focusTable) || 'view'}.png`
      a.click()
      URL.revokeObjectURL(url)
    })
  }
  img.src = svg64
}
</script>

<style scoped>
.graph-root {
  position: relative;
  width: 100%;
  height: 100%;
  overflow: hidden;
  background: radial-gradient(circle at 20% 20%, #f5f8fc 0%, #eef2f7 100%);
}
.graph-svg {
  display: block;
  cursor: grab;
}
.graph-svg:active {
  cursor: grabbing;
}
.graph-layer.animating {
  transition: transform 0.4s cubic-bezier(0.22, 0.61, 0.36, 1);
}
.edge {
  fill: none;
  stroke-width: 1.6;
  pointer-events: none;
}
.edge-hit {
  fill: none;
  stroke: transparent;
  stroke-width: 12;
  pointer-events: stroke;
  cursor: pointer;
}
.edge.down {
  stroke: #9aa7b5;
}
.edge.up {
  stroke: #c2a36b;
}
.edge-g.dim .edge {
  stroke: #e2e7ee;
  opacity: 0.5;
}
.edge-g.hot .edge {
  stroke: #1a73e8;
  stroke-width: 2.6;
}
.edge-g.hover .edge {
  stroke: #1a73e8;
  stroke-width: 3;
}
.node-rect.dim {
  opacity: 0.35;
}
.node-rect.hot {
  stroke-width: 2.5;
}
.node-rect {
  stroke-width: 1.5;
  cursor: pointer;
  filter: drop-shadow(0 2px 4px rgba(0, 0, 0, 0.08));
}
.node-rect.formal {
  fill: #e8f0fe;
  stroke: #1a73e8;
}
.node-rect.temp {
  fill: #fef7e0;
  stroke: #f2a100;
}
.node.focus .node-rect {
  stroke: #188038;
  stroke-width: 2.5;
}
.node.focus .node-rect.hot {
  stroke: #188038;
}
.node-db {
  font-size: 9px;
  font-weight: 600;
  fill: #7a8aa0;
  pointer-events: none;
}
.node-tbl {
  font-size: 10px;
  font-weight: 600;
  fill: #1f2d3d;
  pointer-events: none;
}
.copy-ico {
  cursor: pointer;
}
.copy-ico circle {
  fill: #ffffff;
  stroke: #c2cbd6;
}
.copy-ico:hover circle {
  stroke: #1a73e8;
}
.copy-ico circle.done {
  fill: #188038;
  stroke: #188038;
}
.copy-glyph {
  font-size: 12px;
  fill: #5a6b7b;
  pointer-events: none;
}
.copy-ico:hover .copy-glyph {
  fill: #1a73e8;
}
.copy-ico circle.done + .copy-glyph {
  fill: #fff;
}
.toggle {
  cursor: pointer;
}
.toggle circle {
  fill: #ffffff;
  stroke: #b9c4d0;
  stroke-width: 1.4;
}
.toggle.up.on circle {
  fill: #f2a100;
  stroke: #f2a100;
}
.toggle.down.on circle {
  fill: #1a73e8;
  stroke: #1a73e8;
}
.toggle-ico {
  font-size: 14px;
  font-weight: 700;
  fill: #5a6b7b;
  pointer-events: none;
}
.toggle.on .toggle-ico {
  fill: #fff;
}
.toggle-badge {
  font-size: 10px;
  fill: #8a96a3;
  pointer-events: none;
}
.zoom-controls {
  position: absolute;
  right: 16px;
  bottom: 16px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  z-index: 20;
}
.zoom-controls button {
  width: 36px;
  height: 36px;
  border: 1px solid #d7dee7;
  background: #fff;
  border-radius: 8px;
  font-size: 16px;
  cursor: pointer;
  color: #37475a;
}
.zoom-controls button:hover {
  background: #eef4ff;
  border-color: #1a73e8;
}
.legend {
  position: absolute;
  left: 16px;
  top: 16px;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 16px;
  background: rgba(255, 255, 255, 0.9);
  padding: 8px 14px;
  border-radius: 8px;
  border: 1px solid #e3e9f0;
  font-size: 13px;
  z-index: 20;
  max-width: 70%;
}
.legend-item {
  display: flex;
  align-items: center;
  gap: 6px;
  color: #37475a;
}
.legend-hint {
  color: #9aa7b5;
  font-size: 12px;
}
.dot {
  width: 14px;
  height: 14px;
  border-radius: 4px;
  display: inline-block;
}
.dot.formal {
  background: #e8f0fe;
  border: 1.5px solid #1a73e8;
}
.dot.temp {
  background: #fef7e0;
  border: 1.5px solid #f2a100;
}
.dot.focus {
  background: #e8f0fe;
  border: 2.5px solid #188038;
}
.detail-panel {
  position: absolute;
  top: 16px;
  right: 16px;
  width: 320px;
  max-height: calc(100% - 32px);
  overflow-y: auto;
  background: #fff;
  border: 1px solid #d7dee7;
  border-radius: 10px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.14);
  z-index: 30;
  padding: 12px 14px;
  font-size: 13px;
  color: #37475a;
}
.detail-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}
.detail-title {
  font-size: 15px;
  font-weight: 700;
  color: #1f2d3d;
}
.detail-close {
  border: none;
  background: transparent;
  font-size: 20px;
  line-height: 1;
  color: #8a96a3;
  cursor: pointer;
  padding: 0 4px;
}
.detail-close:hover {
  color: #1a73e8;
}
.detail-full {
  font-size: 11px;
  color: #8a96a3;
  margin: 4px 0 10px;
  word-break: break-all;
  font-family: ui-monospace, Menlo, Consolas, monospace;
}
.detail-tabs {
  display: flex;
  border-bottom: 2px solid #e3e9f0;
  margin: 4px 0 10px;
}
.detail-tab {
  flex: 1;
  text-align: center;
  padding: 7px 8px;
  font-size: 13px;
  font-weight: 600;
  color: #55657a;
  cursor: pointer;
  border-bottom: 2px solid transparent;
  margin-bottom: -2px;
  user-select: none;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.detail-tab:hover {
  color: #1a73e8;
}
.detail-tab.active {
  color: #1a73e8;
  border-bottom-color: #1a73e8;
}
.detail-sec {
  margin-bottom: 10px;
}
.detail-sec-title {
  font-size: 12px;
  font-weight: 700;
  color: #55657a;
  margin-bottom: 4px;
  padding-bottom: 3px;
  border-bottom: 1px dashed #e3e9f0;
}
.detail-sec ul {
  margin: 0;
  padding: 0;
  list-style: none;
}
.wf-group {
  margin-bottom: 6px;
}
.wf-name {
  font-size: 11px;
  font-weight: 700;
  color: #1a73e8;
  background: #eef4ff;
  border-radius: 5px;
  padding: 2px 6px;
  margin-bottom: 3px;
  word-break: break-all;
}
.wf-name.wf-collapsible:hover {
  background: #dbe8ff;
}
.wf-collapsible {
  display: flex;
  align-items: center;
  gap: 4px;
  cursor: pointer;
}
.wf-title {
  flex: 1 1 auto;
  word-break: break-all;
  user-select: text;
}
.wf-caret {
  display: inline-block;
  width: 12px;
  flex: 0 0 12px;
  color: #1a73e8;
  user-select: none;
}
.wf-copy {
  flex: 0 0 auto;
  margin-left: 2px;
  padding: 0 3px;
  font-size: 12px;
  line-height: 1;
  color: #5f6368;
  border-radius: 3px;
  cursor: pointer;
  user-select: none;
}
.wf-copy:hover {
  background: #cfe2ff;
  color: #1a73e8;
}
.ti-copy {
  color: #1a73e8;
  cursor: pointer;
  word-break: break-all;
}
.ti-detail {
  padding: 3px 6px 5px 10px;
  font-size: 12px;
  color: #37475a;
}
.ti-detail > div {
  display: flex;
  gap: 6px;
  padding: 1px 0;
  word-break: break-all;
}
.ti-label {
  flex: 0 0 48px;
  color: #8a96a3;
}
.detail-sec li {
  font-size: 12px;
  padding: 4px 6px;
  border-radius: 5px;
  cursor: pointer;
  word-break: break-all;
}
.detail-sec li:hover {
  background: #eef4ff;
  color: #1a73e8;
}
.detail-empty {
  font-size: 12px;
  color: #9aa7b5;
  padding: 6px 0;
}
.edge-detail {
  z-index: 60;
  max-width: 340px;
}
.edge-rel {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 5px;
  font-size: 13px;
  color: #34465c;
  margin-bottom: 4px;
}
.er-label {
  font-size: 11px;
  font-weight: 700;
  padding: 1px 6px;
  border-radius: 4px;
  color: #fff;
}
.er-label.read {
  background: #c2a36b;
}
.er-label.write {
  background: #1a73e8;
}
.er-name {
  font-weight: 600;
  color: #1f2d3d;
}
.er-arrow {
  color: #b0bac6;
  font-weight: 700;
}
.edge-full {
  font-size: 11px;
  color: #8a96a3;
  margin-top: 2px;
  word-break: break-all;
  font-family: ui-monospace, Menlo, Consolas, monospace;
}
.ctx-menu {
  position: fixed;
  z-index: 50;
  background: #fff;
  border: 1px solid #d7dee7;
  border-radius: 8px;
  box-shadow: 0 6px 20px rgba(0, 0, 0, 0.15);
  padding: 6px;
  min-width: 160px;
}
.ctx-menu .ctx-title {
  font-size: 12px;
  color: #8a96a3;
  padding: 2px 8px 6px;
  border-bottom: 1px solid #eef2f7;
  margin-bottom: 4px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.ctx-menu button {
  display: block;
  width: 100%;
  text-align: left;
  border: none;
  background: transparent;
  padding: 7px 8px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
  color: #37475a;
}
.ctx-menu button:hover {
  background: #eef4ff;
  color: #1a73e8;
}
.empty-hint {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  color: #9aa7b5;
  font-size: 16px;
}
</style>
