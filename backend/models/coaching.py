"""
面试辅导结果 ORM 模型
"""

from datetime import datetime

from sqlalchemy import Column, Integer, Text, DateTime, ForeignKey

from models.database import Base


class CoachingSession(Base):
    """面试辅导结果表"""
    __tablename__ = "coaching_sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey("interview_sessions.id"), nullable=False)
    coaching_json = Column(Text, comment="完整辅导内容 JSON")
    created_at = Column(DateTime, default=datetime.utcnow)
