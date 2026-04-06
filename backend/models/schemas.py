"""
Pydantic 请求 / 响应数据模型（Schema）
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


# ===================== 简历相关 =====================

class ResumeUploadResponse(BaseModel):
    """简历上传成功响应"""
    resume_id: int
    filename: str
    parsed_data: dict


# ===================== 面试会话相关 =====================

class InterviewStartRequest(BaseModel):
    """开始面试请求"""
    resume_id: int
    position: str = "Java后端开发工程师"
    persona_name: str = ""   # 面试官人设名称（可选）


class InterviewStartResponse(BaseModel):
    """开始面试响应"""
    session_id: int
    message: str = "面试会话已创建"
    persona: str = ""   # 使用的面试官人设名称


# ===================== WebSocket 消息 =====================

class ChatMessage(BaseModel):
    """WebSocket 聊天消息"""
    role: str          # interviewer / candidate
    content: str
    stage: Optional[str] = None


# ===================== 报告相关 =====================

class DimensionScore(BaseModel):
    """维度评分"""
    score: int
    comment: str


class QuestionReview(BaseModel):
    """逐题点评"""
    question: str
    answer_quality: str
    comment: str
    reference_answer: str


class ReportResponse(BaseModel):
    """评估报告响应"""
    session_id: int
    overall_score: int
    dimensions: dict
    strengths: list[str]
    weaknesses: list[str]
    suggestions: list[str]
    question_reviews: list[dict]
    created_at: Optional[datetime] = None
