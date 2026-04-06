"""
面试引擎 —— 借鉴 Claude Code 的 QueryEngine 设计

核心改进（相比原 InterviewAgent）：
1. 事件驱动架构：通过 InterviewEvent 统一不同类型的输出
2. 多层预算控制：Token/轮次/时间，任一超限即停止
3. 集成所有增强模块：
   - 面试策略规划器（InterviewPlanner）
   - 结构化会话记忆（InterviewSessionMemory）
   - 上下文压缩器（ContextCompactor + InterviewSnip）
   - 实时评估 Agent（RealTimeEvaluationAgent）
   - 后台洞察提取（InterviewInsightExtractor）
   - Token 消耗追踪（TokenTracker）
   - 面试官人设系统（PersonaLoader）
   - 技能系统（SkillRegistry）
   - 生命周期钩子（InterviewHookManager）
   - 增强安全过滤（EnhancedSafetyFilter）
4. 钩子系统：在关键节点插入自定义逻辑
5. 向后兼容：保留原有 InterviewAgent 的所有公开接口

参考：Claude Code src/QueryEngine.ts (1296行)
"""

import time
import asyncio
from typing import AsyncIterator, Optional, Dict, List, Any
from dataclasses import dataclass, field
from enum import Enum

from loguru import logger

from agent.state_machine import InterviewStateMachine, InterviewStage
from agent.memory import InterviewMemory
from agent.interview_bot import InterviewBot
from agent.session_memory import InterviewSessionMemory
from agent.context_compactor import ContextCompactor, InterviewSnip
from agent.evaluation_agent import RealTimeEvaluationAgent
from agent.interview_planner import InterviewPlanner
from agent.insight_extractor import InterviewInsightExtractor
from agent.persona_loader import get_persona_loader, InterviewerPersona, DEFAULT_PERSONA
from agent.hooks import (
    InterviewHookManager, HookContext, HookEvent,
    create_evaluation_hook, create_memory_update_hook, create_budget_check_hook,
)
from agent.enhanced_safety import EnhancedSafetyFilter
from services.token_tracker import TokenTracker
from skills.base import SkillRegistry, SkillContext, create_default_registry
from services.resume_parser import get_resume_summary
from services.text_utils import clean_llm_output
from models.resume import Resume


# ======================== 事件类型 ========================

class EventType(str, Enum):
    """面试事件类型"""
    TEXT_CHUNK = "text_chunk"                # 流式文本片段
    EVALUATION_RESULT = "evaluation_result"  # 后台评估结果
    STAGE_TRANSITION = "stage_transition"    # 阶段切换
    PROGRESS_UPDATE = "progress_update"      # 进度更新
    BUDGET_WARNING = "budget_warning"        # 预算警告
    SAFETY_ALERT = "safety_alert"            # 安全警报
    INSIGHT_UPDATE = "insight_update"        # 洞察更新
    PLAN_READY = "plan_ready"               # 面试计划就绪
    COMPACT_DONE = "compact_done"           # 上下文压缩完成


@dataclass
class InterviewEvent:
    """面试事件"""
    type: EventType
    data: Any = None
    stage: str = ""
    timestamp: float = field(default_factory=time.time)


# ======================== 引擎配置 ========================

@dataclass
class InterviewEngineConfig:
    """面试引擎配置"""
    max_token_budget: int = 100000          # 最大 Token 预算
    max_cost_usd: float = 1.0              # 最大美元预算
    max_turns: int = 30                     # 最大对话轮次
    max_duration_minutes: int = 40          # 最大面试时长（分钟）
    enable_evaluation: bool = True          # 是否启用实时评估
    enable_insight_extraction: bool = True  # 是否启用洞察提取
    enable_planning: bool = True            # 是否启用面试规划
    enable_compact: bool = True             # 是否启用上下文压缩
    persona_name: str = ""                  # 面试官人设名称（空则使用默认）


# ======================== 面试引擎 ========================

class InterviewEngine:
    """
    面试引擎 —— 系统的核心驱动器

    使用方式（与原 InterviewAgent 接口兼容）：
        engine = InterviewEngine(
            session_id=1,
            resume=resume_obj,
            position="Java后端开发",
            config=InterviewEngineConfig(enable_evaluation=True),
        )

        # 生成开场白（流式）
        async for token in engine.generate_opening():
            print(token)

        # 处理候选人消息（流式）
        async for token in engine.chat("我的回答是..."):
            print(token)

        # 获取增强状态
        state = engine.get_state()

        # 面试结束后获取完整报告数据
        report_data = await engine.get_enhanced_report_data()
    """

    def __init__(
        self,
        session_id: int,
        resume: Resume,
        position: str,
        config: Optional[InterviewEngineConfig] = None,
    ):
        self.session_id = session_id
        self.resume = resume
        self.position = position
        self.config = config or InterviewEngineConfig()
        self.resume_summary = get_resume_summary(resume)

        # ---- 原有核心组件 ----
        self.state_machine = InterviewStateMachine({}, position)
        self.memory = InterviewMemory()
        self.bot = InterviewBot(self.resume_summary, position)

        # ---- 新增：增强模块 ----
        self.token_tracker = TokenTracker(budget_usd=self.config.max_cost_usd)
        self.session_memory = InterviewSessionMemory()
        self.compactor = ContextCompactor()
        self.snip = InterviewSnip()
        self.evaluation_agent = RealTimeEvaluationAgent()
        self.planner = InterviewPlanner()
        self.insight_extractor = InterviewInsightExtractor()
        self.safety_filter = EnhancedSafetyFilter()
        self.skill_registry = create_default_registry()
        self.hook_manager = InterviewHookManager()

        # ---- 人设系统 ----
        self.persona = self._load_persona()

        # ---- 面试计划 ----
        self.plan = None

        # ---- 状态追踪 ----
        self._start_time = time.time()
        self._turn_count = 0
        self._last_question = ""
        self._events: List[InterviewEvent] = []

        # ---- 初始化钩子 ----
        self._setup_hooks()

        # ---- 初始化会话记忆 ----
        self.session_memory.initialize(
            candidate_name="候选人",
            position=position,
            date=time.strftime("%Y-%m-%d"),
        )

        logger.info(
            "[Engine] 面试引擎初始化: session_id=%d, position=%s, persona=%s",
            session_id, position, self.persona.name,
        )

    def _load_persona(self) -> InterviewerPersona:
        """加载面试官人设"""
        if self.config.persona_name:
            loader = get_persona_loader()
            return loader.get_persona(self.config.persona_name)
        return DEFAULT_PERSONA

    def _setup_hooks(self):
        """设置内置钩子"""
        # 评估钩子（每次回答后触发）
        if self.config.enable_evaluation:
            self.hook_manager.register(
                HookEvent.POST_ANSWER.value,
                create_evaluation_hook(self.evaluation_agent),
                name="auto_evaluation",
                priority=10,
                run_in_background=True,
            )

        # 记忆更新钩子
        self.hook_manager.register(
            HookEvent.POST_ANSWER.value,
            create_memory_update_hook(self.session_memory),
            name="memory_update",
            priority=20,
        )

        # 预算检查钩子
        self.hook_manager.register(
            HookEvent.POST_ANSWER.value,
            create_budget_check_hook(self.token_tracker),
            name="budget_check",
            priority=30,
        )

    # ======================== 公开接口（兼容原 InterviewAgent） ========================

    async def generate_opening(self) -> AsyncIterator[str]:
        """
        生成开场白（流式输出）

        增强：
        1. 面试前生成策略计划
        2. 人设系统影响开场风格
        3. Token 追踪
        """
        # 1. 生成面试策略计划（后台）
        if self.config.enable_planning:
            try:
                self.plan = await self.planner.generate_plan(
                    resume_summary=self.resume_summary,
                    position=self.position,
                )
                self._emit_event(EventType.PLAN_READY, self.plan.to_dict())
                logger.info("[Engine] 面试计划生成完成")
            except Exception as e:
                logger.warning("[Engine] 面试计划生成失败: %s", e)

        # 2. 触发面试开始钩子
        await self.hook_manager.trigger(
            HookEvent.INTERVIEW_START.value,
            HookContext(
                event=HookEvent.INTERVIEW_START.value,
                stage=self.state_machine.stage.value,
                data={"plan": self.plan.to_dict() if self.plan else {}},
            ),
        )

        # 3. 生成开场白
        full_response = []
        async for token in self.bot.generate_reply(
            user_msg="面试开始",
            stage=self.state_machine.stage,
            context=[],
            question_count=0,
        ):
            full_response.append(token)
            yield token

        # 4. 记录
        complete_text = clean_llm_output("".join(full_response))
        self.memory.add_interviewer_message(complete_text)
        self.state_machine.record_question()
        self._last_question = complete_text

        logger.info("[Engine] 开场白生成完成，长度=%d", len(complete_text))

    async def chat(self, candidate_message: str) -> AsyncIterator[str]:
        """
        处理候选人消息，流式返回面试官回复

        增强流程：
        1. 安全过滤检查
        2. 上下文压缩检查
        3. 生成回复（含人设影响）
        4. 触发 post_answer 钩子（评估、记忆更新、预算检查）
        5. 后台洞察提取
        6. 检查阶段切换
        7. Token 记录
        """
        self._turn_count += 1

        # 1. 安全检查
        safety_result = self.safety_filter.check_candidate_input(candidate_message)
        if not safety_result.is_safe:
            self._emit_event(EventType.SAFETY_ALERT, {
                "threat_level": safety_result.threat_level.value,
                "warnings": safety_result.warnings,
            })
            logger.warning("[Engine] 安全警报: %s", safety_result.warnings)

        # 2. 记录候选人消息
        self.memory.add_candidate_message(candidate_message)

        # 3. 面试已结束
        if self.state_machine.is_finished:
            closing = "感谢你参加本次面试，面试到此结束，稍后会生成评估报告，祝你一切顺利！"
            self.memory.add_interviewer_message(closing)
            yield closing
            return

        # 4. 构建上下文（含压缩）
        context = self._build_context()

        # 5. 上下文压缩检查
        if self.config.enable_compact:
            context, was_compacted = await self.compactor.compact_if_needed(
                context,
                session_memory_text=self.session_memory.get_memory_for_prompt(),
            )
            if was_compacted:
                self._emit_event(EventType.COMPACT_DONE, self.compactor.get_stats())

        # 6. 生成回复
        current_stage = self.state_machine.stage
        question_count = self.state_machine.question_count.get(current_stage.value, 0)

        full_response = []
        async for token in self.bot.generate_reply(
            user_msg=candidate_message,
            stage=current_stage,
            context=context,
            question_count=question_count,
        ):
            full_response.append(token)
            yield token

        # 7. 处理完整响应
        raw_text = "".join(full_response)
        clean_text = clean_llm_output(raw_text)

        # 安全过滤面试官输出
        output_safety = self.safety_filter.check_interviewer_output(clean_text)
        clean_text = output_safety.filtered_text

        # 记录到记忆
        self.memory.add_interviewer_message(clean_text)
        self.state_machine.record_question()
        self._last_question = clean_text

        # 8. 触发 post_answer 钩子（评估、记忆更新、预算检查）
        hook_ctx = HookContext(
            event=HookEvent.POST_ANSWER.value,
            stage=current_stage.value,
            data={
                "question": self._last_question,
                "answer": candidate_message,
                "turn_number": self._turn_count,
                "question_count": question_count,
            },
        )
        await self.hook_manager.trigger(HookEvent.POST_ANSWER.value, hook_ctx)

        # 9. 后台洞察提取
        if self.config.enable_insight_extraction:
            if self.insight_extractor.should_extract(self.memory.message_count):
                asyncio.create_task(self._run_insight_extraction())

        # 10. 检查阶段切换
        should_transition = await self.bot.check_stage_complete(
            stage=self.state_machine.stage,
            context=context,
            last_response=clean_text,
        )

        if should_transition:
            old_stage = self.state_machine.stage.value
            self.state_machine.force_advance()
            new_stage = self.state_machine.stage.value

            self._emit_event(EventType.STAGE_TRANSITION, {
                "from": old_stage,
                "to": new_stage,
            })

            # 触发阶段切换钩子
            await self.hook_manager.trigger(
                HookEvent.POST_STAGE_TRANSITION.value,
                HookContext(
                    event=HookEvent.POST_STAGE_TRANSITION.value,
                    stage=new_stage,
                    data={"from_stage": old_stage, "to_stage": new_stage},
                ),
            )

            logger.info("[Engine] 阶段切换: %s → %s", old_stage, new_stage)

        # 11. 预算检查
        if self._is_over_any_budget():
            self._emit_event(EventType.BUDGET_WARNING, {
                "token_budget": self.token_tracker.is_over_budget(),
                "turn_budget": self._turn_count >= self.config.max_turns,
                "time_budget": self._elapsed_minutes() >= self.config.max_duration_minutes,
            })

    # ======================== 增强方法 ========================

    def get_conversation_history(self) -> str:
        """获取完整对话历史（用于报告生成）"""
        return self.memory.get_history_string()

    def get_state(self) -> dict:
        """获取当前面试状态（增强版）"""
        base_state = self.state_machine.to_dict()
        base_state.update({
            "candidate_engagement": self.bot.candidate_profile.engagement_level,
            "message_count": self.memory.message_count,
            "turn_count": self._turn_count,
            "elapsed_minutes": round(self._elapsed_minutes(), 1),
            "persona": self.persona.name,
            "token_usage": self.token_tracker.get_report()["summary"],
            "evaluation_summary": self.evaluation_agent.get_current_summary(),
            "has_plan": self.plan is not None,
            "session_memory_tokens": self.session_memory.get_total_tokens(),
            "compact_stats": self.compactor.get_stats(),
            "insight_count": len(self.insight_extractor.insights.technical_signals),
        })
        return base_state

    async def get_enhanced_report_data(self) -> dict:
        """获取增强版报告数据（面试结束后调用）"""
        # 触发面试结束钩子
        await self.hook_manager.trigger(
            HookEvent.INTERVIEW_END.value,
            HookContext(
                event=HookEvent.INTERVIEW_END.value,
                stage="finished",
                data={"total_turns": self._turn_count},
            ),
        )

        # 生成最终评估报告
        final_eval = await self.evaluation_agent.generate_final_report(self.position)

        return {
            "evaluation": {
                "overall_score": final_eval.overall_score,
                "verdict": final_eval.verdict,
                "dimension_averages": final_eval.dimension_averages,
                "stage_scores": final_eval.stage_scores,
                "top_strengths": final_eval.top_strengths,
                "top_weaknesses": final_eval.top_weaknesses,
                "hiring_recommendation": final_eval.hiring_recommendation,
                "detailed_feedback": final_eval.detailed_feedback,
            },
            "insights": self.insight_extractor.insights.to_dict(),
            "token_report": self.token_tracker.get_report(),
            "session_memory": self.session_memory.to_dict(),
            "plan": self.plan.to_dict() if self.plan else None,
            "persona": self.persona.to_dict(),
            "hooks_log": self.hook_manager.get_execution_log(20),
            "events": [
                {"type": e.type.value, "stage": e.stage, "timestamp": e.timestamp}
                for e in self._events[-50:]
            ],
        }

    def get_plan_preview(self) -> Optional[dict]:
        """获取面试计划预览（用于前端展示）"""
        if self.plan:
            return self.plan.to_dict()
        return None

    # ======================== 私有方法 ========================

    def _build_context(self) -> List[Dict]:
        """构建上下文消息列表"""
        context = []
        for msg in self.memory.get_messages():
            role = "assistant" if msg.type == "ai" else "user"
            context.append({"role": role, "content": msg.content})
        return context

    async def _run_insight_extraction(self):
        """后台运行洞察提取"""
        try:
            context = self._build_context()
            recent = context[-10:]  # 最近 10 条
            await self.insight_extractor.extract_async(
                recent, self.state_machine.stage.value
            )
            self._emit_event(EventType.INSIGHT_UPDATE, {
                "strategy_suggestion": self.insight_extractor.get_strategy_suggestion(),
            })
        except Exception as e:
            logger.error("[Engine] 洞察提取失败: %s", e)

    def _emit_event(self, event_type: EventType, data: Any = None):
        """发出事件"""
        event = InterviewEvent(
            type=event_type,
            data=data,
            stage=self.state_machine.stage.value,
        )
        self._events.append(event)

    def _elapsed_minutes(self) -> float:
        """已经过的分钟数"""
        return (time.time() - self._start_time) / 60

    def _is_over_any_budget(self) -> bool:
        """是否超过任一预算"""
        return (
            self.token_tracker.is_over_budget()
            or self._turn_count >= self.config.max_turns
            or self._elapsed_minutes() >= self.config.max_duration_minutes
        )
