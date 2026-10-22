<template>
  <div class="status-flow">
    <!-- 4.2 任务迁移状态流转图（配色对齐 CODEBUDDY.md §6.4 设计令牌） -->
    <div class="svg-wrap">
      <svg viewBox="0 0 960 260" xmlns="http://www.w3.org/2000/svg" style="font-family: var(--el-font-family);">
        <defs>
          <marker id="arrow" markerWidth="10" markerHeight="10" refX="8" refY="5" orient="auto">
            <path d="M0,0 L10,5 L0,10 z" fill="#8a96a3" />
          </marker>
          <marker id="arrowRed" markerWidth="10" markerHeight="10" refX="8" refY="5" orient="auto">
            <path d="M0,0 L10,5 L0,10 z" fill="#e53935" />
          </marker>
        </defs>

        <!-- Row 1: 正向状态（绿） / 初始与终态（中性灰） / 挂起（琥珀） -->
        <g>
          <rect x="10" y="40" width="100" height="44" rx="8" fill="#eef2f7" stroke="#bdc3c7" stroke-width="1.5" />
          <text x="60" y="67" text-anchor="middle" font-size="13" fill="#37475a" font-weight="600">未开始</text>
        </g>
        <g>
          <rect x="140" y="40" width="100" height="44" rx="8" fill="#e6f4ea" stroke="#188038" stroke-width="1.5" />
          <text x="190" y="67" text-anchor="middle" font-size="13" fill="#188038" font-weight="600">改造完成</text>
        </g>
        <g>
          <rect x="270" y="40" width="100" height="44" rx="8" fill="#e6f4ea" stroke="#188038" stroke-width="1.5" />
          <text x="320" y="67" text-anchor="middle" font-size="13" fill="#188038" font-weight="600">调度成功</text>
        </g>
        <g>
          <rect x="400" y="40" width="120" height="44" rx="8" fill="#e6f4ea" stroke="#188038" stroke-width="1.5" />
          <text x="460" y="67" text-anchor="middle" font-size="13" fill="#188038" font-weight="600">数据校验通过</text>
        </g>
        <g>
          <rect x="550" y="40" width="130" height="44" rx="8" fill="#e6f4ea" stroke="#188038" stroke-width="1.5" />
          <text x="615" y="67" text-anchor="middle" font-size="13" fill="#188038" font-weight="600">客户验收通过</text>
        </g>
        <g>
          <rect x="710" y="40" width="80" height="44" rx="8" fill="#fef7e0" stroke="#f2a100" stroke-width="1.5" />
          <text x="750" y="67" text-anchor="middle" font-size="13" fill="#b06a00" font-weight="600">挂起</text>
        </g>
        <g>
          <rect x="810" y="40" width="80" height="44" rx="8" fill="#eef2f7" stroke="#bdc3c7" stroke-width="1.5" />
          <text x="850" y="67" text-anchor="middle" font-size="13" fill="#37475a" font-weight="600">废弃</text>
        </g>

        <!-- 正常流转箭头 -->
        <line x1="110" y1="62" x2="138" y2="62" stroke="#8a96a3" stroke-width="2" marker-end="url(#arrow)" />
        <line x1="240" y1="62" x2="268" y2="62" stroke="#8a96a3" stroke-width="2" marker-end="url(#arrow)" />
        <line x1="370" y1="62" x2="398" y2="62" stroke="#8a96a3" stroke-width="2" marker-end="url(#arrow)" />
        <line x1="520" y1="62" x2="548" y2="62" stroke="#8a96a3" stroke-width="2" marker-end="url(#arrow)" />
        <line x1="680" y1="62" x2="708" y2="62" stroke="#f2a100" stroke-width="2" marker-end="url(#arrow)" />
        <line x1="790" y1="62" x2="808" y2="62" stroke="#8a96a3" stroke-width="2" marker-end="url(#arrow)" />

        <!-- 分支：数据校验不通过（异常红） -->
        <g>
          <rect x="400" y="140" width="120" height="44" rx="8" fill="#fdecea" stroke="#e53935" stroke-width="1.5" />
          <text x="460" y="167" text-anchor="middle" font-size="13" fill="#c62828" font-weight="600">数据校验不通过</text>
        </g>
        <line x1="460" y1="84" x2="460" y2="138" stroke="#e53935" stroke-width="2" marker-end="url(#arrowRed)" stroke-dasharray="5,3" />
        <line x1="455" y1="162" x2="340" y2="84" stroke="#e53935" stroke-width="2" marker-end="url(#arrowRed)" stroke-dasharray="5,3" />
        <text x="330" y="130" font-size="11" fill="#e53935">修复后重跑</text>

        <!-- 分支：客户验收不通过（异常红） -->
        <g>
          <rect x="550" y="140" width="130" height="44" rx="8" fill="#fdecea" stroke="#e53935" stroke-width="1.5" />
          <text x="615" y="167" text-anchor="middle" font-size="13" fill="#c62828" font-weight="600">客户验收不通过</text>
        </g>
        <line x1="615" y1="84" x2="615" y2="138" stroke="#e53935" stroke-width="2" marker-end="url(#arrowRed)" stroke-dasharray="5,3" />
        <text x="625" y="115" font-size="11" fill="#e53935">客户驳回</text>
        <path d="M 550 162 Q 500 120 460 84" fill="none" stroke="#e53935" stroke-width="2" stroke-dasharray="5,3" marker-end="url(#arrowRed)" />
        <text x="485" y="135" font-size="11" fill="#e53935">重新排查</text>

        <!-- 图例 -->
        <g transform="translate(10, 210)">
          <rect x="0" y="0" width="14" height="14" rx="3" fill="#e6f4ea" stroke="#188038" />
          <text x="20" y="11" font-size="12" fill="#37475a">正向状态</text>
          <rect x="90" y="0" width="14" height="14" rx="3" fill="#fdecea" stroke="#e53935" />
          <text x="110" y="11" font-size="12" fill="#37475a">异常状态</text>
          <rect x="180" y="0" width="14" height="14" rx="3" fill="#fef7e0" stroke="#f2a100" />
          <text x="200" y="11" font-size="12" fill="#37475a">挂起状态</text>
          <rect x="270" y="0" width="14" height="14" rx="3" fill="#eef2f7" stroke="#bdc3c7" />
          <text x="290" y="11" font-size="12" fill="#37475a">终态</text>
          <line x1="360" y1="7" x2="395" y2="7" stroke="#8a96a3" stroke-width="2" marker-end="url(#arrow)" />
          <text x="403" y="11" font-size="12" fill="#37475a">正常流转</text>
          <line x1="470" y1="7" x2="505" y2="7" stroke="#e53935" stroke-width="2" stroke-dasharray="5,3" marker-end="url(#arrowRed)" />
          <text x="513" y="11" font-size="12" fill="#37475a">异常回退</text>
        </g>
      </svg>
    </div>

    <h4 class="sub-title">状态定义</h4>
    <el-table :data="statusDefs" border size="small" class="def-table">
      <el-table-column prop="value" label="状态值" width="140" />
      <el-table-column label="类型" width="100">
        <template #default="{ row }">
          <el-tag :type="typeTag(row.type).type" size="small" effect="light">
            {{ typeTag(row.type).label }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="meaning" label="含义" />
    </el-table>

    <h4 class="sub-title">状态流转规则</h4>
    <div class="rules">
      <p><strong>正常路径：</strong>未开始 → 改造完成 → 调度成功 → 数据校验通过 → 客户验收通过</p>
      <p><strong>校验不通过回退：</strong>数据校验不通过 → 排查修复 → 重跑校验 → 数据校验通过（或继续不通过）</p>
      <p><strong>验收不通过回退：</strong>客户验收不通过 → 重新排查 → 数据校验通过 → 客户验收通过</p>
      <p><strong>挂起/废弃：</strong>任意正向状态均可转为挂起（可恢复）或废弃（终态）</p>
    </div>
  </div>
</template>

<script setup lang="ts">
// 4.2 任务迁移状态流转（BRD 第四章）
interface StatusDef {
  value: string
  type: '初始' | '正向' | '异常' | '挂起' | '终态'
  meaning: string
}

const statusDefs: StatusDef[] = [
  { value: '未开始', type: '初始', meaning: '任务尚未启动迁移' },
  { value: '改造完成', type: '正向', meaning: '任务代码已完成改造，准备提交新集群调度' },
  { value: '调度成功', type: '正向', meaning: '任务已在新集群成功提交调度并稳定运行' },
  { value: '数据校验通过', type: '正向', meaning: '任务输出表数据在新旧集群对齐，校验通过' },
  { value: '数据校验不通过', type: '异常', meaning: '输出表数据未对齐，需排查修复后重跑校验' },
  { value: '客户验收通过', type: '正向', meaning: '客户线下确认校验结果无误' },
  { value: '客户验收不通过', type: '异常', meaning: '客户线下确认校验结果有误，需重新排查' },
  { value: '挂起', type: '挂起', meaning: '因外部原因暂停迁移，后续可恢复' },
  { value: '废弃', type: '终态', meaning: '任务不再迁移，从清单中标记废弃' },
]

const TYPE_MAP: Record<StatusDef['type'], { label: string; type: 'success' | 'danger' | 'warning' | 'info' }> = {
  初始: { label: '初始', type: 'info' },
  正向: { label: '正向', type: 'success' },
  异常: { label: '异常', type: 'danger' },
  挂起: { label: '挂起', type: 'warning' },
  终态: { label: '终态', type: 'info' },
}

function typeTag(t: StatusDef['type']) {
  return TYPE_MAP[t]
}
</script>

<style scoped>
.svg-wrap {
  width: 100%;
  overflow-x: auto;
  border: 1px solid var(--color-border);
  border-radius: var(--el-border-radius-base);
  background: var(--color-surface);
  padding: 8px;
}
.svg-wrap svg {
  display: block;
  width: 100%;
  min-width: 720px;
  height: auto;
}
.sub-title {
  margin: 20px 0 12px;
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text-primary);
}
.def-table {
  font-size: 12px;
}
.rules {
  border: 1px solid var(--color-border);
  border-radius: var(--el-border-radius-base);
  background: var(--el-color-primary-light-9);
  padding: 12px 16px;
}
.rules p {
  margin: 6px 0;
  font-size: 12px;
  line-height: 1.7;
  color: var(--color-text-regular);
}
.rules strong {
  color: var(--color-text-primary);
}
</style>
