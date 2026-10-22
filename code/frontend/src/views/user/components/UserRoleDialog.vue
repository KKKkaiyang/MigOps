<template>
  <el-dialog
    v-model="visible"
    :title="`角色分配 - ${user?.name ?? ''}`"
    width="560px"
    :close-on-click-modal="false"
    @closed="reset"
  >
    <div class="role-l0">
      <el-checkbox v-model="roleL0" @change="onL0Change">
        系统管理员（L0，全局角色，拥有所有功能权限）
      </el-checkbox>
    </div>

    <template v-if="!roleL0">
      <div class="role-space-title">项目空间角色</div>
      <el-table :data="spaceRoles" border size="small" max-height="300" v-loading="loading">
        <el-table-column label="项目空间" min-width="180">
          <template #default="{ row }">
            <span>{{ row.space_name }}</span>
            <span class="mono muted">（{{ row.space_code }}）</span>
          </template>
        </el-table-column>
        <el-table-column label="角色" width="150">
          <template #default="{ row }">
            <el-select v-model="row.role_level" placeholder="不绑定" clearable size="small">
              <el-option label="项目管理员(L1)" value="L1" />
              <el-option label="项目成员(L2)" value="L2" />
            </el-select>
          </template>
        </el-table-column>
        <template #empty>
          <span class="muted">暂无可分配的项目空间</span>
        </template>
      </el-table>
    </template>

    <template #footer>
      <el-button @click="visible = false">取消</el-button>
      <el-button type="primary" :loading="submitting" @click="submit">保存</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { getUserRoles, setUserRoles } from '@/api/user'
import { listSpaces } from '@/api/space'
import type { RoleLevel, UserOut } from '@/types'

const props = defineProps<{ modelValue: boolean; user?: UserOut | null }>()
const emit = defineEmits<{
  (e: 'update:modelValue', v: boolean): void
  (e: 'saved'): void
}>()

const visible = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})

const loading = ref(false)
const submitting = ref(false)
const roleL0 = ref(false)
const spaceRoles = ref<
  Array<{ space_id: number; space_name: string; space_code: string; role_level: RoleLevel | '' }>
>([])

/** 勾选 L0 时不再逐空间分配（L0 已拥有全部空间权限） */
function onL0Change(val: string | number | boolean) {
  if (val) {
    spaceRoles.value = spaceRoles.value.map((r) => ({ ...r, role_level: '' }))
  }
}

async function load() {
  if (!props.user) return
  loading.value = true
  try {
    const [roles, spaces] = await Promise.all([
      getUserRoles(props.user.id),
      listSpaces(1, 200),
    ])
    roleL0.value = roles.some((r) => r.role_level === 'L0' && !r.space_id)
    spaceRoles.value = spaces.list.map((s) => {
      const bound = roles.find((r) => r.space_id === s.id)
      return {
        space_id: s.id,
        space_name: s.space_name,
        space_code: s.space_code,
        role_level: (bound?.role_level ?? '') as RoleLevel | '',
      }
    })
  } finally {
    loading.value = false
  }
}

async function submit() {
  if (!props.user) return
  submitting.value = true
  try {
    const roles: Array<{ role_level: RoleLevel; space_id?: number | null }> = []
    if (roleL0.value) {
      roles.push({ role_level: 'L0', space_id: null })
    } else {
      for (const r of spaceRoles.value) {
        if (r.role_level) {
          roles.push({ role_level: r.role_level as RoleLevel, space_id: r.space_id })
        }
      }
    }
    await setUserRoles(props.user.id, roles)
    ElMessage.success('角色已更新')
    visible.value = false
    emit('saved')
  } finally {
    submitting.value = false
  }
}

function reset() {
  roleL0.value = false
  spaceRoles.value = []
}

watch(
  () => props.modelValue,
  (open) => {
    if (open) load()
  }
)
</script>

<style scoped>
.role-l0 {
  padding: 10px 12px;
  background: #f3f6fb;
  border-radius: var(--el-border-radius-base);
  margin-bottom: 12px;
}
.role-space-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text-regular);
  margin-bottom: 8px;
}
.muted {
  color: var(--color-text-muted);
  font-size: 12px;
}
</style>
