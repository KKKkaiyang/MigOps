<template>
  <!-- markdown 查看密码验证（确认决策 D4/D10/D16） -->
  <el-dialog
    v-model="visible"
    title="验证查看密码"
    width="420px"
    :close-on-click-modal="false"
    align-center
  >
    <p class="dialog-tip">
      资料「{{ material?.name }}」已设置查看密码，验证通过后可查看与下载（本次会话内不再重复输入）。
    </p>
    <el-input
      v-model="password"
      type="password"
      show-password
      placeholder="请输入查看密码"
      maxlength="64"
      @keyup.enter="submit"
    />
    <template #footer>
      <el-button @click="visible = false">取消</el-button>
      <el-button type="primary" :loading="submitting" @click="submit">验证</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { verifyMaterialPassword } from '@/api/material'
import type { MaterialOut } from '@/types'

const props = defineProps<{ modelValue: boolean; material?: MaterialOut | null }>()
const emit = defineEmits<{
  (e: 'update:modelValue', v: boolean): void
  (e: 'verified', token: string): void
}>()

const route = useRoute()
const spaceId = computed(() => Number(route.params.spaceId))

const visible = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})

const password = ref('')
const submitting = ref(false)

watch(
  () => props.modelValue,
  (open) => {
    if (open) password.value = ''
  }
)

async function submit() {
  if (!password.value) {
    return
  }
  if (!props.material) return
  submitting.value = true
  try {
    const result = await verifyMaterialPassword(
      spaceId.value,
      props.material.id,
      password.value
    )
    emit('verified', result.view_token)
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.dialog-tip {
  margin: 0 0 12px;
  font-size: 13px;
  color: var(--color-text-regular);
  line-height: 1.6;
}
</style>
