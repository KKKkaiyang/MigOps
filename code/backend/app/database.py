from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.models.base import Base


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


def init_models():
    """本地开发建表（生产环境建议使用 Alembic）。"""
    Base.metadata.create_all(bind=engine)
