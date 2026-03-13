"""
简历数据 ORM 模型
"""

from datetime import datetime

from sqlalchemy import Column, Integer, String, Text, DateTime

from models.database import Base


class Resume(Base):
    """简历表"""
    __tablename__ = "resumes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    filename = Column(String(255), nullable=False, comment="原始文件名")
    raw_text = Column(Text, comment="PDF 提取的原始文本")
    parsed_json = Column(Text, comment="LLM 解析后的结构化 JSON")
    created_at = Column(DateTime, default=datetime.utcnow)
