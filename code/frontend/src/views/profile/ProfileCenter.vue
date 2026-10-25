<template>
  <div class="profile-center">
    <el-card shadow="never" class="profile-card">
      <template #header>
        <span class="title">个人中心</span>
      </template>

      <section class="section">
        <h4 class="section-title">账号</h4>
        <div class="account">
          <span class="label">用户名</span>
          <span>{{ user?.username }}</span>
          <span class="label">姓名</span>
          <span>{{ user?.name }}</span>
        </div>
      </section>

      <el-divider />

      <el-tabs v-model="activeTab">
        <el-tab-pane label="API 密钥" name="keys">
          <ApiKeys />
        </el-tab-pane>
        <el-tab-pane label="API 接入帮助" name="help">
          <ApiHelp @open-keys="activeTab = 'keys'" />
        </el-tab-pane>
      </el-tabs>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useUserStore } from '@/store/user'
import ApiKeys from './ApiKeys.vue'
import ApiHelp from './ApiHelp.vue'

const userStore = useUserStore()
const user = computed(() => userStore.user)
const activeTab = ref<'keys' | 'help'>('keys')
</script>

<style scoped>
.profile-card {
  border-radius: var(--el-border-radius-base);
}

.title {
  font-size: 15px;
  font-weight: 600;
  color: var(--color-text-primary);
}

.section-title {
  margin: 0 0 12px;
  font-size: 14px;
  color: var(--color-text-primary);
}

.account {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 13px;
  color: var(--color-text-regular);
}

.account .label {
  color: var(--color-text-muted);
}
</style>
