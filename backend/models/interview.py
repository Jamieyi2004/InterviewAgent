"""
面试会话 & 对话记录 & 报告 ORM 模型
"""

from datetime import datetime

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey

from models.database import Base


class InterviewSession(Base):
    """面试会话表"""
    __tablename__ = "interview_sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    resume_id = Column(Integer, ForeignKey("resumes.id"), nullable=False)
    position = Column(String(255), nullable=False, comment="目标岗位")
    status = Column(String(50), default="in_progress", comment="in_progress / completed")
    current_stage = Column(String(50), default="opening", comment="当前面试阶段")
    created_at = Column(DateTime, default=datetime.utcnow)
    ended_at = Column(DateTime, nullable=True)


class Message(Base):
    """对话记录表"""
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey("interview_sessions.id"), nullable=False)
    role = Column(String(50), nullable=False, comment="interviewer / candidate")
    content = Column(Text, nullable=False)
    stage = Column(String(50), comment="消息所属面试阶段")
    created_at = Column(DateTime, default=datetime.utcnow)


class Report(Base):
    """评估报告表"""
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey("interview_sessions.id"), nullable=False)
    overall_score = Column(Integer, comment="综合评分 0-100")
    report_json = Column(Text, comment="完整报告 JSON")
    created_at = Column(DateTime, default=datetime.utcnow)
