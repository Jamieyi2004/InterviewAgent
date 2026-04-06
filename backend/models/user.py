"""
用户 ORM 模型
"""

from datetime import datetime

from sqlalchemy import Column, Integer, String, Boolean, DateTime

from models.database import Base


class User(Base):
    """用户表"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), unique=True, nullable=False, index=True, comment="邮箱（登录标识）")
    username = Column(String(100), nullable=False, comment="用户名")
    hashed_password = Column(String(255), nullable=False, comment="bcrypt 哈希密码")
    role = Column(String(20), default="user", comment="user / admin")
    is_active = Column(Boolean, default=True, comment="是否启用")
    created_at = Column(DateTime, default=datetime.utcnow)
