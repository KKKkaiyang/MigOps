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

## 状态
- 暂未沉淀技能，待首个模块（b01）稳定后提取 `b01-scaffold`。
