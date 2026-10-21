# MigOps 后端（Python / FastAPI）

## 技术栈
- Web: FastAPI（异步、自带 OpenAPI）
- ORM: SQLAlchemy 2.0（MySQL / StarRocks 双数据源可切换）
- 配置: 环境变量（见 `app/config.py`）

## 数据源切换
通过设置环境变量 `DB_TYPE` 切换：
- `DB_TYPE=mysql`      → 连接 `MYSQL_URL`
- `DB_TYPE=starrocks` → 连接 `STARROCKS_URL`（StarRocks 兼容 MySQL 协议）

两者均经 pymysql 驱动，业务代码不感知具体方言，差异收敛在 repository 层。

## 目录结构
```
app/
├── config.py          # 配置（含 DB_TYPE 切换）
├── database.py        # 引擎/会话工厂、get_db 依赖
├── core/
│   ├── response.py    # 统一响应 ApiResponse / 分页
│   └── exceptions.py  # 业务异常
├── models/            # ORM 模型（映射 b01~b99 表）
├── schemas/           # Pydantic 请求/响应模型
├── services/          # 业务逻辑层
└── routers/           # 接口层（按模块 b01~b05 拆分）
```

## 运行
```bash
pip install -r requirements.txt
# 开发
uvicorn main:app --reload --port 8000
# 或
python main.py
```
API 文档：http://localhost:8000/docs

## 约定
- 分层：router → service → model；跨层用 Schema 传递，不直出 ORM 对象。
- 响应统一 `{ code, message, data, trace_id }`，`code=0` 成功。
- 新增模块请参照 `b01_space` 的完整实现（model/schema/service/router 四件套）。
