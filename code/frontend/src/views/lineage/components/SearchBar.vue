<template>
  <div class="search-bar">
    <div class="search-input-wrap">
      <input
        ref="inputRef"
        v-model="query"
        class="search-input"
        type="text"
        placeholder="输入表名或工作流名称检索血缘"
        @input="onInput"
        @keydown.down.prevent="move(1)"
        @keydown.up.prevent="move(-1)"
        @keydown.enter.prevent="choose(highlighted)"
        @focus="onInput"
        @blur="onBlur"
      />
      <button class="search-btn" @click="choose(highlighted)">检索</button>
    </div>

    <ul v-if="showList && suggestions.length" class="suggest-list">
      <li
        v-for="(s, idx) in suggestions"
        :key="s.key"
        :class="{ active: idx === activeIndex }"
        @mousedown.prevent="choose(idx)"
        @mouseenter="activeIndex = idx"
      >
        <template v-if="s.kind === 'table'">
          <span class="sg-name">{{ shortName(s.value) }}</span>
          <span class="sg-full">{{ s.value }}</span>
          <span class="sg-type" :class="typeClass(s.value)">{{ typeOf(s.value) }}</span>
          <template v-if="projectsOf(s.value).length">
            <span v-for="p in projectsOf(s.value)" :key="'p_' + p" class="sg-tag project">{{ p }}</span>
          </template>
          <template v-if="taskTypesOf(s.value).length">
            <span v-for="tt in taskTypesOf(s.value)" :key="'tt_' + tt" class="sg-tag task-type">{{ tt }}</span>
          </template>
        </template>
        <template v-else>
          <span class="sg-name">⚙ {{ s.value }}</span>
          <span class="sg-full">工作流 · 涉及 {{ s.count }} 张表</span>
          <span class="sg-type wf">工作流</span>
        </template>
      </li>
    </ul>
    <div v-else-if="showList && query && !suggestions.length" class="suggest-empty">
      未找到匹配的表或工作流
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { shortName } from '@/utils/lineage-graph'
import type { LineageWorkflowOut } from '@/types'

const props = defineProps<{
  tables: string[]
  typeMap: Record<string, string>
  projectMap: Record<string, string[]>
  taskTypeMap: Record<string, string[]>
  workflows: LineageWorkflowOut[]
}>()

const emit = defineEmits<{ (e: 'select', name: string): void }>()

interface Suggestion {
  kind: 'table' | 'workflow'
  key: string
  value: string
  count?: number
  focus?: string | null
}

const query = ref('')
const showList = ref(false)
const activeIndex = ref(0)
const inputRef = ref<HTMLInputElement | null>(null)

const suggestions = computed<Suggestion[]>(() => {
  const q = query.value.trim().toLowerCase()
  if (!q) return []
  const tableRes: Suggestion[] = []
  for (const t of props.tables) {
    if (props.typeMap[t] === '临时表') continue // 仅检索正式表
    const full = t.toLowerCase()
    const short = shortName(t).toLowerCase()
    if (full.includes(q) || short.includes(q)) {
      tableRes.push({ kind: 'table', key: 't:' + t, value: t })
      if (tableRes.length >= 20) break
    }
  }
  const wfRes: Suggestion[] = []
  for (const wf of props.workflows) {
    if (wf.name && wf.name.toLowerCase().includes(q)) {
      wfRes.push({ kind: 'workflow', key: 'w:' + wf.name, value: wf.name, count: wf.count, focus: wf.focus })
      if (wfRes.length >= 10) break
    }
  }
  return [...tableRes, ...wfRes]
})

const highlighted = computed(() => suggestions.value[activeIndex.value] || null)

function typeOf(t: string): string {
  return props.typeMap[t] || ''
}
function typeClass(t: string): string {
  return typeOf(t) === '临时表' ? 'temp' : 'formal'
}
function projectsOf(t: string): string[] {
  return props.projectMap[t] || []
}
function taskTypesOf(t: string): string[] {
  return props.taskTypeMap[t] || []
}

function onInput() {
  showList.value = true
  activeIndex.value = 0
}
function onBlur() {
  // 延迟关闭，保证 mousedown 选择先生效
  setTimeout(() => (showList.value = false), 150)
}
function move(delta: number) {
  if (!suggestions.value.length) return
  activeIndex.value = (activeIndex.value + delta + suggestions.value.length) % suggestions.value.length
}
function choose(item: Suggestion | number | null) {
  let target: Suggestion | null
  if (typeof item === 'number') target = suggestions.value[item] || null
  else target = item
  if (!target) return
  if (target.kind === 'workflow') {
    if (!target.focus) return
    query.value = target.value
    showList.value = false
    emit('select', target.focus)
  } else {
    query.value = target.value
    showList.value = false
    emit('select', target.value)
  }
}
</script>

<style scoped>
.search-bar {
  position: relative;
  width: 100%;
}
.search-input-wrap {
  display: flex;
  gap: 8px;
}
.search-input {
  flex: 1;
  height: 40px;
  padding: 0 14px;
  border: 1px solid #c7d2e0;
  border-radius: 8px;
  font-size: 14px;
  outline: none;
  transition: border-color 0.15s;
}
.search-input:focus {
  border-color: #1a73e8;
  box-shadow: 0 0 0 3px rgba(26, 115, 232, 0.12);
}
.search-btn {
  width: 84px;
  height: 40px;
  border: none;
  border-radius: 8px;
  background: #1a73e8;
  color: #fff;
  font-size: 14px;
  cursor: pointer;
}
.search-btn:hover {
  background: #1558b0;
}
.suggest-list {
  position: absolute;
  top: 46px;
  left: 0;
  right: 0;
  max-height: 320px;
  overflow-y: auto;
  margin: 0;
  padding: 4px;
  list-style: none;
  background: #fff;
  border: 1px solid #dce3ec;
  border-radius: 8px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
  z-index: 50;
}
.suggest-list li {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px 8px;
  padding: 7px 10px;
  border-radius: 6px;
  cursor: pointer;
}
.suggest-list li.active {
  background: #eef4ff;
}
.sg-name {
  font-weight: 600;
  color: #1f2d3d;
}
.sg-full {
  flex: 1;
  font-size: 12px;
  color: #8a96a3;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.sg-type {
  font-size: 11px;
  padding: 1px 7px;
  border-radius: 10px;
}
.sg-type.formal {
  background: #e8f0fe;
  color: #1a73e8;
}
.sg-type.temp {
  background: #fef7e0;
  color: #b06a00;
}
.sg-type.wf {
  background: #e6f4ea;
  color: #188038;
}
.sg-tag {
  font-size: 11px;
  padding: 1px 7px;
  border-radius: 10px;
  white-space: nowrap;
}
.sg-tag.project {
  background: #f0e8ff;
  color: #6a3fb5;
}
.sg-tag.task-type {
  background: #e0f2fe;
  color: #075985;
}
.suggest-empty {
  position: absolute;
  top: 46px;
  left: 0;
  right: 0;
  padding: 12px;
  background: #fff;
  border: 1px solid #dce3ec;
  border-radius: 8px;
  color: #8a96a3;
  z-index: 50;
}
</style>
