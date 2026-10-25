# skills/ — 项目技能沉淀

本目录存放迁移管家（MigOps）项目的**可复用技能与方法论**。

## 约定
- 每个技能一个独立子目录，必须包含 `SKILL.md`（技能说明与触发条件、执行流程、输入输出）。
- 技能应面向可复用的工程动作，例如：
  - `b01-scaffold`：按本仓库分层结构快速生成新模块（model/schema/service/router 四件套）。
  - `excel-template`：库表清单 / 任务台账的 Excel 模板校验与导入。
  - `db-switch`：MySQL / StarRocks 数据源切换验证。
- 命名：`{module}-{purpose}`，如 `b04-task-import`。
- 与 `tools/` 区别：skills 是「方法论 + 自动化流程」，tools 是「手动执行的脚本」。

## 自动加载（重要）
CodeBuddy Code 仅会自动加载 `.codebuddy/skills/` 下的技能，因此本目录作为**编写源**，通过软链映射到 `.codebuddy/skills/` 实现「进入项目即自动加载」：
- 每个技能（含 `SKILL.md` 的子目录）在 `.codebuddy/skills/` 下建立相对软链 `../../skills/<name>`。
- 新增技能后执行 `bash skills/link.sh` 即可重建全部软链（clone 后也需执行一次）。
- 进入项目后用 `/skills` 命令可查看已加载的 Project skills。

## 状态
- 暂未沉淀技能，待首个模块（b01）稳定后提取 `b01-scaffold`。

## 已沉淀技能
- **`frontend-dev`**：前端功能开发规范与标准流程（技术栈、命名、目录、视觉风格设计令牌 §4.2/6.4、Element Plus 主题对齐、列表+弹窗表单标准开发流程、交付自检清单）。当用户在 `code/frontend` 下新增/修改页面、组件、接口或需要遵循本项目视觉风格时触发。
- **`biz-req-gen`**：业务需求生成技能（碎片化需求文档 + 合并进总 BRD）。当用户以文本形式描述业务诉求/功能点、希望沉淀为独立需求文档并同步合并进 `迁移管家平台-完整需求文档.md` 时触发。覆盖需求采集、模块归类与冲突检测、交互式确认（AskUserQuestion）、文档生成与增量合并流程。
