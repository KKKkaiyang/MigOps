# 迁移管家（MigOps）开发规范

> 文档版本：V1.0 ｜ 编写日期：2026-10-21
> 适用范围：迁移管家平台全部前后端代码、文档、脚本与技能
> 配套文档：业务需求文档（BRD，见仓库根目录 [`迁移管家平台业务需求文档.md`](../../迁移管家平台业务需求文档.md)）

---

## 1. 项目概述

| 项 | 内容 |
| --- | --- |
| 项目名称 | 迁移管家 |
| 项目简称 | MigOps |
| 项目定位 | 面向公有云大数据迁移项目的管理平台（迁移空间为隔离单元） |
| 后端语言 | Python |
| 数据源 | MySQL / StarRocks（可切换） |
| 前端框架 | Vue.js（Vue 3） |

业务全流程：`需求调研 → 元数据/数据迁移 → 任务迁移 → 数据校验 → 客户验收`。
平台以「迁移空间」为隔离单元，将全流程标准化、线上化、可沉淀。

---

## 2. 项目结构

```
MigOps/
├── code/                 # 项目代码目录
│   ├── frontend/         # 前端代码（Vue 3 + Vite）
│   └── backend/          # 后端代码（Python）
├── docs/                 # 文档目录（规范、设计、BRD 引用）
├── skills/               # 当前项目所有 skill 沉淀
├── tools/                # 手动调用的 Python 工具包
└── outputs/              # 所有要导出的清单/产物
```

约定：
- 每个目录保持单一职责，不混放无关内容。
- `skills/` 与 `tools/` 区别：**skills** 是可复用的方法论/自动化能力（含 SKILL.md）；**tools** 是手动执行的脚本工具（如批量导出、模板校验）。
- `outputs/` 仅存放最终交付物，按日期或模块分子目录，如 `outputs/2026-10-21/空间清单.xlsx`。

---

## 3. 库表命名规范

### 3.1 库名
| 类型 | 命名 | 说明 |
| --- | --- | --- |
| 公共业务库 | `mig_common_db` | 跨空间共享的元数据、标签、字典等 |
| 项目空间库 | `mig_<项目名称>_db` | 每个迁移空间独立库，实现数据隔离 |

> 公共业务表统一使用 `common_` 前缀，归属 `mig_common_db`。

### 3.2 表名前缀
| 前缀 | 模块 | 说明 |
| --- | --- | --- |
| `common_` | 公共业务 | 公共业务相关表 |
| `b01_` | 项目空间管理 | 迁移空间、成员、角色 |
| `b02_` | 项目资料管理 | 资料索引、模板、完整度 |
| `b03_` | 数据迁移管理 | 数据迁移场景、库表清单、迁移历史 |
| `b04_` | 任务迁移管理 | 任务迁移场景、任务台账、输出表、校验记录 |
| `b05_` | 数据校验管理 | 校验规则、校验结果、问题排查 |
| `b99_` | 统计分析管理 | 空间看板、统计聚合 |

### 3.3 字段约定
- 主键统一使用 `id`（BIGINT 自增）或业务唯一编码（如 `space_code`）。
- 所有业务表必含审计字段：`created_by`、`created_at`、`updated_by`、`updated_at`；逻辑删除用 `deleted_at`（NULL 表示未删）。
- 状态字段统一使用 `*_status` 命名，取值见各模块状态机。
- 时间字段统一 `xxx_at`（datetime）；日期字段 `xxx_date`（date）。
- 枚举/字典存储编码，展示名由字典表或代码常量映射。

---

## 4. 命名规范（默认约定，待确认）

> 以下为基于技术栈给出的**默认约定**，落地前可调整。

### 4.1 后端（Python）
| 对象 | 规范 | 示例 |
| --- | --- | --- |
| 变量/函数 | `snake_case` | `create_space()`、`space_list` |
| 类 | `PascalCase` | `SpaceService`、`SpaceModel` |
| 常量 | `UPPER_SNAKE_CASE` | `DEFAULT_PAGE_SIZE` |
| 模块文件 | `snake_case.py` | `b01_space.py`、`database.py` |
| 包 | `snake_case` | `app/models`、`app/routers` |
| API 路径 | `/api/v1/{module}/{resource}` | `/api/v1/b01/spaces`、`/api/v1/b04/tasks` |
| 配置项 | `UPPER_SNAKE_CASE`（环境变量） | `DB_TYPE`、`MYSQL_URL` |

### 4.2 前端（Vue 3）
| 对象 | 规范 | 示例 |
| --- | --- | --- |
| 组件 | `PascalCase.vue` / 文件 `kebab-case.vue` | `SpaceList.vue` |
| 变量/函数 | `camelCase` | `fetchSpaces()` |
| 常量/枚举 | `UPPER_SNAKE_CASE` 或 `camelCase` 常量对象 | `PAGE_SIZE` |
| 文件 | `kebab-case` | `space-list.vue`、`use-space.ts` |
| API 函数 | 按资源分组，`camelCase` | `spaceApi.list()` |
| 路由 name | `kebab-case` 或 `camelCase` | `space-list` |

### 4.3 通用
- Git 分支：`feature/<module>-<desc>`、`fix/<module>-<desc>`、`release/<version>`。
- 提交信息：`<type>(<module>): <desc>`，type ∈ {feat, fix, docs, refactor, test, chore}。
- 公共组件/工具前缀避免与业务命名冲突，统一放 `components/common`、`utils`。

---

## 5. 后端规范（默认约定，待确认）

### 5.1 技术选型
- **Web 框架**：FastAPI（异步、自带 OpenAPI、类型友好）。
- **ORM**：SQLAlchemy 2.0（支持 MySQL 与 StarRocks 双引擎，通过动态 engine 绑定切换）。
- **配置**：pydantic-settings，环境变量驱动；数据源切换由 `DB_TYPE=mysql|starrocks` 决定。
- **校验/序列化**：Pydantic v2（请求/响应模型分离）。
- **迁移**：Alembic（可选，MySQL 侧使用；StarRocks 侧 DDL 手工管理）。

### 5.2 分层架构
```
router（接口层）
   ↓ 调用
service（业务逻辑层）
   ↓ 调用
repository / dao（数据访问层，封装 SQLAlchemy session）
   ↓ 操作
model（ORM 模型，映射 b01~b99 表）
```
- 依赖注入：通过 FastAPI `Depends` 注入 `db session` 与当前用户/权限。
- 跨层数据用 Schema（Pydantic）传递，**禁止**把 ORM 对象直接返回给前端（需 `.dict()`/`from_orm` 转换）。

### 5.3 统一响应
所有接口返回统一结构：
```json
{ "code": 0, "message": "ok", "data": { }, "trace_id": "..." }
```
- `code=0` 成功；非 0 为业务/系统错误码。
- 分页返回 `{ "list": [], "total": 0, "page": 1, "page_size": 20 }`。

### 5.4 错误处理与日志
- 自定义异常（`BizError`/`NotFound`/`Forbidden`），由全局异常处理器统一转换为响应结构。
- 关键路径打印结构化日志（级别、模块、操作人、耗时），**禁止**打印明文密码/敏感字段。
- 审计：状态流转类操作必须记录操作人、时间、变更前/后（写入审计表或日志）。

### 5.5 数据源可切换设计
- `app/database.py` 提供 `get_engine()`，依据 `DB_TYPE` 返回 MySQL（pymysql）或 StarRocks（mysql+pymysql，分析型）引擎。
- 业务代码**不直接依赖具体方言**；差异点（如分页语法、特有函数）收敛到 repository 层适配。
- 公共库（`mig_common_db`）与空间库（`mig_<项目>_db`）通过 engine 路由区分。

---

## 6. 前端规范（默认约定，待确认）

### 6.1 技术选型
- **框架**：Vue 3（`<script setup>` 语法）+ Vite + TypeScript。
- **路由**：Vue Router 4（按模块 `b01~b05` 划分路由分组）。
- **状态**：Pinia。
- **UI 组件库**：Element Plus（表单/表格密集型后台首选，可后续替换）。
- **请求**：Axios 封装 `src/api/request.ts`，统一拦截响应结构、错误提示与登录态。

### 6.2 目录职责
```
src/
├── api/          # 接口封装，按模块 b01~b05 分文件
├── components/   # 通用组件（common/ 放公共组件）
├── views/        # 页面级组件，按模块分目录
├── router/       # 路由定义
├── store/        # Pinia 状态
├── types/        # TS 类型定义（与后端 Schema 对齐）
└── utils/        # 工具函数
```

### 6.3 编码约定
- 组件 ≤ 400 行，单文件内聚；超过则拆分为子组件。
- 页面数据获取放 `store` 或 `api` 调用，组件只负责渲染与交互。
- 列表页统一分页/筛选/导出交互模式，复用 `common` 表格组件。
- 样式 `scoped`，主题变量集中管理。

### 6.4 界面视觉风格规范

> 以下设计令牌（design tokens）提炼自 `tools/hrwx_lineage` 血缘可视化工具的实际前端实现，代表团队已形成的视觉语言。本项目前端（含 Element Plus 主题定制）应与之对齐，保持配色、圆角、间距、阴影与组件样式的统一。

#### 6.4.1 主题色板（Design Tokens）
| 角色 | 色值 | 说明 |
| --- | --- | --- |
| 主色 Primary | `#1a73e8`（hover `#1558b0`） | 按钮、链接、选中、高亮、主操作 |
| 页面背景 | `#eef2f7` | 应用整体底色（浅灰蓝） |
| 表面/卡片 | `#ffffff` | 头部、面板、卡片、对话框背景 |
| 头部底边框 | `#e3e9f0` | 顶部导航栏分隔线 |
| 文本主色 | `#1f2d3d` | 标题、正文重点 |
| 文本次色 | `#37475a` | 正文、标签 |
| 文本弱化 | `#8a96a3` / `#9aa7b5` | 辅助说明、占位、次级信息 |
| 成功 Success | `#188038` / `#27ae60` | 通过、正常态 |
| 警告 Warn | `#f2a100` / `#f1c40f` / `#b06a00` | 临时 / 待关注 / 微小差距 |
| 危险 Danger | `#e53935` / `#c62828` / `#e74c3c` | 错误、必填、不通过 |
| 中性 Neutral | `#bdc3c7` | 未知 / 无数据 |
| 边框 Border | `#d7dee7` / `#c7d2e0` / `#e3e9f0` | 输入框、卡片、分隔 |

#### 6.4.2 语义配色（业务约定，必须遵循）
界面中的类型 / 状态一律采用颜色编码，并辅以文字标签，保证可辨识：

- **表类型**：正式表 = 蓝（填充 `#e8f0fe` / 描边 `#1a73e8`）；临时表 = 琥珀橙（填充 `#fef7e0` / 描边 `#f2a100`）；当前聚焦表 = 绿色描边 `#188038`。
- **血缘方向**：上游（数据流入）= 琥珀 `#c2a36b`；下游（数据流出）= 灰 `#9aa7b5`。
- **数据校验状态**：通过 = 绿 `#27ae60`；微小差距 = 黄 `#f1c40f`（深字 `#5a4b00`）；不通过 = 红 `#e74c3c`；未知 / 无 = 灰 `#bdc3c7`。
- **标签 / 徽标（Tag / Badge）**：正式表蓝底 `#e8f0fe`/`#1a73e8`、临时表橙 `#fef7e0`/`#b06a00`、工作流绿 `#e6f4ea`/`#188038`、项目紫 `#f0e8ff`/`#6a3fb5`、任务类型青 `#e0f2fe`/`#075985`；统一圆角胶囊 `10px`、字号 `11px`、`white-space: nowrap`。

#### 6.4.3 字体
- 系统字体栈：`-apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei", Arial, sans-serif`（全局默认，正文 / 界面文字）。
- 等宽字体：`ui-monospace, Menlo, Consolas, monospace`（表名、脚本路径、代码型内容）。

#### 6.4.4 圆角与间距
- 圆角阶梯：`4px`（状态方块 / 小点）、`6px`（输入框 / 按钮 / 下拉 / 提示框）、`8px`（搜索框 / 卡片 / 面板 / 下拉列表）、`10px`（对话框 / 详情面板 / 徽标胶囊）。
- 间距基准（阶梯）：`4 / 6 / 8 / 10 / 12 / 16 / 20px`；头部高度 `64px`；对话框内边距 `16px 18px`。
- 字号阶梯：正文 `13px`、次要 `12px`、辅助 `11px`、标题 `15~18px`、空态 `16px`。

#### 6.4.5 阴影
- 轻：`0 2px 8px rgba(0,0,0,0.04)`（头部）。
- 中：`0 8px 24px rgba(0,0,0,0.12 ~ 0.18)`（浮层、下拉、卡片）。
- 重：`0 16px 48px rgba(0,0,0,0.25)`（对话框）。

#### 6.4.6 组件样式模式
- **对话框 Dialog**：固定遮罩 `rgba(20,30,45,0.45)` + 居中白卡（圆角 `10px`、阴影 `0 16px 48px`）；头部蓝底 `#1a73e8` 白字（标题 `15px` bold + 右侧关闭 `✕`）；点击遮罩关闭（`@click.self`）；最大宽高 `calc(100vw - 32px)` / `calc(100vh - 48px)`；正文 `overflow-y:auto`。
- **轻提示 Toast**：固定底部居中，深色底 `rgba(31,45,61,0.92)` + 白字 + 圆角 `8px`，约 `3.5s` 自动消失。
- **弹窗内表格**：`border-collapse`，表头 `position: sticky` 吸顶 `#f3f6fb` 加粗，行底分割线 `#eef1f5`，字号 `12px`，长内容 `word-break: break-all`。
- **按钮**：主按钮 primary 蓝底 `#1a73e8` 白字（hover `#1558b0`）；次按钮 ghost 白底 + 灰边 `#d7dee7` + 文字 `#37475a`（hover 蓝边蓝字）；禁用态 `opacity:0.5` + `cursor:not-allowed`。
- **表单字段**：label `13px` `#37475a`；必填 `*` 红 `#e53935`；输入框边框 `#d7dee7` 圆角 `6px`，focus 描边 `#1a73e8`（搜索框带 `0 0 0 3px rgba(26,115,232,0.12)` 浅蓝阴影）。
- **提示框（warn / info）**：浅底 + 同色描边 + 深色字，圆角 `6px`（蓝 `#eef4ff`/`#c5dbff`/`#23527c`、琥珀 `#fff4e5`/`#ffd8a8`/`#9a5b00`）。
- **文件上传区**：虚线边框 `#c2ccd8` 圆角 `6px` 浅灰底 `#fafbfc`，拖拽悬停变蓝边 + 浅蓝底 `#eef4ff`。
- **右键 / 上下文菜单**：白底浮层、圆角 `8px`、轻阴影；标题灰字 + 下边线；菜单项 hover 蓝底 `#eef4ff` 蓝字 `#1a73e8`。

#### 6.4.7 层级（z-index）约定
画布控件 / 图例 `20` → 头部 `25` → 浮层 / 详情面板 `30~60`（详情面板 `30`、校验浮层 `40`、右键菜单 `50`、连线详情 `60`）→ 对话框遮罩 `1000` → Toast `1100`。新增浮层须按此梯度避让，避免遮挡。

---

## 7. 代码质量

- **函数单一职责**：单函数 < 200 行；文件内聚 < 2000 行。
- **避免深层嵌套**：控制嵌套深度 ≤ 4 层（用早返回/卫语句降低嵌套）。
- **错误处理与日志**：每个外部调用（DB、HTTP、文件 IO）必须有错误处理与日志。
- **避免过度设计**：保持简洁，不为未知需求提前抽象；YAGNI 原则。
- **可测试**：核心 service 与工具函数不依赖全局状态，便于单测。
- **一致性**：新增代码遵循本规范既有命名与分层，不引入第二种风格。

---

## 8. 待确认事项（评审结论）

> 以下问题已与负责人确认，结论如下。

1. 后端 Web 框架：**采用 FastAPI**（默认）。异步、自带 OpenAPI、类型友好。
2. 前端技术选型：**采用 TypeScript + Element Plus**（默认）。类型安全与后端 Pydantic Schema 对齐，表格/表单密集型后台首选。
3. `b99_` 统计分析落地时机：**二期落地**。一期先完成 b01~b05 核心流程，b99 看板/聚合留待二期。
4. 公共库与空间库的物理隔离策略：**同实例不同库**（默认）。公共库 `mig_common_db` 与空间库 `mig_<项目>_db` 位于同一数据库实例下不同库，通过 engine 路由区分，运维简单、成本低。
5. 第 4~6 章默认约定与团队习惯冲突情况：**无冲突，直接采用**。第 4~6 章标注的「默认约定」全部生效，无需调整。
