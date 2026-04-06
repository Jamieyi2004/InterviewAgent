"""
简历分析结果 ORM 模型
"""

from datetime import datetime

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey

from models.database import Base


class ResumeAnalysis(Base):
    """简历分析结果表"""
    __tablename__ = "resume_analyses"

    id = Column(Integer, primary_key=True, autoincrement=True)
    resume_id = Column(Integer, ForeignKey("resumes.id"), nullable=False)
    overall_score = Column(Integer, comment="简历综合评分 0-100")
    analysis_json = Column(Text, comment="完整分析结果 JSON")
    target_position = Column(String(255), nullable=True, comment="目标岗位")
    created_at = Column(DateTime, default=datetime.utcnow)
