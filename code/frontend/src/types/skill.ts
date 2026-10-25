// skill 管理（b08）类型定义，与后端 Pydantic Schema 对齐

/** skill 实体（b08_skill，平台级全局） */
export interface SkillOut {
  skill_code: string
  name: string
  intro?: string | null
  /** 是否公开：1 公开 / 0 私有 */
  is_public: number
  /** 状态：上架 / 下架 */
  status: string
  /** 使用热度（累计下载次数） */
  download_count: number
  author_user_id: number
  author_name?: string | null
  version: string
  file_size?: number | null
  created_at?: string | null
}

/** API 密钥列表项（secret 掩码，不返回明文） */
export interface ApiKeyOut {
  id: number
  access_key: string
  /** 状态：启用 / 停用 */
  status: string
  last_used_at?: string | null
  created_at?: string | null
}

/** 生成密钥的返回：secret_key 仅此一次明文 */
export interface ApiKeyCreated {
  id: number
  access_key: string
  secret_key: string
  status: string
}
