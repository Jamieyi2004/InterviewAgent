"""
面试辅导服务 —— 基于报告和对话历史，生成个性化辅导内容
"""

import json
import logging

from sqlalchemy.orm import Session

from agent.chains import call_llm_json
from agent.prompt_templates import COACHING_GENERATION_PROMPT
from models.interview import InterviewSession, Message, Report
from models.coaching import CoachingSession

logger = logging.getLogger(__name__)


async def generate_coaching(session_id: int, db: Session) -> dict:
    """
    生成面试辅导内容

    流程：
    1. 加载评估报告和对话历史
    2. 调用 LLM 生成结构化辅导
    3. 存入数据库

    Returns:
        辅导内容字典
    """
    # 1. 获取报告
    report = db.query(Report).filter(Report.session_id == session_id).first()
    if not report:
        raise ValueError(f"评估报告不存在，请先生成报告：session_id={session_id}")

    report_data = json.loads(report.report_json)

    # 2. 获取会话信息
    session = (
        db.query(InterviewSession)
        .filter(InterviewSession.id == session_id)
        .first()
    )
    position = session.position if session else "未知岗位"

    # 3. 获取对话历史
    messages = (
        db.query(Message)
        .filter(Message.session_id == session_id)
        .order_by(Message.id)
        .all()
    )
    conversation_lines = []
    for msg in messages:
        role_label = "面试官" if msg.role == "interviewer" else "候选人"
        conversation_lines.append(f"[{role_label}] {msg.content}")
    conversation_history = "\n".join(conversation_lines)

    if not conversation_history.strip():
        raise ValueError("对话记录为空，无法生成辅导")

    # 4. 调用 LLM
    prompt = COACHING_GENERATION_PROMPT.format(
        position=position,
        report_json=json.dumps(report_data, ensure_ascii=False, indent=2),
        conversation_history=conversation_history[:8000],  # 截取避免超长
    )

    logger.info("开始生成面试辅导 session_id=%d", session_id)

    coaching_data = await call_llm_json(
        system_prompt="你是一位资深面试辅导教练，只输出JSON格式。",
        user_message=prompt,
        max_tokens=4096,
    )

    # 5. 存入数据库
    record = CoachingSession(
        session_id=session_id,
        coaching_json=json.dumps(coaching_data, ensure_ascii=False),
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    logger.info("面试辅导生成完成 session_id=%d", session_id)

    return {
        "session_id": session_id,
        "coaching_id": record.id,
        **coaching_data,
    }


def get_coaching(session_id: int, db: Session) -> dict | None:
    """查询已有的辅导内容"""
    record = (
        db.query(CoachingSession)
        .filter(CoachingSession.session_id == session_id)
        .order_by(CoachingSession.id.desc())
        .first()
    )
    if not record:
        return None

    coaching_data = json.loads(record.coaching_json)
    return {
        "session_id": session_id,
        "coaching_id": record.id,
        "created_at": record.created_at.isoformat() if record.created_at else None,
        **coaching_data,
    }
