<template>
  <div class="stage-flow">
    <div v-for="(s, i) in stages" :key="s.title" class="stage">
      <div class="stage-card">
        <div class="stage-num">{{ s.no }}</div>
        <div class="stage-title">{{ s.title }}</div>
        <div class="stage-desc">{{ s.desc }}</div>
      </div>
      <div v-if="i < stages.length - 1" class="stage-arrow" aria-hidden="true">→</div>
    </div>
  </div>
</template>

<script setup lang="ts">
// 4.1 大数据迁移标准流程（BRD 第四章）
const stages = [
  {
    no: 1,
    title: '需求调研',
    desc: '旧集群架构、数据流向、数据链路、元数据与数据清单、任务台账、代码清单、数据源清单',
  },
  {
    no: 2,
    title: '元数据与数据迁移',
    desc: '按清单执行历史数据迁移，完成后标注每个表的数据迁移截止日期',
  },
  {
    no: 3,
    title: '任务迁移',
    desc: '代码改造 → 迁移至新集群 → 提交调度 → 持续解决报错与优化 → 稳定运行',
  },
  {
    no: 4,
    title: '数据校验',
    desc: '以任务台账为入口，逐表比对输出数据，每日校验，排查记录留痕',
  },
  {
    no: 5,
    title: '客户验收',
    desc: '客户对校验通过的表线下验收确认，回填台账补全任务状态',
  },
]
</script>

<style scoped>
.stage-flow {
  display: flex;
  flex-wrap: wrap;
  align-items: stretch;
  gap: 4px;
}
.stage {
  display: flex;
  align-items: center;
  flex: 1 1 180px;
  min-width: 180px;
}
.stage-card {
  flex: 1;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--el-border-radius-base);
  padding: 14px 14px 16px;
  position: relative;
}
.stage-num {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: var(--color-primary);
  color: #fff;
  font-size: 13px;
  font-weight: 600;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 10px;
}
.stage-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text-primary);
  margin-bottom: 6px;
}
.stage-desc {
  font-size: 12px;
  line-height: 1.6;
  color: var(--color-text-muted);
}
.stage-arrow {
  flex: none;
  padding: 0 8px;
  color: var(--color-text-muted);
  font-size: 18px;
}
</style>
