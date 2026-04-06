"""
面试生命周期钩子系统 —— 借鉴 Claude Code 的 Hook 系统设计

核心设计：
1. 在面试的关键节点插入自定义逻辑
2. 支持 pre/post 两种时机
3. 钩子链式执行，支持中断
4. 异步执行，不阻塞主流程（可选）
5. 统一的钩子注册和管理

参考：
- Claude Code src/services/tools/toolHooks.ts
- Claude Code src/hooks/useCanUseTool.tsx

支持的事件：
- interview_start: 面试开始
- interview_end: 面试结束
- pre_question: 提问前（可修改问题）
- post_answer: 回答后（可触发评估）
- pre_stage_transition: 阶段切换前（可拦截）
- post_stage_transition: 阶段切换后（可初始化）
- pre_compact: 上下文压缩前
- post_compact: 上下文压缩后
- evaluation_complete: 评估完成
- plan_generated: 面试计划生成完成
"""

import asyncio
import time
from typing import Callable, Dict, List, Any, Optional, Awaitable
from dataclasses import dataclass, field
from enum import Enum

from loguru import logger


# ======================== 事件类型 ========================

class HookEvent(str, Enum):
    """钩子事件类型"""
    INTERVIEW_START = "interview_start"
    INTERVIEW_END = "interview_end"
    PRE_QUESTION = "pre_question"
    POST_ANSWER = "post_answer"
    PRE_STAGE_TRANSITION = "pre_stage_transition"
    POST_STAGE_TRANSITION = "post_stage_transition"
    PRE_COMPACT = "pre_compact"
    POST_COMPACT = "post_compact"
    EVALUATION_COMPLETE = "evaluation_complete"
    PLAN_GENERATED = "plan_generated"


# ======================== 钩子上下文 ========================

@dataclass
class HookContext:
    """钩子执行上下文"""
    event: str                              # 事件类型
    stage: str = ""                         # 当前面试阶段
    data: Dict[str, Any] = field(default_factory=dict)  # 事件相关数据
    timestamp: float = field(default_factory=time.time)

    # 控制字段
    _abort: bool = False                    # 是否中断后续钩子和主流程
    _modified: bool = False                 # 数据是否被修改

    def abort(self):
        """中断后续执行"""
        self._abort = True

    @property
    def is_aborted(self) -> bool:
        return self._abort

    @property
    def is_modified(self) -> bool:
        return self._modified

    def set_data(self, key: str, value: Any):
        """修改上下文数据"""
        self.data[key] = value
        self._modified = True


# ======================== 钩子定义 ========================

# 钩子函数类型：接收 HookContext，返回 HookContext
HookFunction = Callable[[HookContext], Awaitable[HookContext]]


@dataclass
class HookRegistration:
    """钩子注册信息"""
    event: str
    callback: HookFunction
    name: str = ""                  # 钩子名称（用于调试）
    priority: int = 100             # 优先级（数字越小越先执行）
    is_async: bool = True           # 是否异步执行
    run_in_background: bool = False # 是否后台执行（不等待结果）


# ======================== 钩子管理器 ========================

class InterviewHookManager:
    """
    面试生命周期钩子管理器

    使用方式：
        hooks = InterviewHookManager()

        # 注册钩子
        hooks.register("post_answer", my_evaluation_hook, name="评估钩子")
        hooks.register("pre_stage_transition", my_guard_hook, name="阶段守卫")

        # 触发钩子
        context = HookContext(event="post_answer", data={"answer": "..."})
        result = await hooks.trigger("post_answer", context)

        if result.is_aborted:
            print("被钩子中断了")
    """

    def __init__(self):
        self._hooks: Dict[str, List[HookRegistration]] = {
            event.value: [] for event in HookEvent
        }
        self._execution_log: List[dict] = []

    def register(
        self,
        event: str,
        callback: HookFunction,
        name: str = "",
        priority: int = 100,
        run_in_background: bool = False,
    ):
        """
        注册钩子

        Args:
            event: 事件类型
            callback: 钩子回调函数
            name: 钩子名称
            priority: 优先级（数字越小越先执行）
            run_in_background: 是否后台执行
        """
        if event not in self._hooks:
            logger.warning("[Hook] 未知事件类型: %s", event)
            self._hooks[event] = []

        registration = HookRegistration(
            event=event,
            callback=callback,
            name=name or f"hook_{event}_{len(self._hooks[event])}",
            priority=priority,
            run_in_background=run_in_background,
        )

        self._hooks[event].append(registration)
        # 按优先级排序
        self._hooks[event].sort(key=lambda h: h.priority)

        logger.info("[Hook] 注册钩子: event=%s, name=%s, priority=%d",
                     event, registration.name, priority)

    def unregister(self, event: str, name: str):
        """注销指定钩子"""
        if event in self._hooks:
            self._hooks[event] = [
                h for h in self._hooks[event] if h.name != name
            ]

    async def trigger(self, event: str, context: HookContext) -> HookContext:
        """
        触发钩子链

        按优先级顺序执行所有注册的钩子。
        如果某个钩子调用了 context.abort()，后续钩子不再执行。

        Args:
            event: 事件类型
            context: 钩子上下文

        Returns:
            执行后的上下文（可能被修改）
        """
        hooks = self._hooks.get(event, [])
        if not hooks:
            return context

        logger.debug("[Hook] 触发事件 %s, 共 %d 个钩子", event, len(hooks))

        background_tasks = []

        for hook in hooks:
            if context.is_aborted:
                logger.info("[Hook] 事件 %s 被钩子 %s 中断", event, hook.name)
                break

            start = time.time()

            try:
                if hook.run_in_background:
                    # 后台执行，不等待结果
                    task = asyncio.create_task(hook.callback(context))
                    background_tasks.append((hook.name, task))
                else:
                    # 同步执行，等待结果
                    context = await hook.callback(context)

                elapsed = time.time() - start
                self._execution_log.append({
                    "event": event,
                    "hook": hook.name,
                    "elapsed_ms": round(elapsed * 1000, 1),
                    "aborted": context.is_aborted,
                    "modified": context.is_modified,
                    "background": hook.run_in_background,
                })

            except Exception as e:
                logger.error(
                    "[Hook] 钩子执行异常: event=%s, hook=%s, error=%s",
                    event, hook.name, e
                )

        return context

    def has_hooks(self, event: str) -> bool:
        """检查是否有注册的钩子"""
        return bool(self._hooks.get(event))

    def get_registered_hooks(self) -> Dict[str, List[str]]:
        """获取所有已注册的钩子信息"""
        return {
            event: [h.name for h in hooks]
            for event, hooks in self._hooks.items()
            if hooks
        }

    def get_execution_log(self, limit: int = 50) -> List[dict]:
        """获取最近的执行日志"""
        return self._execution_log[-limit:]

    def clear_all(self):
        """清除所有注册的钩子"""
        for event in self._hooks:
            self._hooks[event] = []
        self._execution_log.clear()


# ======================== 内置钩子工厂 ========================

def create_evaluation_hook(evaluation_agent) -> HookFunction:
    """创建评估钩子：每次回答后自动触发评估"""
    async def hook(ctx: HookContext) -> HookContext:
        answer = ctx.data.get("answer", "")
        question = ctx.data.get("question", "")
        stage = ctx.stage
        turn = ctx.data.get("turn_number", 0)

        if answer and question:
            evaluation = await evaluation_agent.evaluate_async(
                question=question,
                answer=answer,
                stage=stage,
                turn_number=turn,
            )
            ctx.set_data("evaluation", {
                "verdict": evaluation.verdict,
                "score": evaluation.overall_score,
                "follow_up": evaluation.follow_up_suggestion,
            })

        return ctx

    return hook


def create_stage_guard_hook(min_questions: int = 2) -> HookFunction:
    """创建阶段守卫钩子：至少问 N 个问题才能切换阶段"""
    async def hook(ctx: HookContext) -> HookContext:
        question_count = ctx.data.get("question_count", 0)
        if question_count < min_questions:
            logger.info(
                "[Hook] 阶段守卫：已问 %d 个问题，需至少 %d 个，阻止切换",
                question_count, min_questions
            )
            ctx.abort()
        return ctx

    return hook


def create_memory_update_hook(session_memory) -> HookFunction:
    """创建记忆更新钩子：每次回答后更新会话记忆"""
    async def hook(ctx: HookContext) -> HookContext:
        answer = ctx.data.get("answer", "")
        question = ctx.data.get("question", "")
        stage = ctx.stage
        evaluation = ctx.data.get("evaluation")

        session_memory.update_from_turn(
            stage=stage,
            question=question,
            answer=answer,
            evaluation=evaluation,
        )

        return ctx

    return hook


def create_budget_check_hook(token_tracker) -> HookFunction:
    """创建预算检查钩子：超预算时发出警告"""
    async def hook(ctx: HookContext) -> HookContext:
        if token_tracker.is_over_budget():
            ctx.set_data("budget_warning", {
                "message": "Token 预算已超限",
                "total_cost": token_tracker.total_cost,
                "budget": token_tracker.budget_usd,
            })
            logger.warning("[Hook] Token 预算超限!")
        return ctx

    return hook
