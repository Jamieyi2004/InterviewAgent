"""
SQLAlchemy 数据库引擎和 Session 管理
"""

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from config import DATABASE_URL

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """ORM 基类"""
    pass


def get_db():
    """FastAPI 依赖注入：获取数据库 session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """创建所有表（首次启动时调用）+ 迁移旧表"""
    Base.metadata.create_all(bind=engine)

    # 迁移：为旧表添加 user_id 列（已存在则忽略）
    with engine.connect() as conn:
        for table in ("resumes", "interview_sessions"):
            try:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN user_id INTEGER"))
                conn.commit()
            except Exception:
                pass  # 列已存在
