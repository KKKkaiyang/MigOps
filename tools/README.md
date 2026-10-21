# tools/ — 手动调用 Python 工具包

本目录存放迁移管家（MigOps）项目中**手动执行的 Python 工具脚本**（非服务常驻代码）。

## 约定
- 每个工具一个 `.py` 文件或子目录，文件头注明：用途、用法示例、依赖。
- 典型工具：
  - `export_space_list.py`：将空间清单导出为 `outputs/` 下 Excel。
  - `validate_excel_template.py`：校验导入的库表清单 / 任务台账模板格式。
  - `db_health_check.py`：按 `DB_TYPE` 检查 MySQL / StarRocks 连通性与表结构。
- 依赖统一在脚本内注明，优先使用仓库内虚拟环境，不污染全局。
- 执行产物放入 `outputs/`，不在本目录留输出文件。

## 状态
- 暂未放置工具，待后端模块稳定后补充。
