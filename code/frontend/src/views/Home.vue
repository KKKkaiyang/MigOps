<template>
  <div class="overview">
    <!-- 我的项目空间 Panel 区（需求 §3：概览页主体最上方） -->
    <SpacePanelSection />

    <el-card class="banner" shadow="never">
      <div class="banner-inner">
        <div>
          <div class="banner-title">迁移管家 MigOps</div>
          <div class="banner-sub">面向公有云大数据迁移项目的管理平台 · 以「迁移空间」为隔离单元</div>
        </div>
        <el-button type="primary" @click="goSpaces">进入项目空间</el-button>
      </div>
    </el-card>

    <el-card class="section-card" shadow="never">
      <template #header>
        <div class="section-head">
          <span class="sec-no">4.1</span>
          <span class="sec-title">大数据迁移标准流程</span>
        </div>
      </template>
      <p class="section-desc">
        一个完整的公有云大数据迁移项目包含以下五大阶段，平台支撑全流程线上化管理：
      </p>
      <MigrationStageFlow />
    </el-card>

    <el-card class="section-card" shadow="never">
      <template #header>
        <div class="section-head">
          <span class="sec-no">4.2</span>
          <span class="sec-title">任务迁移状态流转</span>
        </div>
      </template>
      <p class="section-desc">
        任务在全生命周期中的状态定义如下，状态之间按规则流转：
      </p>
      <TaskStatusFlow />
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
import MigrationStageFlow from '@/components/overview/MigrationStageFlow.vue'
import TaskStatusFlow from '@/components/overview/TaskStatusFlow.vue'
import SpacePanelSection from '@/views/home/components/SpacePanelSection.vue'

const router = useRouter()

function goSpaces() {
  router.push('/b01/spaces')
}
</script>

<style scoped>
.overview {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.banner {
  border-color: var(--color-border);
}

.banner-inner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.banner-title {
  font-size: 18px;
  font-weight: 600;
  color: var(--color-text-primary);
}

.banner-sub {
  margin-top: 4px;
  font-size: 12px;
  color: var(--color-text-muted);
}

.section-card {
  border-color: var(--color-border);
}

.section-head {
  display: flex;
  align-items: center;
  gap: 10px;
}

.sec-no {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 36px;
  height: 22px;
  padding: 0 8px;
  border-radius: var(--el-border-radius-base);
  background: var(--color-primary);
  color: #fff;
  font-size: 12px;
  font-weight: 600;
}

.sec-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--color-text-primary);
}

.section-desc {
  margin: 0 0 16px;
  font-size: 13px;
  color: var(--color-text-regular);
}
</style>
