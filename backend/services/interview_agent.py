"""
面试 Agent 核心服务（增强版）

借鉴闲鱼客服Agent的设计：
1. 完整的会话生命周期管理
2. 候选人画像实时追踪
3. 安全过滤集成
4. 对话历史格式化

职责：组装 状态机 + 记忆 + InterviewBot，驱动完整的面试对话流程
"""

from typing import AsyncIterator, Optional

from sqlalchemy.orm import Session

from agent.state_machine import InterviewStateMachine, InterviewStage
from agent.memory import InterviewMemory
from agent.interview_bot import InterviewBot
from models.interview import InterviewSession, Message
from models.resume import Resume
from services.resume_parser import get_resume_summary
from services.text_utils import clean_llm_output

import logging
logger = logging.getLogger(__name__)


class InterviewAgent:
    """
    面试 Agent —— 每个面试会话对应一个实例（增强版）

    核心流程：
    1. 初始化时加载简历数据，创建状态机、记忆和 Bot
    2. 每次候选人发消息时：
       a. 将消息存入记忆
       b. 调用对应阶段的 Agent 生成回复（含安全过滤）
       c. 通过三级路由检查是否需要跳转阶段
       d. 更新候选人画像
    """

    def __init__(
        self,
        session_id: int,
        resume: Resume,
        position: str,
    ):
        self.session_id = session_id
        self.resume = resume
        self.position = position
        self.resume_summary = get_resume_summary(resume)

        # 核心组件
        self.state_machine = InterviewStateMachine({}, position)
        self.memory = InterviewMemory()

        # 面试机器人（多 Agent 架构，含安全过滤和候选人画像）
        self.bot = InterviewBot(self.resume_summary, position)

        logger.info(
            "[Agent] 面试会话初始化: session_id=%d, position=%s, resume_chars=%d",
            session_id, position, len(self.resume_summary)
        )

    async def generate_opening(self) -> AsyncIterator[str]:
        """
        生成开场白（面试刚开始时调用，无需候选人输入）
        """
        # 使用开场 Agent 生成
        full_response = []

        async for token in self.bot.generate_reply(
            user_msg="面试开始",
            stage=self.state_machine.stage,
            context=[],
            question_count=0,
        ):
            full_response.append(token)
            yield token

        # 记录到记忆
        complete_text = clean_llm_output("".join(full_response))
        self.memory.add_interviewer_message(complete_text)
        self.state_machine.record_question()

        logger.info("[Agent] 开场白生成完成，长度=%d", len(complete_text))

    async def chat(self, candidate_message: str) -> AsyncIterator[str]:
        """
        处理候选人的一条消息，流式返回面试官的回复

        Args:
            candidate_message: 候选人发送的消息

        Yields:
            面试官回复的 token
        """
        # 1. 记录候选人消息
        self.memory.add_candidate_message(candidate_message)

        # 2. 如果面试已结束
        if self.state_machine.is_finished:
            closing = "感谢你参加本次面试，面试到此结束，稍后会生成评估报告，祝你一切顺利！"
            self.memory.add_interviewer_message(closing)
            yield closing
            return

        # 3. 获取对话历史（转换为 list[dict] 格式）
        context = []
        for msg in self.memory.get_messages():
            role = "assistant" if msg.type == "ai" else "user"
            context.append({"role": role, "content": msg.content})

        # 4. 调用对应阶段的 Agent 生成回复
        current_stage = self.state_machine.stage
        question_count = self.state_machine.question_count.get(current_stage.value, 0)

        logger.info(
            "[Agent] 处理消息: stage=%s, question_count=%d, msg_len=%d",
            current_stage.value, question_count, len(candidate_message)
        )

        full_response = []
        async for token in self.bot.generate_reply(
            user_msg=candidate_message,
            stage=current_stage,
            context=context,
            question_count=question_count,
        ):
            full_response.append(token)
            yield token

        # 5. 处理完整响应
        raw_text = "".join(full_response)
        clean_text = clean_llm_output(raw_text)

        logger.info("[Agent] AI 回复完成: stage=%s, len=%d", current_stage.value, len(clean_text))

        # 记录面试官回复
        self.memory.add_interviewer_message(clean_text)
        self.state_machine.record_question()

        # 6. 检查是否应该切换阶段（三级路由策略）
        should_transition = await self.bot.check_stage_complete(
            stage=self.state_machine.stage,
            context=context,
            last_response=clean_text,
        )

        if should_transition:
            old_stage = self.state_machine.stage.value
            self.state_machine.force_advance()
            new_stage = self.state_machine.stage.value
            logger.info("[Agent] 阶段切换: %s → %s", old_stage, new_stage)

    def get_conversation_history(self) -> str:
        """获取完整对话历史（用于生成报告）"""
        return self.memory.get_history_string()

    def get_state(self) -> dict:
        """获取当前面试状态（增强版，包含候选人画像信息）"""
        base_state = self.state_machine.to_dict()
        # 注入候选人画像信息
        base_state["candidate_engagement"] = self.bot.candidate_profile.engagement_level
        base_state["message_count"] = self.memory.message_count
        return base_state


# ===================== 会话管理 =====================

# 内存中保存活跃的面试 Agent 实例（session_id -> InterviewAgent）
_active_agents: dict[int, InterviewAgent] = {}


async def create_interview_session(
    resume_id: int, position: str, db: Session
) -> int:
    """
    创建面试会话

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
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    # 创建 Agent 实例并缓存
    agent = InterviewAgent(session.id, resume, position)
    _active_agents[session.id] = agent

    logger.info("[Service] 面试会话创建: session_id=%d, resume_id=%d, position=%s",
                session.id, resume_id, position)

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
