"""
面试技能抽象基类 —— 借鉴 Claude Code 的 Tool 抽象设计

核心设计：
1. 统一的技能接口（输入验证、权限检查、执行、结果输出）
2. 工厂函数模式（提供安全的默认值）
3. 技能注册与发现机制
4. 阶段感知（不同阶段启用不同技能）
5. 并发安全声明

参考：Claude Code src/Tool.ts (793行)
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum

from loguru import logger


# ======================== 数据模型 ========================

@dataclass
class SkillContext:
    """技能执行上下文"""
    stage: str                              # 当前面试阶段
    user_msg: str                           # 候选人的最新消息
    resume_summary: str                     # 简历摘要
    conversation_history: List[Dict]        # 对话历史
    candidate_profile: Dict                 # 候选人画像
    session_memory: Dict                    # 会话记忆
    question_count: int = 0                 # 当前阶段已问问题数
    position: str = ""                      # 目标岗位
    plan: Optional[Dict] = None            # 面试计划
    evaluation_history: List[Dict] = field(default_factory=list)  # 历史评估


@dataclass
class SkillResult:
    """技能执行结果"""
    output: str                             # 主输出文本
    metadata: Dict[str, Any] = field(default_factory=dict)
    should_update_profile: bool = False     # 是否需要更新候选人画像
    profile_updates: Dict[str, Any] = field(default_factory=dict)
    suggested_follow_up: str = ""           # 建议的追问方向
    confidence: float = 0.8                 # 结果置信度 (0-1)


# ======================== 技能基类 ========================

class InterviewSkill(ABC):
    """
    面试技能抽象基类

    每个技能必须声明：
    - 何时可用（阶段限制）
    - 是否可并行执行
    - 是否影响面试状态
    - 输入验证规则

    子类必须实现：
    - execute(): 执行技能
    - get_prompt(): 生成技能的 Prompt
    """

    name: str = "unnamed_skill"
    description: str = "未描述的技能"
    when_to_use: str = "通用场景"

    # 可用阶段（空列表表示所有阶段可用）
    available_stages: List[str] = []

    def is_enabled(self, stage: str) -> bool:
        """当前阶段是否可用"""
        if not self.available_stages:
            return True
        return stage in self.available_stages

    def is_concurrency_safe(self) -> bool:
        """是否可以和其他技能并行执行（默认不安全）"""
        return False

    def is_read_only(self) -> bool:
        """是否只读（不影响面试状态）（默认只读）"""
        return True

    def max_output_tokens(self) -> int:
        """最大输出 Token 数"""
        return 500

    def validate_input(self, context: SkillContext) -> Optional[str]:
        """
        输入验证，返回 None 表示通过，否则返回错误信息
        """
        if not context.user_msg and not context.conversation_history:
            return "缺少对话上下文"
        return None

    @abstractmethod
    async def execute(self, context: SkillContext) -> SkillResult:
        """执行技能"""
        ...

    @abstractmethod
    def get_prompt(self, context: SkillContext) -> str:
        """生成技能的 Prompt"""
        ...


# ======================== 内置技能 ========================

class StarMethodSkill(InterviewSkill):
    """STAR 追问法技能"""
    name = "star_method"
    description = "使用 STAR 法则（Situation-Task-Action-Result）深入追问项目经历"
    when_to_use = "当需要深入了解候选人的项目经历时"
    available_stages = ["project_deep"]

    def is_concurrency_safe(self) -> bool:
        return True

    async def execute(self, context: SkillContext) -> SkillResult:
        # 分析候选人已经提供了 STAR 的哪些部分
        answer = context.user_msg
        provided = []
        missing = []

        situation_keywords = ["背景", "项目是", "当时", "场景"]
        task_keywords = ["负责", "任务", "职责", "目标"]
        action_keywords = ["做了", "实现", "采用", "使用了", "解决"]
        result_keywords = ["结果", "成效", "提升", "优化了", "最终"]

        if any(kw in answer for kw in situation_keywords):
            provided.append("Situation")
        else:
            missing.append("Situation（项目背景）")

        if any(kw in answer for kw in task_keywords):
            provided.append("Task")
        else:
            missing.append("Task（你的职责）")

        if any(kw in answer for kw in action_keywords):
            provided.append("Action")
        else:
            missing.append("Action（你做了什么）")

        if any(kw in answer for kw in result_keywords):
            provided.append("Result")
        else:
            missing.append("Result（成果和数据）")

        if missing:
            suggestion = f"候选人已描述了 {'/'.join(provided) or '无'}，建议追问 {'/'.join(missing)}"
        else:
            suggestion = "候选人已完整描述 STAR，可以深挖技术细节或换一个项目"

        return SkillResult(
            output=suggestion,
            metadata={"provided": provided, "missing": missing},
            suggested_follow_up=missing[0] if missing else "技术细节",
        )

    def get_prompt(self, context: SkillContext) -> str:
        return (
            "请使用 STAR 法则追问候选人的项目经历。"
            "重点关注候选人尚未提及的部分。"
        )


class DifficultyAdaptSkill(InterviewSkill):
    """难度自适应技能"""
    name = "difficulty_adapt"
    description = "根据候选人表现动态调整问题难度"
    when_to_use = "当需要根据候选人表现动态调整问题难度时"
    available_stages = ["basic_qa", "coding"]

    def is_concurrency_safe(self) -> bool:
        return True

    async def execute(self, context: SkillContext) -> SkillResult:
        profile = context.candidate_profile
        confidence = profile.get("confidence_signals", 0)
        hesitation = profile.get("hesitation_signals", 0)
        avg_length = profile.get("avg_answer_length", 50)

        # 判断当前难度是否合适
        if confidence > hesitation + 2 and avg_length > 100:
            recommendation = "提升难度"
            detail = "候选人表现自信且回答详细，建议提高问题难度"
            level = "hard"
        elif hesitation > confidence + 1 or avg_length < 30:
            recommendation = "降低难度"
            detail = "候选人多次犹豫或回答简短，建议降低难度或换方向"
            level = "easy"
        else:
            recommendation = "保持当前难度"
            detail = "候选人表现正常，继续当前难度"
            level = "medium"

        return SkillResult(
            output=detail,
            metadata={"recommendation": recommendation, "level": level},
            should_update_profile=True,
            profile_updates={"suggested_difficulty": level},
        )

    def get_prompt(self, context: SkillContext) -> str:
        return "根据候选人的历史表现，建议调整问题难度。"


class CodeReviewSkill(InterviewSkill):
    """代码审查技能"""
    name = "code_review"
    description = "对候选人提交的代码进行专业点评"
    when_to_use = "当候选人提交代码需要专业点评时"
    available_stages = ["coding"]

    async def execute(self, context: SkillContext) -> SkillResult:
        code = context.user_msg

        # 基本代码分析
        analysis = {
            "has_code": "【代码提交】" in code or "def " in code or "class " in code,
            "estimated_lines": code.count("\n") + 1,
            "has_comments": "#" in code or "//" in code,
        }

        if analysis["has_code"]:
            output = "候选人已提交代码，请从正确性、效率、代码风格三个维度点评"
        else:
            output = "候选人尚未提交代码，请引导其完成编码"

        return SkillResult(
            output=output,
            metadata=analysis,
        )

    def get_prompt(self, context: SkillContext) -> str:
        return (
            "请对候选人提交的代码进行审查，关注：\n"
            "1. 正确性：逻辑是否正确，边界情况处理\n"
            "2. 效率：时间/空间复杂度\n"
            "3. 代码风格：命名规范、可读性"
        )


class KnowledgeGraphSkill(InterviewSkill):
    """知识图谱关联技能"""
    name = "knowledge_graph"
    description = "从一个知识点关联到相关知识点进行追问"
    when_to_use = "当需要从一个知识点关联到相关知识点进行追问时"
    available_stages = ["basic_qa"]

    def is_concurrency_safe(self) -> bool:
        return True

    # 简化的知识关联图
    KNOWLEDGE_GRAPH = {
        "HashMap": ["红黑树", "ConcurrentHashMap", "哈希冲突", "扩容机制"],
        "多线程": ["线程池", "锁机制", "volatile", "CAS", "AQS"],
        "JVM": ["垃圾回收", "类加载", "内存模型", "JIT编译"],
        "Spring": ["IoC", "AOP", "Bean生命周期", "事务管理"],
        "数据库": ["索引", "事务隔离", "MVCC", "分库分表", "SQL优化"],
        "Redis": ["数据结构", "持久化", "集群", "缓存击穿", "过期策略"],
        "网络": ["TCP/IP", "HTTP", "HTTPS", "WebSocket", "DNS"],
        "设计模式": ["单例", "工厂", "观察者", "策略", "代理"],
        "算法": ["排序", "二分查找", "动态规划", "贪心", "回溯"],
        "操作系统": ["进程线程", "内存管理", "文件系统", "死锁"],
    }

    async def execute(self, context: SkillContext) -> SkillResult:
        answer = context.user_msg
        related_topics = []

        # 检查回答中涉及的知识点
        for topic, relations in self.KNOWLEDGE_GRAPH.items():
            if topic in answer:
                related_topics.extend(relations)

        if related_topics:
            # 去重，取前3个
            unique_topics = list(dict.fromkeys(related_topics))[:3]
            output = f"可以关联追问的知识点：{', '.join(unique_topics)}"
        else:
            output = "未检测到明确的知识关联，建议根据岗位要求选择方向"

        return SkillResult(
            output=output,
            metadata={"related_topics": related_topics[:5]},
            suggested_follow_up=related_topics[0] if related_topics else "",
        )

    def get_prompt(self, context: SkillContext) -> str:
        return "根据候选人回答涉及的知识点，推荐关联的追问方向。"


# ======================== 技能注册表 ========================

class SkillRegistry:
    """
    技能注册表 —— 管理所有可用技能

    使用方式：
        registry = SkillRegistry()
        registry.register(StarMethodSkill())
        registry.register(DifficultyAdaptSkill())

        # 获取当前阶段可用的技能
        skills = registry.get_available_skills("project_deep")

        # 根据上下文自动选择技能
        selected = registry.auto_select(context)
    """

    def __init__(self):
        self._skills: Dict[str, InterviewSkill] = {}

    def register(self, skill: InterviewSkill):
        """注册技能"""
        self._skills[skill.name] = skill
        logger.info("[SkillRegistry] 注册技能: %s", skill.name)

    def unregister(self, skill_name: str):
        """注销技能"""
        self._skills.pop(skill_name, None)

    def get_skill(self, name: str) -> Optional[InterviewSkill]:
        """获取指定技能"""
        return self._skills.get(name)

    def get_all_skills(self) -> List[InterviewSkill]:
        """获取所有已注册技能"""
        return list(self._skills.values())

    def get_available_skills(self, stage: str) -> List[InterviewSkill]:
        """获取当前阶段可用的技能"""
        return [
            skill for skill in self._skills.values()
            if skill.is_enabled(stage)
        ]

    def get_concurrent_safe_skills(self, stage: str) -> List[InterviewSkill]:
        """获取可并行执行的技能"""
        return [
            skill for skill in self.get_available_skills(stage)
            if skill.is_concurrency_safe()
        ]

    def auto_select(self, context: SkillContext) -> List[InterviewSkill]:
        """根据上下文自动选择合适的技能"""
        available = self.get_available_skills(context.stage)
        selected = []

        for skill in available:
            error = skill.validate_input(context)
            if error is None:
                selected.append(skill)

        return selected

    def list_skills_info(self) -> List[dict]:
        """获取所有技能的信息（用于展示）"""
        return [
            {
                "name": skill.name,
                "description": skill.description,
                "when_to_use": skill.when_to_use,
                "available_stages": skill.available_stages,
                "is_concurrent_safe": skill.is_concurrency_safe(),
                "is_read_only": skill.is_read_only(),
            }
            for skill in self._skills.values()
        ]


# ======================== 全局注册表 ========================

def create_default_registry() -> SkillRegistry:
    """创建并注册所有内置技能"""
    registry = SkillRegistry()
    registry.register(StarMethodSkill())
    registry.register(DifficultyAdaptSkill())
    registry.register(CodeReviewSkill())
    registry.register(KnowledgeGraphSkill())
    logger.info("[SkillRegistry] 已注册 %d 个内置技能", len(registry.get_all_skills()))
    return registry
