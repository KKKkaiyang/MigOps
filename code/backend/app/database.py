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


def _apply_space_additive_migrations(engine: Engine) -> None:
    """空间库增量 DDL：create_all 仅能建缺失表，不能加列。

    当前无 Alembic，新增列（如 b04_saved_view.view_mode）在此以幂等方式补齐；
    新表由 init_space_models 的 create_all 自动建好。
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
