"""
面试 Agent 核心服务（增强版 v2）

借鉴 Claude Code QueryEngine + Coordinator-Worker 架构重构：
1. InterviewEngine 集成所有增强模块
2. 保留原 InterviewAgent 作为轻量级兼容接口
3. 完整的会话生命周期管理
4. 支持通过配置选择不同面试官人设
5. Token 追踪、实时评估、会话记忆、上下文压缩等

新增能力：
- 面试策略规划器
- 结构化会话记忆
- 上下文压缩
- 实时评估
- 后台洞察提取
- Token 消耗追踪
- 面试官人设系统
- 技能系统
- 生命周期钩子
- 增强安全过滤
"""

from typing import AsyncIterator, Optional

from sqlalchemy.orm import Session

from agent.interview_engine import InterviewEngine, InterviewEngineConfig
from models.interview import InterviewSession, Message
from models.resume import Resume

import logging
logger = logging.getLogger(__name__)


class InterviewAgent:
    """
    面试 Agent（增强版 v2）—— InterviewEngine 的便捷包装

    保持与原接口完全兼容，同时通过 InterviewEngine 获得所有增强能力。
    """

    def __init__(
        self,
        session_id: int,
        resume: Resume,
        position: str,
        persona_name: str = "",
    ):
        self.session_id = session_id
        self.resume = resume
        self.position = position

        # 使用 InterviewEngine 作为核心驱动
        config = InterviewEngineConfig(persona_name=persona_name)
        self.engine = InterviewEngine(
            session_id=session_id,
            resume=resume,
            position=position,
            config=config,
        )

        # 暴露引擎的内部组件（兼容旧接口）
        self.state_machine = self.engine.state_machine
        self.memory = self.engine.memory
        self.bot = self.engine.bot

        logger.info(
            "[Agent] 面试会话初始化(v2): session_id=%d, position=%s, persona=%s",
            session_id, position, self.engine.persona.name,
        )

    async def generate_opening(self) -> AsyncIterator[str]:
        """生成开场白（委托给 Engine）"""
        async for token in self.engine.generate_opening():
            yield token

    async def chat(self, candidate_message: str) -> AsyncIterator[str]:
        """处理候选人消息（委托给 Engine）"""
        async for token in self.engine.chat(candidate_message):
            yield token

    def get_conversation_history(self) -> str:
        """获取完整对话历史"""
        return self.engine.get_conversation_history()

    def get_state(self) -> dict:
        """获取当前面试状态（增强版）"""
        return self.engine.get_state()

    async def get_enhanced_report_data(self) -> dict:
        """获取增强版报告数据"""
        return await self.engine.get_enhanced_report_data()

    def get_plan_preview(self) -> Optional[dict]:
        """获取面试计划预览"""
        return self.engine.get_plan_preview()


# ===================== 会话管理 =====================

# 内存中保存活跃的面试 Agent 实例（session_id -> InterviewAgent）
_active_agents: dict[int, InterviewAgent] = {}


async def create_interview_session(
    resume_id: int, position: str, db: Session,
    persona_name: str = "",
    user_id: int = None,
) -> int:
    """
    创建面试会话

    Args:
        resume_id: 简历 ID
        position: 目标岗位
        db: 数据库 session
        persona_name: 面试官人设名称（可选）

    Returns:
        session_id
    """
    # 查询简历
    resume = db.query(Resume).filter(Resume.id == resume_id).first()
    if not resume:
        raise ValueError(f"简历不存在：resume_id={resume_id}")

    # 创建数据库记录
    session = InterviewSession(
        resume_id=resume_id,
        position=position,
        user_id=user_id,
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    # 创建 Agent 实例并缓存（使用 InterviewEngine 增强版）
    agent = InterviewAgent(session.id, resume, position, persona_name=persona_name)
    _active_agents[session.id] = agent

    logger.info(
        "[Service] 面试会话创建(v2): session_id=%d, resume_id=%d, position=%s, persona=%s",
        session.id, resume_id, position, persona_name or "default",
    )

    return session.id


def get_agent(session_id: int) -> Optional[InterviewAgent]:
    """获取活跃的面试 Agent"""
    return _active_agents.get(session_id)


def remove_agent(session_id: int):
    """移除面试 Agent（面试结束后清理）"""
    agent = _active_agents.pop(session_id, None)
    if agent:
        logger.info("[Service] 面试会话清理: session_id=%d", session_id)


async def save_message(
    session_id: int, role: str, content: str, stage: str, db: Session
):
    """将消息持久化到数据库"""
    msg = Message(
        session_id=session_id,
        role=role,
        content=content,
        stage=stage,
    )
    db.add(msg)
    db.commit()
