---
name: frontend-dev
description: 迁移管家（MigOps）前端功能开发规范与标准流程。当用户在 code/frontend 下新增/修改页面、组件、接口封装、表单对话框、列表页，或需要遵循本项目的 Vue 3 + TypeScript + Element Plus 视觉风格（设计令牌 / 语义配色 / 圆角间距阴影 / z-index 层级）时使用。覆盖技术栈、命名、目录职责、视觉风格约束与「列表页 + 弹窗表单」标准开发流程。
---

# MigOps 前端功能开发（frontend-dev）

本技能沉淀迁移管家前端开发的**约束与标准流程**，用于在一个独立功能开发任务中保持一致性与视觉统一。所有规范以仓库 `CODEBUDDY.md` 第 4.2 / 6.1~6.4 节为权威来源，本文件为其面向「如何动手」的萃取。

适用场景：
- 新增/修改一个功能模块（b01~b05）的页面、组件、接口。
- 实现「列表 + 搜索 + 分页 + 弹窗表单」这类后台标准交互。
- 需要确保配色、圆角、阴影、层级与团队现有视觉语言（提炼自 `tools/hrwx_lineage`）一致。
- 自定义 Element Plus 主题以对齐主色与语义色。

---

## 1. 技术栈与目录

**技术栈**（不可偏离）：Vue 3（`<script setup>`）+ Vite + TypeScript + Vue Router 4 + Pinia + Element Plus + Axios。

```text
src/
├── api/          # 接口封装，按模块 b01~b05 分文件（已有示例 space.ts）
├── components/   # 通用组件（common/ 放公共组件）
├── router/       # 路由定义（按模块 b01~b05 分组）
├── store/        # Pinia 状态
├── types/        # TS 类型定义（与后端 Pydantic Schema 对齐）
├── utils/        # 工具函数
└── views/        # 页面级组件，按模块分目录（示例 views/space/SpaceList.vue）
```

- 路径别名 `@` → `src/`（`vite.config.ts` 已配置）。
- 请求封装统一走 `@/api/request.ts`：`baseURL='/api/v1'`，响应拦截器处理统一结构 `{code,message,data}`（`code!==0` 自动 `ElMessage.error`），并剥离 `data` 返回。
- 开发代理：`/api` → `http://127.0.0.1:8999`（见 `vite.config.ts`）。

## 2. 命名规范

| 对象 | 规范 | 示例 |
| --- | --- | --- |
| 组件 | `PascalCase.vue`，文件 `kebab-case.vue` | `SpaceList.vue` / `space-list.vue` |
| 变量/函数 | `camelCase` | `fetchSpaces()` |
| 常量/枚举对象 | `UPPER_SNAKE_CASE` 或 `camelCase` 常量对象 | `PAGE_SIZE` |
| 文件 | `kebab-case` | `space-list.vue`、`use-space.ts` |
| API 函数 | 按资源分组，`camelCase` | `spaceApi.list()`（实践中 `listSpaces`） |
| 路由 name | `kebab-case` 或 `camelCase` | `space-list` |
| 后端接口路径 | `/api/v1/{module}/{resource}` | `/api/v1/b01/spaces`、`/api/v1/b04/tasks` |

> 后端接口路径前缀 `b01~b05` 与前端 `api/` 分文件、路由分组一一对应。新增模块先确认所属 `b0x` 前缀。

## 3. 编码约定

- 组件 ≤ 400 行，超过拆分为子组件。
- 页面数据获取优先放 `store`（Pinia）或视图内调用；`api/` 只做请求封装，不含业务逻辑。
- 列表页统一「搜索 + 表格 + 分页 + 弹窗表单」交互，复用 Element Plus 组件。
- 样式 `scoped`；跨组件复用的主题变量集中管理（见 §5）。
- 与后端 Schema 对齐：在 `types/` 定义接口类型，分页统一 `PageData<T> { list, total, page, page_size }`。

## 4. 视觉风格约束（必须遵循）

> 以下设计令牌提炼自 `tools/hrwx_lineage` 血缘工具，代表团队已形成的视觉语言。Element Plus 主题须据此定制，**禁止**私自引入第二套配色/圆角体系。

### 4.1 主题色板（Design Tokens）
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

### 4.2 语义配色（业务约定）
类型 / 状态一律**颜色编码 + 文字标签**双标识，保证可辨识：
- **表类型**：正式表 = 蓝（填充 `#e8f0fe`/描边 `#1a73e8`）；临时表 = 琥珀橙（填充 `#fef7e0`/描边 `#f2a100`）；聚焦表 = 绿描边 `#188038`。
- **血缘方向**：上游（流入）= 琥珀 `#c2a36b`；下游（流出）= 灰 `#9aa7b5`。
- **数据校验状态**：通过 = 绿 `#27ae60`；微小差距 = 黄 `#f1c40f`（深字 `#5a4b00`）；不通过 = 红 `#e74c3c`；未知/无 = 灰 `#bdc3c7`。
- **标签/徽标**：正式表蓝、临时表橙、工作流绿 `#e6f4ea`/`#188038`、项目紫 `#f0e8ff`/`#6a3fb5`、任务类型青 `#e0f2fe`/`#075985`；统一胶囊圆角 `10px`、字号 `11px`、`white-space:nowrap`。

### 4.3 字体
- 系统字体栈：`-apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei", Arial, sans-serif`。
- 等宽（表名/脚本路径/代码）：`ui-monospace, Menlo, Consolas, monospace`。

### 4.4 圆角与间距
- 圆角阶梯：`4px`（状态方块/小点）、`6px`（输入框/按钮/下拉/提示框）、`8px`（卡片/面板/下拉列表）、`10px`（对话框/详情面板/徽标胶囊）。
- 间距基准：`4/6/8/10/12/16/20px`；头部高度 `64px`；对话框内边距 `16px 18px`。
- 字号阶梯：正文 `13px`、次要 `12px`、辅助 `11px`、标题 `15~18px`。

### 4.5 阴影
- 轻 `0 2px 8px rgba(0,0,0,0.04)`（头部）；中 `0 8px 24px rgba(0,0,0,0.12~0.18)`（浮层/卡片）；重 `0 16px 48px rgba(0,0,0,0.25)`（对话框）。

### 4.6 组件样式模式
- **对话框**：遮罩 `rgba(20,30,45,0.45)` + 居中白卡（圆角 `10px`、阴影重）；头部蓝底 `#1a73e8` 白字（标题 `15px` bold + 关闭 `✕`）；点击遮罩可关闭；最大宽高 `calc(100vw-32px)`/`calc(100vh-48px)`。
- **轻提示 Toast**：底部居中，深色底 `rgba(31,45,61,0.92)` + 白字 + 圆角 `8px`，约 `3.5s` 自动消失（优先用 `ElMessage`）。
- **表格**：`border-collapse` 风格；表头吸顶 `#f3f6fb` 加粗；行底分割线 `#eef1f5`；字号 `12px`；长内容 `word-break:break-all`。
- **按钮**：主 `primary` 蓝底白字（hover `#1558b0`）；次 `ghost` 白底灰边 `#d7dee7` 文字 `#37475a`（hover 蓝边蓝字）；禁用 `opacity:0.5`。
- **表单字段**：label `13px` `#37475a`；必填 `*` 红 `#e53935`；输入框边框 `#d7dee7` 圆角 `6px`，focus 描边 `#1a73e8`。
- **提示框（warn/info）**：浅底 + 同色描边 + 深色字，圆角 `6px`（蓝 `#eef4ff`/`#c5dbff`/`#23527c`、琥珀 `#fff4e5`/`#ffd8a8`/`#9a5b00`）。
- **文件上传区**：虚线边框 `#c2ccd8` 圆角 `6px` 浅灰底 `#fafbfc`，拖拽悬停变蓝边 + 浅蓝底 `#eef4ff`。
- **右键/上下文菜单**：白底浮层、圆角 `8px`、轻阴影；菜单项 hover 蓝底 `#eef4ff` 蓝字 `#1a73e8`。

### 4.7 z-index 层级
画布控件/图例 `20` → 头部 `25` → 浮层/详情面板 `30~60` → 对话框遮罩 `1000` → Toast `1100`。新增浮层须按梯度避让，避免遮挡。

## 5. Element Plus 主题对齐

在 `src/styles/theme.css`（或 `main.ts` 引入）覆盖 Element Plus CSS 变量，使组件默认配色与 §4 一致：

```css
:root {
  --el-color-primary: #1a73e8;
  --el-color-primary-light-3: #4d92ee;
  --el-color-primary-light-5: #8fb6f3;
  --el-color-primary-light-7: #c2d6f8;
  --el-color-primary-light-8: #d8e5fb;
  --el-color-primary-light-9: #eef4ff;
  --el-color-primary-dark-2: #1558b0;
  --el-border-radius-base: 6px;
  --el-border-radius-small: 4px;
  --el-color-success: #188038;
  --el-color-warning: #f2a100;
  --el-color-danger: #e53935;
  --el-color-info: #37475a;
  --el-text-color-primary: #1f2d3d;
  --el-text-color-regular: #37475a;
  --el-border-color: #d7dee7;
}
```

- 主色按钮直接用 `<el-button type="primary">` 即自动采用 `--el-color-primary`。
- 自定义徽标/标签用 §4.2 的浅底深字配色（`bg + color`）。
- 涉及校验状态、表类型等语义色时，**必须**使用 §4.2 规定色值并叠加文字标签。

## 6. 标准开发流程（列表 + 弹窗表单）

以新增一个 `b0x` 模块为例，参照 `views/space/SpaceList.vue` + `api/space.ts`：

1. **类型**：在 `src/types/` 定义响应接口与 `PageData<T>`（复用已有泛型）。
2. **接口**：在 `src/api/` 新增 `{module}.ts`，导出 `listXxx/getXxx/createXxx/...`，路径 `/api/v1/{b0x}/{resource}`，统一返回 `PageData<T>` 或实体。
3. **页面**：在 `src/views/{module}/` 新增页面组件（`<script setup lang="ts">`）。
   - 顶部 `el-card` + `header`（标题 + 「新建」`type="primary"` 按钮）。
   - 工具栏：`el-input`（搜索）+ `el-button type="primary"`（查询）。
   - 表格：`el-table border v-loading` + `el-table-column`；底部 `el-pagination`。
   - 弹窗：`el-dialog`（标题、宽 `480px`）+ `el-form label-width`（必填项用 `required` 角标红 `*`）+ footer 取消/确定（`type="primary"`、`:loading`）。
4. **交互**：`ref` 持有列表/分页/loading/弹窗状态；`load()` 用 `try/finally` 管理 `loading`；提交前校验必填（`ElMessage.warning`），成功后 `ElMessage.success` 并重新 `load()`。
5. **路由**：在 `src/router/index.ts` 注册路由（name `kebab-case`，按模块分组）。
6. **视觉自检**：对照 §4 检查主色、圆角（`6px` 输入/按钮、`10px` 弹窗）、间距（`12px` 表格上间距、`8px` 工具栏 gap）、语义色、z-index 是否一致；确认未引入第二套配色。
7. **校验**：`npm run build`（含 `vue-tsc` 类型检查）通过后再交付。

## 7. 自检清单（交付前）

- [ ] 命名符合 §2（组件/文件/变量/路由）。
- [ ] 接口路径带 `/api/v1/{b0x}/` 前缀，返回结构含 `code/data`。
- [ ] 业务数据获取在 `store` 或视图内，未塞进 `api/`。
- [ ] 主色为 `#1a73e8`，语义色取自 §4.2；状态/类型有文字标签。
- [ ] 圆角/间距/阴影符合 §4.4~4.6；未引入新配色体系。
- [ ] 浮层 z-index 不破坏 §4.7 梯度。
- [ ] 组件 ≤ 400 行；样式 `scoped`。
- [ ] `npm run build` 类型检查通过。
