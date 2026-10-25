import re
import time
from typing import Dict

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.models.base import Base
from app.models.space_base import SpaceBase


def _build_url() -> str:
    """依据 DB_TYPE 返回对应数据源连接串（MySQL / StarRocks 可切换）。"""
    if settings.DB_TYPE == "starrocks":
        return settings.STARROCKS_URL
    return settings.MYSQL_URL


engine = create_engine(_build_url(), pool_pre_ping=True, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db():
    """FastAPI 依赖：会话生命周期管理。"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _db_name() -> str:
    """当前配置连接串中的库名。"""
    return make_url(_build_url()).database or ""


def _server_engine():
    """不带库名的 server 级 engine，用于建库。"""
    # 注意：URL.set(database=None) 会忽略 None 值，必须用 _replace 才能真正移除库名
    url = make_url(_build_url())._replace(database=None)
    return create_engine(url, pool_pre_ping=True, future=True, isolation_level="AUTOCOMMIT")


def _create_database_if_absent(db_name: str) -> None:
    """在数据库实例上创建库（幂等）。"""
    if not db_name:
        return
    eng = _server_engine()
    try:
        with eng.connect() as conn:
            conn.execute(
                text(
                    f"CREATE DATABASE IF NOT EXISTS `{db_name}` "
                    "CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci"
                )
            )
    finally:
        eng.dispose()


def ensure_database() -> None:
    """确保公共业务库存在（本地开发引导；生产建议由 DBA 预建）。"""
    _create_database_if_absent(_db_name())


def _space_db_name(space_code: str) -> str:
    """由项目简称派生空间库名：mig_<space_code>_db。"""
    return f"{settings.SPACE_DB_PREFIX}{space_code}_db"


def space_db_name(space_code: str) -> str:
    return _space_db_name(space_code)


_IDENTIFIER_RE = re.compile(r"^[a-z][a-z0-9_]{1,30}$")


def create_space_database(space_code: str) -> str:
    """创建项目空间独立数据库（幂等），返回库名。

    空间库创建后，按业务模块维护的建表脚本在各空间库内执行；
    调用方通常使用 ensure_space_tables() 一并完成建表。
    """
    if not _IDENTIFIER_RE.match(space_code):
        raise ValueError(f"非法的项目简称: {space_code}")
    db_name = _space_db_name(space_code)
    _create_database_if_absent(db_name)
    return db_name


# 物理删除时的库名安全校验：仅允许删除 mig_<code>_db 形态的空间库，杜绝误删公共库/其他库
_SPACE_DB_RE = re.compile(r"^mig_[a-z][a-z0-9_]{1,30}_db$")


def drop_space_database(db_name: str) -> None:
    """物理删除空间数据库并清理引擎缓存。

    仅接受 `mig_<space_code>_db` 形态的库名；校验不通过直接拒绝，避免误删其他库。
    删除成功后驱逐 `_space_engines` 中对应缓存，防止后续重连已销毁的数据库。
    """
    if not _SPACE_DB_RE.match(db_name or ""):
        raise ValueError(f"非法的空间数据库名，拒绝删除: {db_name}")
    eng = _server_engine()
    try:
        with eng.connect() as conn:
            conn.execute(text(f"DROP DATABASE IF EXISTS `{db_name}`"))
    finally:
        eng.dispose()
    _space_engines.pop(db_name, None)


# ── 空间库引擎与建表 ──
# 空间库与公共库同实例不同库（CODEBUDDY.md §8.4），复用同一连接配置，
# 按库名缓存 engine，避免重复创建连接池。
_space_engines: Dict[str, Engine] = {}


def get_space_engine(db_name: str) -> Engine:
    """按空间库名获取（并缓存）engine。"""
    eng = _space_engines.get(db_name)
    if eng is None:
        url = make_url(_build_url())._replace(database=db_name)
        eng = create_engine(url, pool_pre_ping=True, future=True)
        _space_engines[db_name] = eng
    return eng


def init_space_models(engine: Engine) -> None:
    """在指定空间库创建空间业务表（幂等）。

    注意：create_all 仅能新建缺失的表，改列/改类型需手工 DDL
    （当前无 Alembic，空间库 DDL 由各模块建表入口维护）。
    """
    SpaceBase.metadata.create_all(bind=engine)


def ensure_space_tables(space_code: str) -> str:
    """确保空间库存在且空间业务表就绪，返回库名。"""
    db_name = create_space_database(space_code)
    engine = get_space_engine(db_name)
    init_space_models(engine)
    _apply_space_additive_migrations(engine)
    return db_name


def _space_column_exists(conn, table: str, column: str) -> bool:
    row = conn.execute(
        text(
            "SELECT COUNT(*) FROM information_schema.COLUMNS "
            "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = :t AND COLUMN_NAME = :c"
        ),
        {"t": table, "c": column},
    ).scalar()
    return bool(row)


def _index_exists(conn, index_name: str) -> bool:
    """空间库内索引是否已存在（幂等 DDL 前置判断）。"""
    row = conn.execute(
        text(
            "SELECT COUNT(*) FROM information_schema.STATISTICS "
            "WHERE TABLE_SCHEMA = DATABASE() AND INDEX_NAME = :i"
        ),
        {"i": index_name},
    ).scalar()
    return bool(row)


def _ensure_index(conn, table: str, index_name: str, columns: list) -> None:
    """幂等创建索引（仅当不存在时）。"""
    if not _index_exists(conn, index_name):
        cols = ", ".join(f"`{c}`" for c in columns)
        conn.execute(text(f"CREATE INDEX `{index_name}` ON `{table}` ({cols})"))


def _apply_space_additive_migrations(engine: Engine) -> None:
    """空间库增量 DDL：create_all 仅能建缺失表，不能加列/改列。

    当前无 Alembic，新增/删除列在此以幂等方式补齐/清理（见需求 D1~D4 重塑）：
    - b04_task 重塑：删除旧列（开发态清空重建，丢弃旧数据，决策①），补齐 5 维状态等新列；
    - 新表 b04_task_ext / b04_migration_template 由 init_space_models 的 create_all 自动建好。
    - b07 血缘检索加速：空间作用域复合索引（按 表名称/工作流名称/任务名称 检索慢，bug 修复）。
    """
    with engine.begin() as conn:
        if not _space_column_exists(conn, "b04_saved_view", "view_mode"):
            conn.execute(
                text(
                    "ALTER TABLE b04_saved_view ADD COLUMN view_mode "
                    "VARCHAR(16) NOT NULL DEFAULT 'dynamic' COMMENT 'dynamic=动态引用;fixed=固化台账'"
                )
            )
        if not _space_column_exists(conn, "b06_tag", "tag_category"):
            conn.execute(
                text(
                    "ALTER TABLE b06_tag ADD COLUMN tag_category "
                    "VARCHAR(16) NOT NULL DEFAULT '技术标签' COMMENT '标签分类: 管理标签 / 技术标签'"
                )
            )
        # ── b04_task 重塑（D1~D3）：删除旧列（开发态清空重建，丢弃旧数据） ──
        _OLD_B04_TASK_COLS = [
            "script_name",
            "input_tables",
            "output_tables",
            "schedule_status",
            "dw_project_space",
            "owner",
            "latest_note",
        ]
        for col in _OLD_B04_TASK_COLS:
            if _space_column_exists(conn, "b04_task", col):
                conn.execute(text(f"ALTER TABLE b04_task DROP COLUMN `{col}`"))
        # 补齐 b04_task 新列（create_all 已建表时一并创建；此处覆盖存量旧表升级场景）
        # B04-08 导入放宽：env/迁移负责人/5 维状态/数据校验结果改可空且不设默认值
        # （显式 NULL 需能落库；任务创建仅经导入路径，无需默认值）
        _NEW_B04_TASK_COLS = {
            "project_name": "VARCHAR(128) NOT NULL DEFAULT 'default'",
            "env": "VARCHAR(32) NULL",
            "business": "VARCHAR(255) NULL",
            "task_type": "VARCHAR(64) NULL",
            "migration_owner": "VARCHAR(64) NULL",
            "active_status": "VARCHAR(32) NULL",
            "migration_status": "VARCHAR(32) NULL",
            "dualrun_status": "VARCHAR(32) NULL",
            "check_status": "VARCHAR(32) NULL",
            "acceptance_status": "VARCHAR(32) NULL",
            "remark": "VARCHAR(1024) NULL",
            "check_result": "VARCHAR(32) NULL",
        }
        for col, ddl in _NEW_B04_TASK_COLS.items():
            if not _space_column_exists(conn, "b04_task", col):
                conn.execute(
                    text(f"ALTER TABLE b04_task ADD COLUMN `{col}` {ddl} COMMENT 'b04重塑新增'")
                )
        # B04-08：存量 NOT NULL 列幂等改可空（导入仅强制 项目名称+任务名称，其余可留空）
        for col in (
            "env",
            "migration_owner",
            "active_status",
            "migration_status",
            "dualrun_status",
            "check_result",
        ):
            nullable = conn.execute(
                text(
                    "SELECT IS_NULLABLE FROM information_schema.COLUMNS "
                    "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'b04_task' AND COLUMN_NAME = :c"
                ),
                {"c": col},
            ).scalar()
            if nullable == "NO":
                conn.execute(
                    text(f"ALTER TABLE b04_task MODIFY COLUMN `{col}` {_NEW_B04_TASK_COLS[col]}")
                )

        # ── b07 血缘检索加速：空间作用域复合索引（按 表名称/工作流名称/任务名称 检索慢） ──
        # 新空间由 create_all 直接建好；存量空间（如 lineage_demo）在此幂等补齐。
        _ensure_index(conn, "b07_lineage", "idx_b07_space_workflow", ["space_id", "workflow_name"])
        _ensure_index(conn, "b07_lineage", "idx_b07_space_task", ["space_id", "task_name"])
        _ensure_index(conn, "b07_lineage", "idx_b07_space_proj_task", ["space_id", "project_name", "task_name"])
        _ensure_index(conn, "b07_lineage", "idx_b07_space_input", ["space_id", "input_table"])
        _ensure_index(conn, "b07_lineage", "idx_b07_space_output", ["space_id", "output_table"])
        # 清理被取代的旧单列索引（幂等）
        for _old in ("idx_b07_workflow", "idx_b07_input", "idx_b07_output"):
            if _index_exists(conn, _old):
                conn.execute(text(f"DROP INDEX `{_old}` ON `b07_lineage`"))


# 扩展列名白名单：仅允许 f_<数字>，防止动态 DDL 注入（需求 §9.4）
_EXT_COL_RE = re.compile(r"^f_[0-9]+$")


def ensure_task_ext_columns(engine: Engine, ext_field_defs: list) -> None:
    """按空间模板的扩展字段定义（有序）对 b04_task_ext 动态加列 / 删列（D4）。

    ext_field_defs: 列表，每项 {"name": "f_1", "ext_type": "enum"|"string"}，
                    顺序即列编号（f_1、f_2 …）。enum 默认建索引、string 默认 VARCHAR(255)。
    开发态清空重建：删除不在目标集的 f_n 列（保留 task_id）。
    """
    with engine.begin() as conn:
        existing_cols = set(
            conn.execute(
                text(
                    "SELECT COLUMN_NAME FROM information_schema.COLUMNS "
                    "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'b04_task_ext'"
                )
            ).scalars().all()
        )
        target_cols = {d["name"] for d in ext_field_defs}
        # 新增缺失列
        for d in ext_field_defs:
            col = d["name"]
            if not _EXT_COL_RE.match(col):
                raise ValueError(f"非法的扩展列名: {col}")
            if col not in existing_cols:
                conn.execute(
                    text(
                        f"ALTER TABLE b04_task_ext ADD COLUMN `{col}` "
                        "VARCHAR(255) NULL COMMENT '模板扩展字段'"
                    )
                )
                if d.get("ext_type") == "enum":
                    conn.execute(
                        text(f"ALTER TABLE b04_task_ext ADD INDEX `idx_{col}` (`{col}`)")
                    )
        # 删除多余扩展列（开发态清空重建，决策①）
        for col in existing_cols:
            if _EXT_COL_RE.match(col) and col not in target_cols:
                conn.execute(text(f"ALTER TABLE b04_task_ext DROP COLUMN `{col}`"))


def init_models():
    """本地开发建表（生产环境建议使用 Alembic）。"""
    Base.metadata.create_all(bind=engine)
    _apply_common_additive_migrations()


def _column_exists(conn, table: str, column: str) -> bool:
    row = conn.execute(
        text(
            "SELECT COUNT(*) FROM information_schema.COLUMNS "
            "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = :t AND COLUMN_NAME = :c"
        ),
        {"t": table, "c": column},
    ).scalar()
    return bool(row)


def _apply_common_additive_migrations() -> None:
    """公共库增量 DDL：create_all 只能建缺失的表，不能加列。

    当前无 Alembic，新增列在此以幂等方式补齐（仅 ADD COLUMN，不改列）。
    """
    with engine.begin() as conn:
        if not _column_exists(conn, "b01_space", "overall_progress"):
            conn.execute(
                text(
                    "ALTER TABLE b01_space ADD COLUMN overall_progress "
                    "TINYINT NOT NULL DEFAULT 0 COMMENT '整体进展(0-100,手工维护)'"
                )
            )


def init_models_with_retry(retries: int = 10, delay: float = 1.0):
    """带重试的建表：等待数据库服务就绪（容器化部署场景）。"""
    last_err = None
    for _ in range(retries):
        try:
            ensure_database()
            init_models()
            return
        except Exception as exc:  # noqa: BLE001
            last_err = exc
            time.sleep(delay)
    raise last_err
