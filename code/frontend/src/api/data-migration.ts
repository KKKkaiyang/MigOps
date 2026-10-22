// 数据迁移管理（b03）接口封装
import http from './request'
import type {
  DataMigrationScenarioOut,
  ImportResult,
  MigrationRecordOut,
  PageData,
  TableItemOut,
} from '@/types'

/** 迁移场景列表（含 table_count） */
export function listScenarios(spaceId: number) {
  return http<DataMigrationScenarioOut[]>({
    url: '/b03/scenarios',
    method: 'GET',
    params: { space_id: spaceId },
  })
}

/** 新建迁移场景 */
export function createScenario(spaceId: number, payload: { name: string; remark?: string }) {
  return http<{ id: number; name: string }>({
    url: '/b03/scenarios',
    method: 'POST',
    params: { space_id: spaceId },
    data: payload,
  })
}

/** 更新迁移场景 */
export function updateScenario(
  spaceId: number,
  scenarioId: number,
  payload: { name?: string; remark?: string }
) {
  return http<null>({
    url: `/b03/scenarios/${scenarioId}`,
    method: 'PUT',
    params: { space_id: spaceId },
    data: payload,
  })
}

/** 删除迁移场景（级联删除其下清单与记录） */
export function deleteScenario(spaceId: number, scenarioId: number) {
  return http<null>({
    url: `/b03/scenarios/${scenarioId}`,
    method: 'DELETE',
    params: { space_id: spaceId },
  })
}

/** 库表清单分页 */
export function listTableItems(
  spaceId: number,
  scenarioId: number,
  page = 1,
  page_size = 20,
  filters: {
    keyword?: string
    table_type?: string
    metadata_status?: string
    full_sync_status?: string
    incr_sync_status?: string
  } = {}
) {
  return http<PageData<TableItemOut>>({
    url: `/b03/scenarios/${scenarioId}/table-items`,
    method: 'GET',
    params: { space_id: spaceId, page, page_size, ...filters },
  })
}

/** 新建库表 */
export function createTableItem(
  spaceId: number,
  scenarioId: number,
  payload: {
    db_name: string
    table_name: string
    target_db_name?: string
    target_table_name?: string
    table_type?: string
    data_volume?: number
    partition_count?: number
    remark?: string
  }
) {
  return http<TableItemOut>({
    url: `/b03/scenarios/${scenarioId}/table-items`,
    method: 'POST',
    params: { space_id: spaceId },
    data: payload,
  })
}

/** 更新库表基础信息 */
export function updateTableItem(
  spaceId: number,
  itemId: number,
  payload: {
    target_db_name?: string
    target_table_name?: string
    table_type?: string
    data_volume?: number
    partition_count?: number
    remark?: string
  }
) {
  return http<TableItemOut>({
    url: `/b03/table-items/${itemId}`,
    method: 'PUT',
    params: { space_id: spaceId },
    data: payload,
  })
}

/** 删除库表 */
export function deleteTableItem(spaceId: number, itemId: number) {
  return http<null>({
    url: `/b03/table-items/${itemId}`,
    method: 'DELETE',
    params: { space_id: spaceId },
  })
}

/** 批量更新迁移状态 */
export function batchUpdateStatus(
  spaceId: number,
  scenarioId: number,
  payload: {
    ids: number[]
    metadata_status?: string
    full_sync_status?: string
    full_sync_cutoff_date?: string
    incr_sync_status?: string
    incr_sync_latest_at?: string
  }
) {
  return http<{ affected: number }>({
    url: `/b03/scenarios/${scenarioId}/table-items/batch-status`,
    method: 'POST',
    params: { space_id: spaceId },
    data: payload,
  })
}

/** 导入库表清单（xlsx/csv，按 库名.表名 upsert） */
export function importTableItems(spaceId: number, scenarioId: number, file: File) {
  const form = new FormData()
  form.append('file', file)
  return http<ImportResult>({
    url: `/b03/scenarios/${scenarioId}/table-items/import`,
    method: 'POST',
    params: { space_id: spaceId },
    data: form,
  })
}

/** 迁移过程记录分页 */
export function listRecords(
  spaceId: number,
  itemId: number,
  page = 1,
  page_size = 10
) {
  return http<PageData<MigrationRecordOut>>({
    url: `/b03/table-items/${itemId}/records`,
    method: 'GET',
    params: { space_id: spaceId, page, page_size },
  })
}

/** 新建迁移过程记录 */
export function createRecord(
  spaceId: number,
  itemId: number,
  payload: {
    migration_type: string
    started_at?: string
    finished_at?: string
    data_volume?: number
    method?: string
    data_cutoff_date?: string
    status: string
    remark?: string
  }
) {
  return http<MigrationRecordOut>({
    url: `/b03/table-items/${itemId}/records`,
    method: 'POST',
    params: { space_id: spaceId },
    data: payload,
  })
}

/** 删除迁移过程记录 */
export function deleteRecord(spaceId: number, recordId: number) {
  return http<null>({
    url: `/b03/records/${recordId}`,
    method: 'DELETE',
    params: { space_id: spaceId },
  })
}

/** 导入迁移过程记录 */
export function importRecords(spaceId: number, scenarioId: number, file: File) {
  const form = new FormData()
  form.append('file', file)
  return http<ImportResult>({
    url: `/b03/scenarios/${scenarioId}/records/import`,
    method: 'POST',
    params: { space_id: spaceId },
    data: form,
  })
}
