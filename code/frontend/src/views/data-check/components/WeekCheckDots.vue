<template>
  <!-- 近7天校验结果：7 个方格（T-7~T-1，最近在左；通过=绿实心 / 不通过=红实心 / 无记录=灰空心，D8） -->
  <div class="week-dots">
    <el-tooltip
      v-for="d in days"
      :key="d.data_date"
      :content="tipContent(d)"
      placement="top"
      :show-after="100"
    >
      <span class="dot" :class="dotClass(d)" />
    </el-tooltip>
  </div>
</template>

<script setup lang="ts">
import { formatNumber } from '@/utils/format'
import type { CheckResultDay } from '@/types'

defineProps<{ days: CheckResultDay[] }>()

/** MM-DD */
function fmtMD(iso: string): string {
  return iso ? iso.slice(5, 10) : ''
}

function dotClass(d: CheckResultDay): string {
  if (d.result === '通过') return 'dot-pass'
  if (d.result === '不通过') return 'dot-fail'
  return 'dot-none'
}

function tipContent(d: CheckResultDay): string {
  const md = fmtMD(d.data_date)
  if (!d.result) return `${md} 无校验记录`
  return `${md} ${d.result}｜源端 ${formatNumber(d.src_volume)} / 目标端 ${formatNumber(d.dst_volume)}`
}
</script>

<style scoped>
.week-dots {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.dot {
  width: 14px;
  height: 14px;
  border-radius: 4px;
  display: inline-block;
  cursor: default;
}

.dot-pass {
  background: #27ae60;
}

.dot-fail {
  background: #e74c3c;
}

.dot-none {
  background: #f3f6fb;
  border: 1px solid #bdc3c7;
  box-sizing: border-box;
}
</style>
