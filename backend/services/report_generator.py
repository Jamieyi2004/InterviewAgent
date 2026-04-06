"""
报告生成服务 —— 收集对话历史，调用 LLM 生成评估报告
"""

import json

from sqlalchemy.orm import Session

from agent.chains import call_llm_json
from agent.prompt_templates import REPORT_GENERATION_PROMPT
from models.interview import InterviewSession, Report
from services.interview_agent import get_agent


async def generate_report(session_id: int, db: Session) -> dict:
    """
    生成面试评估报告

    流程：
    1. 从 Agent 获取对话历史
    2. 构建报告生成 Prompt
    3. 调用 LLM 生成 JSON 报告
    4. 存入数据库

    Args:
        session_id: 面试会话 ID
        db: 数据库 session

    Returns:
        报告数据字典
    """
    # 1. 获取对话历史
    agent = get_agent(session_id)
    if not agent:
        raise ValueError(f"面试会话不存在或已过期：session_id={session_id}")

    conversation_history = agent.get_conversation_history()
    if not conversation_history.strip():
        raise ValueError("对话记录为空，无法生成报告")

    # 2. 获取面试会话信息
    session = db.query(InterviewSession).filter(
        InterviewSession.id == session_id
    ).first()

    # 3. 调用 LLM 生成报告
    prompt = REPORT_GENERATION_PROMPT.format(
        position=session.position if session else "未知岗位",
        conversation_history=conversation_history,
    )

    report_data = await call_llm_json(
        system_prompt="你是一位资深的面试评估专家，只输出JSON格式。",
        user_message=prompt,
    )

    # 4. 存入数据库
    report = Report(
        session_id=session_id,
        overall_score=report_data.get("overall_score", 0),
        report_json=json.dumps(report_data, ensure_ascii=False),
    )
    db.add(report)

    # 更新面试会话状态
    if session:
        session.status = "completed"

    db.commit()
    db.refresh(report)

    return {
        "session_id": session_id,
        "report_id": report.id,
        **report_data,
    }


def get_report(session_id: int, db: Session) -> dict | None:
    """
    查询已生成的报告

    Args:
        session_id: 面试会话 ID
        db: 数据库 session

    Returns:
        报告数据字典，未找到则返回 None
    """
    report = db.query(Report).filter(
        Report.session_id == session_id
    ).first()

    if not report:
        return None

    report_data = json.loads(report.report_json)
    return {
        "session_id": session_id,
        "overall_score": report.overall_score,
        "created_at": report.created_at.isoformat() if report.created_at else None,
        **report_data,
    }
