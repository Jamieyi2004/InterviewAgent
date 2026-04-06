"""
增强功能 API —— 提供面试增强模块的 REST 接口

新增端点：
1. GET /api/enhanced/personas — 获取所有面试官人设
2. GET /api/enhanced/plan/{session_id} — 获取面试计划
3. GET /api/enhanced/evaluation/{session_id} — 获取实时评估结果
4. GET /api/enhanced/token-usage/{session_id} — 获取 Token 消耗报告
5. GET /api/enhanced/insights/{session_id} — 获取候选人洞察
6. GET /api/enhanced/session-memory/{session_id} — 获取会话记忆
7. GET /api/enhanced/skills — 获取所有可用技能
8. POST /api/enhanced/report/{session_id} — 生成增强版报告
"""

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from models.database import get_db
from services.interview_agent import get_agent
from agent.persona_loader import get_persona_loader
from skills.base import create_default_registry

router = APIRouter(prefix="/api/enhanced", tags=["增强功能"])
logger = logging.getLogger(__name__)


@router.get("/personas")
async def list_personas():
    """获取所有可用的面试官人设"""
    loader = get_persona_loader()
    return {
        "personas": loader.list_personas_info(),
        "total": len(loader.list_persona_names()),
    }


@router.get("/plan/{session_id}")
async def get_plan(session_id: int):
    """获取面试策略计划"""
    agent = get_agent(session_id)
    if not agent:
        raise HTTPException(status_code=404, detail="面试会话不存在")

    plan = agent.get_plan_preview()
    if not plan:
        return {"message": "面试计划尚未生成", "plan": None}

    return {"plan": plan}


@router.get("/evaluation/{session_id}")
async def get_evaluation(session_id: int):
    """获取实时评估结果"""
    agent = get_agent(session_id)
    if not agent:
        raise HTTPException(status_code=404, detail="面试会话不存在")

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
async def get_token_usage(session_id: int):
    """获取 Token 消耗报告"""
    agent = get_agent(session_id)
    if not agent:
        raise HTTPException(status_code=404, detail="面试会话不存在")

    return agent.engine.token_tracker.get_report()


@router.get("/insights/{session_id}")
async def get_insights(session_id: int):
    """获取候选人洞察"""
    agent = get_agent(session_id)
    if not agent:
        raise HTTPException(status_code=404, detail="面试会话不存在")

    return {
        "insights": agent.engine.insight_extractor.insights.to_dict(),
        "prompt_text": agent.engine.insight_extractor.insights.to_prompt_text(),
    }


@router.get("/session-memory/{session_id}")
async def get_session_memory(session_id: int):
    """获取结构化会话记忆"""
    agent = get_agent(session_id)
    if not agent:
        raise HTTPException(status_code=404, detail="面试会话不存在")

    return agent.engine.session_memory.to_dict()


@router.get("/skills")
async def list_skills():
    """获取所有可用的面试技能"""
    registry = create_default_registry()
    return {
        "skills": registry.list_skills_info(),
        "total": len(registry.get_all_skills()),
    }


@router.get("/state/{session_id}")
async def get_enhanced_state(session_id: int):
    """获取增强版面试状态（包含所有模块的状态）"""
    agent = get_agent(session_id)
    if not agent:
        raise HTTPException(status_code=404, detail="面试会话不存在")

    return agent.get_state()


@router.post("/report/{session_id}")
async def generate_enhanced_report(session_id: int, db: Session = Depends(get_db)):
    """生成增强版面试报告（包含评估、洞察、Token统计等）"""
    agent = get_agent(session_id)
    if not agent:
        raise HTTPException(status_code=404, detail="面试会话不存在")

    try:
        report_data = await agent.get_enhanced_report_data()
        return {"session_id": session_id, **report_data}
    except Exception as e:
        logger.error("[Enhanced] 增强报告生成失败: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
