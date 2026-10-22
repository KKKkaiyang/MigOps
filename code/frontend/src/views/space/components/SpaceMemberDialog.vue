<template>
  <el-dialog
    v-model="visible"
    :title="`成员管理 - ${space?.space_name ?? ''}`"
    width="640px"
    :close-on-click-modal="false"
    @closed="reset"
  >
    <div class="member-toolbar" v-if="canManage">
      <el-select
        v-model="newMember.user_id"
        placeholder="选择用户"
        filterable
        :loading="usersLoading"
        style="width: 200px"
      >
        <el-option
          v-for="u in candidateUsers"
          :key="u.id"
          :label="`${u.name}（${u.username}）`"
          :value="u.id"
        />
      </el-select>
      <el-select v-model="newMember.role_level" style="width: 140px">
        <el-option label="项目管理员" value="L1" />
        <el-option label="项目成员" value="L2" />
      </el-select>
      <el-button type="primary" :loading="adding" @click="add">添加</el-button>
      <span class="toolbar-tip">仅系统管理员与项目管理员可管理成员</span>
    </div>

    <el-table :data="members" v-loading="loading" border size="small" max-height="360">
      <el-table-column prop="username" label="用户名" width="120">
        <template #default="{ row }">
          <span class="mono">{{ row.username }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="name" label="姓名" width="100" />
      <el-table-column prop="org_type" label="归属" width="90" />
      <el-table-column label="角色" width="120">
        <template #default="{ row }">
          <RoleLevelTag :level="row.role_level" />
        </template>
      </el-table-column>
      <el-table-column label="操作" min-width="140">
        <template #default="{ row }">
          <template v-if="canManage">
            <el-button link type="primary" @click="switchRole(row as SpaceMemberOut)">切换角色</el-button>
            <el-button link type="danger" @click="remove(row as SpaceMemberOut)">移除</el-button>
          </template>
          <span v-else class="muted">—</span>
        </template>
      </el-table-column>
      <template #empty>
        <span class="muted">暂无成员</span>
      </template>
    </el-table>

    <template #footer>
      <el-button @click="visible = false">关闭</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { addMember, listMembers, removeMember, updateMemberRole } from '@/api/space'
import { listUsers } from '@/api/user'
import RoleLevelTag from '@/components/common/RoleLevelTag.vue'
import { useUserStore } from '@/store/user'
import type { SpaceMemberOut, SpaceOut, UserOut } from '@/types'

const props = defineProps<{ modelValue: boolean; space?: SpaceOut | null }>()
const emit = defineEmits<{
  (e: 'update:modelValue', v: boolean): void
  (e: 'changed'): void
}>()

const userStore = useUserStore()

const visible = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})

const loading = ref(false)
const adding = ref(false)
const members = ref<SpaceMemberOut[]>([])
const users = ref<UserOut[]>([])
const usersLoading = ref(false)

const newMember = reactive<{ user_id: number | undefined; role_level: 'L1' | 'L2' }>({
  user_id: undefined,
  role_level: 'L2',
})

/** 空间管理员可管理成员：L0 或该空间 L1 */
const canManage = computed(
  () => props.space?.my_role === 'L0' || props.space?.my_role === 'L1'
)

const memberIds = computed(() => new Set(members.value.map((m) => m.user_id)))
const candidateUsers = computed(() => users.value.filter((u) => !memberIds.value.has(u.id)))

async function loadMembers() {
  if (!props.space) return
  loading.value = true
  try {
    members.value = await listMembers(props.space.id)
  } finally {
    loading.value = false
  }
}

async function loadUsers() {
  usersLoading.value = true
  try {
    const data = await listUsers(1, 200)
    users.value = data.list.filter((u) => u.status === 'enabled')
  } finally {
    usersLoading.value = false
  }
}

async function add() {
  if (!props.space || !newMember.user_id) {
    ElMessage.warning('请选择要添加的用户')
    return
  }
  adding.value = true
  try {
    await addMember(props.space.id, {
      user_id: newMember.user_id,
      role_level: newMember.role_level,
    })
    ElMessage.success('成员已添加')
    newMember.user_id = undefined
    await loadMembers()
    emit('changed')
  } finally {
    adding.value = false
  }
}

async function switchRole(row: SpaceMemberOut) {
  if (!props.space) return
  const next = row.role_level === 'L1' ? 'L2' : 'L1'
  const label = next === 'L1' ? '项目管理员' : '项目成员'
  await ElMessageBox.confirm(
    `确认将「${row.name}」的角色切换为${label}？`,
    '切换角色',
    { type: 'warning' }
  )
  await updateMemberRole(props.space.id, row.user_id, next)
  ElMessage.success('角色已更新')
  await loadMembers()
  emit('changed')
}

async function remove(row: SpaceMemberOut) {
  if (!props.space) return
  await ElMessageBox.confirm(`确认将「${row.name}」移出该空间？`, '移除成员', {
    type: 'warning',
    confirmButtonText: '移除',
  })
  await removeMember(props.space.id, row.user_id)
  ElMessage.success('成员已移除')
  await loadMembers()
  emit('changed')
}

function reset() {
  members.value = []
  newMember.user_id = undefined
  newMember.role_level = 'L2'
}

watch(
  () => props.modelValue,
  (open) => {
    if (open) {
      loadMembers()
      if (canManage.value) loadUsers()
    }
  }
)

onMounted(() => {
  // 组件随对话框按需渲染，此处无需主动加载
})
</script>

<style scoped>
.member-toolbar {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
  flex-wrap: wrap;
}

.toolbar-tip {
  font-size: 11px;
  color: var(--color-text-muted);
  margin-left: auto;
}

.muted {
  color: var(--color-text-muted);
  font-size: 12px;
}
</style>
