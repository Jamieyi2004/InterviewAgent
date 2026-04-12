"""
增强功能 API —— 提供面试增强模块的 REST 接口
"""

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from auth import get_current_user, verify_session_owner
from models.database import get_db
from models.user import User
from services.interview_agent import get_agent
from agent.persona_loader import get_persona_loader
from skills.base import create_default_registry

router = APIRouter(prefix="/api/enhanced", tags=["增强功能"])
logger = logging.getLogger(__name__)

# 与「标准评估报告」不同：以下接口依赖内存中的 InterviewAgent（后端重启或结束面试后即不可用）
_AGENT_UNAVAILABLE = (
    "该会话的实时面试实例不可用（可能已结束面试或后端已重启）。"
    "此类数据仅在面试进行中的活跃会话内可查；评估总结请使用「评估报告」页。"
)


def _require_live_agent(session_id: int, db: Session, user_id: int):
    """校验会话归属，并返回仍在内存中的 Agent。"""
    verify_session_owner(session_id, user_id, db)
    agent = get_agent(session_id)
    if not agent:
        raise HTTPException(status_code=404, detail=_AGENT_UNAVAILABLE)
    return agent


@router.get("/personas")
async def list_personas(current_user: User = Depends(get_current_user)):
    """获取所有可用的面试官人设"""
    loader = get_persona_loader()
    return {
        "personas": loader.list_personas_info(),
        "total": len(loader.list_persona_names()),
    }


@router.get("/plan/{session_id}")
async def get_plan(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取面试策略计划"""
    agent = _require_live_agent(session_id, db, current_user.id)
    plan = agent.get_plan_preview()
    if not plan:
        return {"message": "面试计划尚未生成", "plan": None}
    return {"plan": plan}


@router.get("/evaluation/{session_id}")
async def get_evaluation(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取实时评估结果"""
    agent = _require_live_agent(session_id, db, current_user.id)
    return {
        "summary": agent.engine.evaluation_agent.get_current_summary(),
        "evaluations": [
            {
                "turn": e.turn_number,
                "stage": e.stage,
                "verdict": e.verdict,
                "score": e.overall_score,
                "strengths": e.strengths,
                "weaknesses": e.weaknesses,
            }
            for e in agent.engine.evaluation_agent.evaluations
        ],
    }


@router.get("/token-usage/{session_id}")
async def get_token_usage(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取 Token 消耗报告"""
    agent = _require_live_agent(session_id, db, current_user.id)
    return agent.engine.token_tracker.get_report()


@router.get("/insights/{session_id}")
async def get_insights(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取候选人洞察"""
    agent = _require_live_agent(session_id, db, current_user.id)
    return {
        "insights": agent.engine.insight_extractor.insights.to_dict(),
        "prompt_text": agent.engine.insight_extractor.insights.to_prompt_text(),
    }


@router.get("/session-memory/{session_id}")
async def get_session_memory(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取结构化会话记忆"""
    agent = _require_live_agent(session_id, db, current_user.id)
    return agent.engine.session_memory.to_dict()


@router.get("/skills")
async def list_skills(current_user: User = Depends(get_current_user)):
    """获取所有可用的面试技能"""
    registry = create_default_registry()
    return {
        "skills": registry.list_skills_info(),
        "total": len(registry.get_all_skills()),
    }


@router.get("/state/{session_id}")
async def get_enhanced_state(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取增强版面试状态"""
    agent = _require_live_agent(session_id, db, current_user.id)
    return agent.get_state()


@router.post("/report/{session_id}")
async def generate_enhanced_report(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """生成增强版面试报告"""
    agent = _require_live_agent(session_id, db, current_user.id)
    try:
        report_data = await agent.get_enhanced_report_data()
        return {"session_id": session_id, **report_data}
    except Exception as e:
        logger.error("[Enhanced] 增强报告生成失败: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
