<template>
  <!-- 一次性密码展示：创建用户 / 重置密码共用 -->
  <el-dialog v-model="visible" :title="title" width="420px" :show-close="false">
    <el-alert type="warning" :closable="false" show-icon>
      <template #title>{{ tip }}</template>
    </el-alert>
    <div class="temp-pwd mono">{{ password }}</div>
    <template #footer>
      <el-button type="primary" @click="visible = false">我已记录</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  modelValue: boolean
  password: string
  /** 场景：created 新建用户 / reset 重置密码 */
  scene: 'created' | 'reset'
}>()

const emit = defineEmits<{ (e: 'update:modelValue', v: boolean): void }>()

const visible = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})

const title = computed(() => (props.scene === 'created' ? '用户已创建' : '密码已重置'))
const tip = computed(() =>
  props.scene === 'created'
    ? '请将以下初始密码提供给用户，首次登录需强制修改'
    : '临时密码如下，用户首次登录需强制修改'
)
</script>

<style scoped>
.temp-pwd {
  margin-top: 12px;
  padding: 12px;
  background: #f3f6fb;
  border: 1px solid var(--color-border);
  border-radius: var(--el-border-radius-base);
  font-size: 15px;
  text-align: center;
  letter-spacing: 1px;
  user-select: all;
}
</style>
