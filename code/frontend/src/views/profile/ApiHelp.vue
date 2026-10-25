<template>
  <div class="api-help">
    <el-alert type="info" :closable="false" show-icon class="intro">
      <template #title>API 接入帮助</template>
      ak/sk 是平台 REST API 的签名鉴权凭证，用于以程序方式调用接口，完成
      <b>台账刷新</b>、<b>数据校验结果回写</b>、<b>skill 上传</b> 等自动化操作。
      本页提供创建指引、公共报文约定、Python 调用模板与按板块的场景化接口说明，与 Swagger（<a href="/docs" target="_blank">/docs</a>）互补。
    </el-alert>

    <div class="layout">
      <!-- 左侧锚点导航 -->
      <nav class="toc">
        <div class="toc-title">本页导航</div>
        <a
          v-for="item in toc"
          :key="item.id"
          :href="`#${item.id}`"
          class="toc-link"
          :class="{ active: activeSection === item.id }"
          @click.prevent="scrollTo(item.id)"
        >
          {{ item.label }}
        </a>
        <el-button link type="primary" :icon="Key" class="toc-keys" @click="$emit('open-keys')">
          前往生成密钥
        </el-button>
      </nav>

      <!-- 右侧内容 -->
      <div class="content">
        <!-- 概述 -->
        <section id="overview" class="block">
          <h3 class="block-title">一、概述</h3>
          <p>
            平台以「迁移空间」为隔离单元，核心业务（数据迁移 b03、任务迁移 b04、血缘 b07、skill b08 等）
            均已支持<b>双鉴权</b>：既可用网页登录态（<code>Authorization: Bearer &lt;token&gt;</code>），
            也可用 ak/sk 签名调用 REST API。借助 ak/sk，你可以把平台的台账维护、校验回写、skill 分发等动作
            自动化，例如定时脚本刷新任务状态、CI 流水线回写校验结果。
          </p>
          <ul class="tip-list">
            <li>ak/sk 为<b>平台级公共能力</b>，任何登录用户均可自助生成，自管自身密钥。</li>
            <li>空间隔离业务（b03~b07）经 ak/sk 调用时，操作人须为目标空间成员（详见常见问题）。</li>
          </ul>
        </section>

        <!-- 创建密钥 -->
        <section id="create" class="block">
          <h3 class="block-title">二、创建密钥</h3>
          <el-steps :active="1" align-center class="steps">
            <el-step title="进入个人中心" description="顶部头像 → 个人中心" />
            <el-step title="切换至 API 密钥" description="本页标签页「API 密钥」" />
            <el-step title="生成并保存" description="点击「生成密钥」" />
          </el-steps>
          <el-alert type="warning" :closable="false" show-icon class="warn">
            <template #title>secret_key 仅展示一次</template>
            <span>
              生成后 <code>secret_key</code> 仅在弹窗中明文展示一次，请立即复制并妥善保存；
              关闭后无法再次查看。遗失须先吊销旧密钥再重新生成。
            </span>
          </el-alert>
          <el-button type="primary" :icon="Key" class="mt" @click="$emit('open-keys')">
            前往「API 密钥」生成
          </el-button>
        </section>

        <!-- 公共报文 -->
        <section id="common" class="block">
          <h3 class="block-title">三、公共报文规范</h3>
          <p>以下约定适用于所有接口，场景化接口不再重复。</p>

          <h4 class="sub-title">3.1 公共请求头</h4>
          <el-table :data="reqHeaders" border size="small" class="tbl">
            <el-table-column prop="name" label="头名称" width="170">
              <template #default="{ row }"><code class="mono">{{ row.name }}</code></template>
            </el-table-column>
            <el-table-column prop="required" label="必填" width="90" align="center" />
            <el-table-column prop="desc" label="说明" />
          </el-table>

          <h4 class="sub-title">3.2 公共响应信封</h4>
          <p>所有接口统一返回：</p>
          <pre class="code-block">{{ respEnvelope }}</pre>

          <h4 class="sub-title">3.3 公共错误码</h4>
          <el-table :data="errorCodes" border size="small" class="tbl">
            <el-table-column prop="code" label="code" width="100" align="center">
              <template #default="{ row }"><code class="mono">{{ row.code }}</code></template>
            </el-table-column>
            <el-table-column prop="name" label="含义" width="200" />
            <el-table-column prop="scene" label="触发场景" />
          </el-table>
        </section>

        <!-- 鉴权与调用 -->
        <section id="auth" class="block">
          <h3 class="block-title">四、鉴权与调用（Python）</h3>
          <p>
            签名串为 <code class="mono">METHOD\nPATH\nTIMESTAMP\nNONCE</code>，
            使用 <code class="mono">HMAC-SHA256</code> 计算；时间戳为<b>毫秒</b>、与服务器偏差 ≤ 5 分钟，
            <code class="mono">nonce</code> 单次有效（防重放）。<b>PATH 仅取路径，不含 query 参数。</b>
          </p>
          <div class="code-wrap">
            <div class="code-head">
              <span>Python 通用签名 / 调用模板（仅 Python）</span>
              <el-button link type="primary" :icon="CopyDocument" @click="copy(pyTemplate)">复制</el-button>
            </div>
            <pre class="code-block">{{ pyTemplate }}</pre>
          </div>
          <p class="note">
            说明：<code class="mono">secret_key</code> 仅保存在客户端，请勿通过任何请求上传；
            正式环境将 <code class="mono">BASE_URL</code> 替换为平台地址（如 <code class="mono">https://host/api/v1</code>）。
          </p>
        </section>

        <!-- 板块接口说明 -->
        <section id="apis" class="block">
          <h3 class="block-title">五、按板块场景化接口说明</h3>
          <p>
            下列为典型自动化场景的<b>精选</b>接口；每个接口仅列「接口名称 / 接口说明 / 接口输入 / 输出参数说明」四项。
            完整端点与双鉴权标注以 Swagger（<a href="/docs" target="_blank">/docs</a>）为准。
          </p>

          <div v-for="block in apiBlocks" :key="block.id" class="api-block">
            <h4 class="sub-title">
              {{ block.tag }} — 场景「{{ block.scene }}」
            </h4>
            <el-table :data="block.apis" border size="small" class="tbl">
              <el-table-column prop="name" label="接口名称" width="300">
                <template #default="{ row }"><code class="mono">{{ row.name }}</code></template>
              </el-table-column>
              <el-table-column prop="desc" label="接口说明" width="200" />
              <el-table-column prop="input" label="接口输入" />
              <el-table-column prop="output" label="输出参数说明" />
            </el-table>
          </div>

          <el-alert type="info" :closable="false" class="warn">
            <template #title>b05 数据校验（二期前瞻）</template>
            <span>
              二期将开放校验结果回写接口（如 <code class="mono">POST /api/v1/b05/checks/{id}/result</code>），
              用于以 ak/sk 方式回写校验结论。具体输入 / 输出以二期需求与 Swagger 为准，本期不实现。
            </span>
          </el-alert>
        </section>

        <!-- 常见问题 -->
        <section id="faq" class="block">
          <h3 class="block-title">六、常见问题（401 / 403 排查）</h3>
          <el-collapse class="faq">
            <el-collapse-item title="40100 未认证：签名校验失败" name="401">
              检查四项是否齐全：<code class="mono">X-Access-Key</code> / <code class="mono">X-Timestamp</code> /
              <code class="mono">X-Nonce</code> / <code class="mono">X-Signature</code>；
              时间戳是否为<b>毫秒</b>且在 ±5 分钟内；签名串是否为
              <code class="mono">METHOD\nPATH\nTIMESTAMP\nNONCE</code>（PATH 不含 query）；
              <code class="mono">secret_key</code> 是否与 <code class="mono">access_key</code> 匹配。
            </el-collapse-item>
            <el-collapse-item title="40300 无权限：非空间成员 / 角色不足" name="403">
              b03~b07 为空间隔离业务，ak/sk 操作人须为目标空间成员且具对应角色。
              调用时须带空间上下文（如 <code class="mono">space_id</code> 或路径中的空间场景 ID），否则返回 40300。
            </el-collapse-item>
            <el-collapse-item title="40400 资源不存在" name="404">
              指定的 id / code 不存在、已删除或已下架；请核对路径参数与接口所属空间。
            </el-collapse-item>
          </el-collapse>
        </section>

        <!-- Swagger 边界 -->
        <section id="swagger" class="block">
          <h3 class="block-title">七、与 Swagger（/docs）的边界</h3>
          <ul class="tip-list">
            <li><b>本帮助页</b> = 任务导向精选，面向「怎么用」（按场景 + Python 示例）。</li>
            <li><b>Swagger（<a href="/docs" target="_blank">/docs</a>）</b> = 完整接口参考，面向每个端点的定义与双鉴权标注。</li>
            <li>二者互补，帮助页不重复罗列全部端点，避免口径漂移。</li>
          </ul>
        </section>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, onBeforeUnmount, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { CopyDocument, Key } from '@element-plus/icons-vue'

defineEmits<{ (e: 'open-keys'): void }>()

const toc = [
  { id: 'overview', label: '一、概述' },
  { id: 'create', label: '二、创建密钥' },
  { id: 'common', label: '三、公共报文规范' },
  { id: 'auth', label: '四、鉴权与调用' },
  { id: 'apis', label: '五、板块接口说明' },
  { id: 'faq', label: '六、常见问题' },
  { id: 'swagger', label: '七、与 Swagger 边界' },
]
const activeSection = ref('overview')

const reqHeaders = [
  { name: 'Content-Type', required: '是', desc: 'application/json（上传 skill 为 multipart/form-data）' },
  { name: 'Authorization', required: '二选一', desc: '网页登录态：Bearer <token>' },
  { name: 'X-Access-Key', required: '二选一', desc: 'ak/sk 调用：访问密钥（与 Authorization 二选一）' },
  { name: 'X-Timestamp', required: 'ak/sk 必填', desc: '毫秒时间戳，与 X-Access-Key 配套' },
  { name: 'X-Nonce', required: 'ak/sk 必填', desc: '单次随机串，单次有效（防重放）' },
  { name: 'X-Signature', required: 'ak/sk 必填', desc: 'HMAC-SHA256 签名（签名串见「四、鉴权与调用」）' },
]

const respEnvelope = `{
  "code": 0,            // 0 成功；非 0 为业务/系统错误码
  "message": "ok",
  "data": { },          // 业务数据；分页接口形如 { list, total, page, page_size }
  "trace_id": "..."     // 链路追踪 ID，排错时提供
}`

const errorCodes = [
  { code: '40000', name: '业务错误（BizError）', scene: '参数 / 业务校验不通过' },
  { code: '40100', name: '未认证（UnauthorizedError）', scene: '缺 / 错令牌或 ak/sk 签名校验失败' },
  { code: '40300', name: '无权限（ForbiddenError）', scene: '非目标空间成员 / 角色不足' },
  { code: '40400', name: '资源不存在（NotFoundError）', scene: '指定 id / code 不存在 / 已删除 / 已下架' },
]

const pyTemplate = `import hashlib
import hmac
import time
import uuid

import requests

ACCESS_KEY = "你的 access_key"
SECRET_KEY = "你的 secret_key（仅本地保存，不上传）"
BASE_URL = "http://<平台地址>/api/v1"


def sign(method: str, path: str, timestamp: str, nonce: str) -> str:
    """构造 HMAC-SHA256 签名：METHOD\\nPATH\\nTIMESTAMP\\nNONCE（PATH 不含 query）"""
    message = f"{method}\\n{path}\\n{timestamp}\\n{nonce}"
    return hmac.new(SECRET_KEY.encode("utf-8"), message.encode("utf-8"), hashlib.sha256).hexdigest()


def call_api(method: str, path: str, *, params=None, json=None, files=None):
    timestamp = str(int(time.time() * 1000))  # 毫秒
    nonce = uuid.uuid4().hex               # 单次有效
    headers = {
        "X-Access-Key": ACCESS_KEY,
        "X-Timestamp": timestamp,
        "X-Nonce": nonce,
        "X-Signature": sign(method, path, timestamp, nonce),
    }
    url = BASE_URL + path
    resp = requests.request(method, url, headers=headers, params=params, json=json, files=files)
    return resp.json()  # 统一响应信封 {"code","message","data","trace_id"}


# 示例 1：上传 skill（multipart/form-data）
with open("my_skill.zip", "rb") as f:
    r = call_api("POST", "/b08/skills",
                 files={"file": f},
                 data={"name": "demo-skill", "is_public": "1"})

# 示例 2：获取某场景下的任务列表（带分页）
r = call_api("GET", "/b04/scenarios/123/tasks", params={"page": 1, "page_size": 20})
`

const apiBlocks = [
  {
    id: 'b08',
    tag: 'b08 skill',
    scene: '脚本自动上传 / 下载 skill',
    apis: [
      {
        name: 'POST /api/v1/b08/skills',
        desc: '上传 skill（公开 / 私有）',
        input: 'form：name(名称,必填,平台唯一)、intro(简介,可选)、is_public(1/0)、file(.zip,≤50MB)',
        output: 'data = { skill_code, name, is_public, created_at }',
      },
      {
        name: 'GET /api/v1/b08/skills/{skill_code}/download',
        desc: '按 code 下载 skill 包（二进制流）',
        input: 'path：skill_code',
        output: 'application/zip 文件流；失败返回错误码（公开任意下载，私有仅作者/L0）',
      },
    ],
  },
  {
    id: 'b04',
    tag: 'b04 任务迁移（含台账）',
    scene: '自动刷新 / 更新任务视图',
    apis: [
      {
        name: 'GET /api/v1/b04/scenarios/{scenario_id}/tasks',
        desc: '获取某场景下的任务列表（支持分页 / 筛选）',
        input: 'path：scenario_id；query：page, page_size, status?(可选)',
        output: 'data = { list:[{ id, task_name, project_name, status, ... }], total, page, page_size }',
      },
      {
        name: 'POST /api/v1/b04/tasks/{task_id}/status',
        desc: '更新任务状态（状态流转，需对应角色）',
        input: 'path：task_id；json：{ status, remark?(可选) }',
        output: 'data = { id, status, updated_at }',
      },
      {
        name: 'PUT /api/v1/b04/tasks/{task_id}/tags',
        desc: '为任务打标 / 改标（b06 标签）',
        input: 'path：task_id；json：{ tag_codes: [] }',
        output: 'data = { id, tag_codes: [] }',
      },
    ],
  },
  {
    id: 'b03',
    tag: 'b03 数据迁移',
    scene: '自动补录迁移过程记录',
    apis: [
      {
        name: 'POST /api/v1/b03/table-items/{item_id}/records',
        desc: '为库表清单项补录迁移过程记录',
        input: 'path：item_id；json：{ stage, content, operator?(可选) }',
        output: 'data = { id, table_item_id, stage, content, created_at }',
      },
    ],
  },
  {
    id: 'b07',
    tag: 'b07 血缘',
    scene: '脚本批量入库血缘',
    apis: [
      {
        name: 'POST /api/v1/b07/lineages/import',
        desc: '批量导入血缘关系（节点 / 边）',
        input: 'json：{ space_id, nodes:[...], edges:[...] }',
        output: 'data = { imported, skipped }',
      },
    ],
  },
]

function scrollTo(id: string) {
  const el = document.getElementById(id)
  if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' })
  activeSection.value = id
}

let observer: IntersectionObserver | null = null
onMounted(() => {
  const sections = toc.map((t) => document.getElementById(t.id)).filter(Boolean) as HTMLElement[]
  observer = new IntersectionObserver(
    (entries) => {
      for (const e of entries) {
        if (e.isIntersecting) activeSection.value = e.target.id
      }
    },
    { rootMargin: '-10% 0px -80% 0px' }
  )
  sections.forEach((s) => observer?.observe(s))
})

onBeforeUnmount(() => observer?.disconnect())

async function copy(text: string) {
  try {
    await navigator.clipboard.writeText(text)
    ElMessage.success('已复制')
  } catch {
    ElMessage.warning('复制失败，请手动选择')
  }
}
</script>

<style scoped>
.intro {
  margin-bottom: 16px;
  line-height: 1.6;
}

.layout {
  display: flex;
  gap: 20px;
  align-items: flex-start;
}

.toc {
  position: sticky;
  top: 16px;
  flex: 0 0 160px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 12px;
  background: var(--color-page-bg);
  border: 1px solid var(--color-border);
  border-radius: var(--el-border-radius-base);
}

.toc-title {
  font-size: 12px;
  color: var(--color-text-muted);
  margin-bottom: 6px;
}

.toc-link {
  font-size: 13px;
  color: var(--color-text-regular);
  text-decoration: none;
  padding: 4px 8px;
  border-radius: 6px;
  white-space: nowrap;
}

.toc-link:hover {
  background: #eef4ff;
  color: var(--el-color-primary);
}

.toc-link.active {
  background: #eef4ff;
  color: var(--el-color-primary);
  font-weight: 600;
}

.toc-keys {
  margin-top: 8px;
  justify-content: flex-start;
}

.content {
  flex: 1;
  min-width: 0;
}

.block {
  margin-bottom: 26px;
  scroll-margin-top: 16px;
}

.block-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--color-text-primary);
  margin: 0 0 12px;
  padding-left: 10px;
  border-left: 3px solid var(--el-color-primary);
}

.sub-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text-primary);
  margin: 16px 0 8px;
}

p {
  font-size: 13px;
  line-height: 1.7;
  color: var(--color-text-regular);
  margin: 0 0 10px;
}

.tip-list,
.note {
  font-size: 13px;
  color: var(--color-text-regular);
  line-height: 1.7;
}

.note {
  margin-top: 10px;
  color: var(--color-text-muted);
}

.tbl {
  margin: 8px 0 4px;
}

.steps {
  margin: 4px 0 16px;
}

.warn {
  margin: 12px 0;
}

.mt {
  margin-top: 6px;
}

.code-wrap {
  border: 1px solid var(--color-border);
  border-radius: 6px;
  overflow: hidden;
  margin: 8px 0;
}

.code-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 10px;
  background: #f3f6fb;
  font-size: 12px;
  color: var(--color-text-muted);
  border-bottom: 1px solid var(--color-border);
}

.code-block {
  margin: 0;
  padding: 12px 14px;
  background: #1f2d3d;
  color: #e6edf3;
  font-family: var(--el-font-family-mono, monospace);
  font-size: 12px;
  line-height: 1.6;
  overflow-x: auto;
  white-space: pre;
}

.mono {
  font-family: var(--el-font-family-mono, monospace);
  font-size: 12px;
  color: var(--el-color-primary);
  background: var(--color-page-bg);
  padding: 1px 4px;
  border-radius: 4px;
}

.api-block {
  margin-bottom: 14px;
}

.faq :deep(.el-collapse-item__header) {
  font-size: 13px;
}
</style>
