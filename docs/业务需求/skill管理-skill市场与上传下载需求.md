# 迁移管家（MigOps）skill 管理 — skill 市场与上传下载需求

> 文档版本：V1.0 ｜ 编写日期：2026-10-24 ｜ 状态：需求确认版（已交互确认关键决策 D1~D6）
> 适用范围：平台级 skill 市场（`b08`），覆盖 skill 市场展示、手工/REST API 上传、公开/私有可见性、web/REST API 下载，以及用户自助 ak/sk 密钥管理
> 配套文档：[`迁移管家平台-完整需求文档.md`](./迁移管家平台-完整需求文档.md)（平台总 BRD）、根目录 [`CODEBUDDY.md`](../../CODEBUDDY.md)（开发规范：库表命名 §3 / 前后端分层 §5 / §6.4 设计令牌）

---

## 1. 概述

### 1.1 背景与目标
平台在多个大数据迁移项目中沉淀了大量可复用的 skill（方法论 / 自动化能力），但目前缺少统一的共享渠道。本需求建设**平台级 skill 市场**，让所有登录用户都能：

- 上传自己在项目中沉淀的 skill（手工或 REST API），并选择是否公开；
- 浏览、搜索、下载他人公开的 skill，形成平台级能力复用；
- 为后续「skill 人机对话方式」自动上传/下载预留并完整定义 REST API，采用 ak/sk 密钥鉴权。

skill 文件当前存储到服务器本地指定目录，存储层做抽象以便后续对接对象存储。

### 1.2 范围
- **涉及前端**：新增「skill 市场」全局一级菜单、上传对话框、我的 skill 列表、个人中心 / API 密钥页。
- **涉及后端**：新增 `b08` skill 相关接口（市场列表 / 上传 / 下载 / 详情 / 下架 / 删除）、ak/sk 密钥接口；存储落地本地目录（抽象存储层）。
- **涉及库**：公共库 `mig_common_db`（`b08_` 前缀表 + `common_user_api_key`）。
- **不在本范围**：skill 内容在线预览/编辑、版本历史回溯、skill 评价/评分体系（后续迭代）。

### 1.3 术语
| 术语 | 含义 |
| --- | --- |
| skill（技能） | 一段可复用的迁移方法论 / 自动化能力，含 `SKILL.md` 及资源，以 zip 包形式上传 / 下载 |
| skill 市场 | 平台级全局的 skill 展示与获取入口，所有登录用户可见公开 skill |
| 公开 / 私有 | skill 可见性：公开 = 全员市场可见可下载；私有 = 仅上传者本人与 L0 可见可下载（D4） |
| ak/sk | AccessKey / SecretKey 密钥对，用于 REST API 的 HMAC 签名鉴权 |
| 使用热度 | 以累计下载次数衡量 |

---

## 2. 需求总览

| 编号 | 需求 | 优先级 | 关键约束（已确认） |
| --- | --- | --- | --- |
| SK-01 | skill 市场平铺展示 | P1 | 平台级全局，公开 skill 全员可见；卡片含名称 / 简介（截断）/ 热度 |
| SK-02 | 手工上传 skill | P1 | 任意登录用户可上传；可选公开 / 私有；本地目录存储 |
| SK-03 | 私有 skill 可见性 | P1 | 私有仅上传者 + L0 可见 / 可下载（D4） |
| SK-04 | web 下载 skill | P1 | 公开 → 全员；私有 → 上传者 + L0；下载计数 +1 |
| SK-05 | 个人中心 ak/sk 自管理 | P1 | 每用户自助生成 / 查看 / 吊销；解决「用户管理仅 L0」冲突（D2） |
| SK-06 | REST API 上传 / 下载（ak/sk 鉴权） | P1 | 完整定义并实现（D3）；HMAC 签名鉴权 |
| SK-07 | 存储策略 | P2 | 本地目录 + 抽象存储层，后续切对象存储（D5） |

---

## 3. SK-01 skill 市场（展示）

### 3.1 功能描述
「skill 市场」以 panel/card 网格平铺展示所有**公开** skill，不展示私有 skill。市场为平台级能力，与迁移空间隔离模型解耦（D1）。

### 3.2 交互与界面
- **入口**：顶部全局导航一级菜单「skill 市场」（位于空间视图之外，平台级，所有登录用户可见）。
- **卡片字段**：skill 名称、简介（超过 60 字显示「…」，鼠标 hover 或点击查看全文弹层）、使用热度（下载次数，图标 + 数字）、作者、公开 / 私有标签、下载按钮。
- **筛选 / 搜索**：按名称、作者、标签模糊搜索；排序（热度 / 最新上传）。
- **视觉（对齐 `CODEBUDDY.md` §6.4）**：卡片表面 `#ffffff`、边框 `#d7dee7`、圆角 `8px`、轻阴影 `0 2px 8px rgba(0,0,0,0.04)`；下载主按钮主色 `#1a73e8`；标签胶囊圆角 `10px`、字号 `11px`（`white-space:nowrap`）——公开 = 项目紫 `#f0e8ff`/`#6a3fb5`，私有 = 中性灰 `#bdc3c7`。
- **结果反馈**：下载成功底部居中深色 Toast（`rgba(31,45,61,0.92)` 白字，约 3.5s）。

### 3.3 权限与可用性
- 全部登录用户（L0 / L1 / L2）可见公开 skill 并下载，与总文档 §3.2 角色模型一致。
- 市场为平台级能力，**不受空间隔离约束**（D1）。

### 3.4 后端接口
```
GET /api/v1/b08/skills/market
鉴权：登录态（require_login）
参数：keyword(可选), sort(heat|latest), page, page_size
响应：{ code, message, data:{ list:[{ skill_code, name, intro, download_count, is_public, author_name, updated_at }], total, page, page_size } }
```

---

## 4. SK-02 手工上传 skill

### 4.1 功能描述
任意登录用户可从市场页上传自己在项目中沉淀的 skill：填写元信息、选择是否公开、上传 zip 包；提交后系统保存元数据并将文件落盘，作者记为当前用户。

### 4.2 交互与界面
- **入口**：市场页「上传 skill」按钮 → 对话框。
- **字段**：名称（必填，平台级唯一）、简介（必填，textarea，≤500 字）、是否公开（switch，默认公开）、zip 文件（必填，拖拽上传区）。
- **校验**：名称全局唯一；zip 大小上限默认 50MB（可配置）；建议 zip 内含 `SKILL.md`（不强制）。
- **视觉（对齐 §6.4）**：对话框蓝底头部 `#1a73e8` 白字、圆角 `10px`、遮罩 `rgba(20,30,45,0.45)`；文件上传区虚线边框 `#c2ccd8`、圆角 `6px`、浅灰底 `#fafbfc`，拖拽悬停变蓝边 + 浅蓝底 `#eef4ff`（§6.4.6）。
- **结果反馈**：成功 Toast + 关闭对话框并刷新市场；失败提示具体原因。

### 4.3 后端接口
```
POST /api/v1/b08/skills
鉴权：登录态（require_login）
Content-Type：multipart/form-data
请求：name, intro, is_public(0/1), file(zip)
响应：{ code, message, data:{ skill_code } }
```

---

## 5. SK-03 私有 skill 可见性

- 私有（`is_public=0`）skill **不进入市场公开列表**，仅出现在上传者本人的「我的 skill」列表，以及 L0 的监管视图（D4）。
- 私有 skill 的下载权限同 SK-04（仅上传者本人与 L0）。
- 上传者可在「我的 skill」中对公开 skill 执行**下架**（状态置为「下架」）：下架后从市场移除，但仍可由本人管理与重新上架；删除为逻辑删除（保留记录）。

---

## 6. SK-04 web 下载 skill

```
GET /api/v1/b08/skills/{skill_code}/download
鉴权：登录态（require_login）+ 可见性校验
可见性：公开 → 全员；私有 → 仅 author_user_id 与 L0
行为：流式返回 zip 包；成功则 download_count +1（防重复计数：同一用户 5 分钟内重复下载不重复累加，可选）
失败：无权限 / 不存在 → 业务错误码 + 提示
```

---

## 7. SK-05 个人中心 ak/sk 自管理（D2）

### 7.1 功能描述
新增「个人中心 → API 密钥」页，每个登录用户可**自助**管理自己的 ak/sk 密钥对，用于 REST API 鉴权。该能力与既有「用户管理（仅 L0）」解耦，解决「用户管理仅 L0 可操作」与「所有用户可用 REST API」之间的冲突（D2）。

### 7.2 交互与界面
- **能力**：生成密钥对（access_key 随机生成，secret_key 随机生成**仅展示一次**，需用户复制保存）、列表（access_key 掩码显示、状态、最近使用时间）、启用 / 停用、吊销。
- **权限**：仅本人可访问与管理自身密钥（后端按当前登录用户过滤，禁止跨用户）。

### 7.3 后端接口
```
POST   /api/v1/common/users/me/api-keys        # 生成（返回 access_key + secret_key，secret 仅此一次明文）
GET    /api/v1/common/users/me/api-keys        # 列表（secret 掩码，含状态 / 最近使用时间）
DELETE /api/v1/common/users/me/api-keys/{id}   # 吊销（逻辑删除）
PATCH  /api/v1/common/users/me/api-keys/{id}   # 启用 / 停用
鉴权：登录态（仅本人）
```

> **归属说明（2026-10-24 补充）**：ak/sk 密钥能力已由《公共业务-aksk通用能力与接口开放需求》V1.0 提升为**平台级公共业务通用能力**（适用范围由仅 b08 扩展为 b03~b08），前端入口仍为本节「个人中心 → API 密钥」。本节仅描述其作为 skill REST API 鉴权的使用方式；密钥的管理与平台化定位以该文档及 BRD §4.5 / §9.10 为准。

---

## 8. SK-06 REST API 上传 / 下载（ak/sk 鉴权，D3）

### 8.1 鉴权方案（HMAC-SHA256 签名）
- **请求头**：`X-Access-Key`、`X-Timestamp`（毫秒）、`X-Nonce`、`X-Signature`。
- **待签字符串** = `HTTP方法 + "\n" + 请求路径 + "\n" + timestamp + "\n" + nonce + "\n" + bodySHA256`（无 body 时为固定占位）。
- **签名** = `HMAC-SHA256(secret_key, 待签字符串)` 的十六进制。
- **服务端校验**：access_key 存在且状态为启用；timestamp 与服务器偏差 ≤ 5 分钟（防重放）；nonce 在 5 分钟内不重复；签名一致。任一不通过返回 `401` 业务错误码。
- 鉴权通过后，REST API 操作归属为该 ak/sk 对应的用户（上传 author = 对应 user）。

### 8.2 接口
```
POST /api/v1/b08/skills/upload
      multipart/form-data：name, intro, is_public, file   # 同 SK-02，author = ak 对应 user
GET  /api/v1/b08/skills/{skill_code}/download             # 同 SK-04
GET  /api/v1/b08/skills                                   # 列举当前用户全部 skill（含私有）
鉴权：ak/sk 签名（SK-06.1），不再要求登录态 Cookie
```

---

## 9. SK-07 存储策略（D5）

- **默认本地目录**：环境变量 `SKILL_STORAGE_DIR`（默认 `<部署根>/data/skills/`），按 `skill_code/` 组织子目录，文件命名 `<version>.zip`。
- **抽象存储层**：定义 `StorageBackend` 接口，先实现本地磁盘后端；后续增加对象存储（COS / OSS）后端，业务层不感知切换。
- 文件元数据（路径、大小、版本）记录在 `b08_skill` 表，便于审计与迁移。

---

## 10. 数据模型（`mig_common_db`）

### 10.1 `b08_skill`（skill 主表）
| 字段 | 类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| `id` | BIGINT | PK，自增 | skill ID |
| `skill_code` | VARCHAR | 唯一、非空 | skill 编码（平台级唯一，如 `sk_xxxxxxxx`） |
| `name` | VARCHAR | 唯一、非空 | skill 名称 |
| `intro` | VARCHAR(500) | 可空 | 简介（市场截断展示） |
| `author_user_id` | BIGINT | 非空 | 上传者，关联 `common_user.id` |
| `is_public` | TINYINT(1) | 默认 1 | 是否公开：1 公开 / 0 私有 |
| `status` | ENUM | 默认 `上架` | 上架 / 下架 |
| `download_count` | INT | 默认 0 | 使用热度（累计下载次数） |
| `file_path` | VARCHAR | 非空 | 文件相对存储路径 |
| `file_size` | BIGINT | 可空 | 文件大小（字节） |
| `version` | VARCHAR | 默认 `1.0.0` | 版本 |
| 审计字段 | — | 必填 | `created_by` / `created_at` / `updated_by` / `updated_at` / `deleted_at`（逻辑删除） |

> 市场可见条件：`is_public = 1` 且 `status = 上架` 且 `deleted_at IS NULL`。

### 10.2 `common_user_api_key`（用户 API 密钥）
| 字段 | 类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| `id` | BIGINT | PK | 密钥 ID |
| `user_id` | BIGINT | 非空 | 关联 `common_user.id` |
| `access_key` | VARCHAR | 唯一、非空 | 访问标识（明文） |
| `secret_key_enc` | VARCHAR | 非空 | 密钥（加密存储，可逆，用于 HMAC 校验） |
| `status` | ENUM | 默认 `启用` | 启用 / 停用 |
| `last_used_at` | DATETIME | 可空 | 最近使用时间 |
| 审计字段 | — | 必填 | `created_by` / `created_at` / `updated_by` / `updated_at` / `deleted_at` |

---

## 11. 非功能性约束

### 11.1 统一响应与分层（沿用 CODEBUDDY.md §5）
- 接口统一返回 `{ code, message, data, trace_id }`；分页 `{ list, total, page, page_size }`。
- 后端按 router → service → repository → model 分层；跨层用 Pydantic Schema，禁止直接返回 ORM 对象。

### 11.2 界面视觉（沿用 CODEBUDDY.md §6.4）
- 主色 `#1a73e8`、危险红 `#e53935`、对话框圆角 `10px`、遮罩 `rgba(20,30,45,0.45)` 等设计令牌；状态 / 类型采用「颜色编码 + 文字标签」双标识。

### 11.3 安全与质量
- secret_key **加密存储、仅生成时展示一次**；签名校验防重放（时间戳 + nonce）。
- 权限越权由后端统一拦截（市场可见性、下载可见性、密钥仅本人）。
- 日志脱敏：禁止打印 secret_key 明文、文件内容；审计覆盖上传 / 下载 / 密钥生成吊销。

---

## 12. 验收标准

| 编号 | 验收项 | 通过条件 |
| --- | --- | --- |
| SK-01 | 市场展示 | 公开 skill 以卡片网格平铺，含名称 / 截断简介 / 热度；私有不出现；搜索 / 排序生效 |
| SK-02 | 手工上传 | 登录用户可上传 zip 并选择公开 / 私有；名称唯一校验、大小上限生效；文件落盘 |
| SK-03 | 私有可见性 | 私有 skill 仅上传者本人与 L0 可见 / 可下载；公开 skill 全员可见 |
| SK-04 | web 下载 | 公开全员可下、私有仅限上传者 + L0；下载成功计数 +1 |
| SK-05 | ak/sk 自管理 | 用户可自助生成（secret 仅一次明文）/ 列表 / 停用 / 吊销；仅本人可见自身密钥 |
| SK-06 | REST API | 持有效 ak/sk 可签名调用上传 / 下载；错误签名 / 过期时间戳 / 重复 nonce 被拒（401） |
| SK-07 | 存储 | 文件按 `SKILL_STORAGE_DIR/skill_code/version.zip` 落地；存储层接口可替换为对象存储 |

---

## 13. 已确认决策汇总（2026-10-24）

| 编号 | 议题 | 决策 |
| --- | --- | --- |
| D1 | skill 市场数据 / 入口归属层级 | 平台级全局：所有登录用户共享同一市场，库表存 `mig_common_db`，与迁移空间隔离解耦 |
| D2 | ak/sk 生成能力归属（与「用户管理仅 L0」冲突） | 放入「个人中心 → API 密钥」自助管理，每用户自管自身密钥，不依赖 L0 |
| D3 | REST API（ak/sk 上传 / 下载）实现程度 | 完整定义接口形态、HMAC 鉴权方案与请求响应，并随市场功能一并实现 |
| D4 | 私有 skill 可见 / 下载范围 | 仅上传者本人 + L0 可见 / 可下载（非仅本人） |
| D5 | skill 文件存储策略 | 本地指定目录 + 抽象 `StorageBackend`，后续对接对象存储 |
| D6 | 市场可见状态模型 | 可见条件 = `is_public=1` 且 `status=上架` 且未逻辑删除；下架后仍可由本人管理 |

> 决策均经交互式确认（AskUserQuestion）。D2 为对既有「用户管理仅 L0」规则的有意偏离（将 API 密钥能力下沉到个人中心），理由：REST API 面向所有登录用户，密钥须自助获取。

---

## 14. 修订记录
| 版本 | 日期 | 说明 |
| --- | --- | --- |
| V1.0 | 2026-10-24 | 基于需求描述整体优化，交互确认关键决策（D1~D6）后形成独立需求文档 |
