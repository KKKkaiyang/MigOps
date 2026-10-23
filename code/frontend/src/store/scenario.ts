import { defineStore } from 'pinia'
import { ref } from 'vue'
import { listScenarios as listB03Scenarios } from '@/api/data-migration'
import { listScenarios as listB04Scenarios } from '@/api/task-migration'
import type { TaskScenarioOut } from '@/types'

/** b03 数据迁移场景（结构兼容 TaskScenarioOut 展示） */
interface ScenarioBrief {
  id: number
  name: string
}

/**
 * 空间级迁移场景上下文（交互评审 I2）：
 * b03 数据迁移与 b04 任务迁移的场景在空间头常驻切换，且跨导航保持——
 * 用户从「数据迁移」切到「任务迁移」不再丢失已选场景。
 *
 * 两个模块场景表相互独立（b03_scenario / b04_scenario），分别记忆；
 * 切换空间时整体重置，避免串空间。
 */
export const useScenarioStore = defineStore('scenario', () => {
  const spaceId = ref<number | null>(null)
  /** b03 数据迁移当前场景 */
  const b03 = ref<ScenarioBrief | null>(null)
  /** b04 任务迁移当前场景 */
  const b04 = ref<ScenarioBrief | null>(null)

  /** 空间头场景切换器展示用：当前空间是否有任一模块已选场景 */
  const active = ref<'b03' | 'b04' | null>(null)

  function reset(sid: number) {
    if (spaceId.value !== sid) {
      spaceId.value = sid
      b03.value = null
      b04.value = null
      active.value = null
    }
  }

  /** 切空间时整体清空（SpaceLayout watch spaceId 调用） */
  function clear() {
    spaceId.value = null
    b03.value = null
    b04.value = null
    active.value = null
  }

  /**
   * 进入 b03 页面时调用：确保场景已加载。
   * 优先沿用 store 中记忆的场景（校验仍存在）；否则默认选中第一个。
   */
  async function ensureB03(sid: number): Promise<ScenarioBrief | null> {
    reset(sid)
    if (b03.value) return b03.value
    const list = await listB03Scenarios(sid)
    const first = list[0]
    b03.value = first ? { id: first.id, name: first.name } : null
    active.value = 'b03'
    return b03.value
  }

  /** 进入 b04 页面时调用：同上 */
  async function ensureB04(sid: number): Promise<ScenarioBrief | null> {
    reset(sid)
    if (b04.value) return b04.value
    const list: TaskScenarioOut[] = await listB04Scenarios(sid)
    const first = list[0]
    b04.value = first ? { id: first.id, name: first.name } : null
    active.value = 'b04'
    return b04.value
  }

  function selectB03(s: ScenarioBrief | null) {
    b03.value = s
    active.value = s ? 'b03' : active.value
  }

  function selectB04(s: ScenarioBrief | null) {
    b04.value = s
    active.value = s ? 'b04' : active.value
  }

  /** 场景被删除后清理记忆，避免悬挂 ID */
  function clearB03() {
    b03.value = null
    if (active.value === 'b03') active.value = null
  }

  function clearB04() {
    b04.value = null
    if (active.value === 'b04') active.value = null
  }

  return {
    spaceId,
    b03,
    b04,
    active,
    reset,
    clear,
    ensureB03,
    ensureB04,
    selectB03,
    selectB04,
    clearB03,
    clearB04,
  }
})
