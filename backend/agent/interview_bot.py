"""
面试机器人 —— 多 Agent 架构（借鉴闲鱼客服机器人深度改造）

核心设计：
1. 阶段路由器：三级路由策略（关键词→正则→LLM兜底），精准判断阶段转换
2. 专业 Agent：每个面试阶段有专门的 Agent，拥有差异化策略
3. 动态参数：根据面试进度动态调整 temperature、max_tokens 等
4. 安全过滤：防止角色混乱、信息泄露、格式异常
5. 候选人画像：实时追踪候选人表现，影响提问策略
"""

import os
import re
from typing import List, Dict, AsyncIterator
from openai import AsyncOpenAI
from loguru import logger

from agent.state_machine import InterviewStage
from config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL


class InterviewBot:
    """面试机器人主类"""

    def __init__(self, resume_summary: str, position: str):
        self.resume_summary = resume_summary
        self.position = position

        # 初始化 OpenAI 客户端
        self.client = AsyncOpenAI(
            api_key=LLM_API_KEY,
            base_url=LLM_BASE_URL,
        )
        self.model = LLM_MODEL

        # 加载所有 prompt
        self._load_prompts()

        # 初始化各阶段 Agent
        self._init_agents()

        # 初始化阶段路由器
        self.router = StageRouter(self.agents["classify"], self.client, self.model)

        # 候选人实时画像（面试过程中积累）
        self.candidate_profile = CandidateProfile()

    def _load_prompts(self):
        """加载所有 Agent 的 prompt，优先加载用户自定义文件，否则使用默认文件"""
        prompt_dir = os.path.join(os.path.dirname(__file__), "prompts")

        def load_prompt(name: str) -> str:
            """尝试加载提示词文件"""
            # 优先尝试加载自定义 prompt
            target_path = os.path.join(prompt_dir, f"{name}.txt")
            if os.path.exists(target_path):
                file_path = target_path
            else:
                # 尝试默认提示词
                file_path = os.path.join(prompt_dir, f"{name}_default.txt")

            if not os.path.exists(file_path):
                logger.warning(f"Prompt 文件不存在: {file_path}")
                return ""

            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                logger.debug(f"已加载 {name} 提示词，路径: {file_path}, 长度: {len(content)} 字符")
                return content

        self.prompts = {
            "classify": load_prompt("classify_prompt"),
            "opening": load_prompt("opening_prompt"),
            "coding": load_prompt("coding_prompt"),
            "basic_qa": load_prompt("basic_qa_prompt"),
            "project": load_prompt("project_prompt"),
            "summary": load_prompt("summary_prompt"),
        }
        logger.info("成功加载所有面试 prompt")

    def _init_agents(self):
        """初始化各阶段 Agent"""
        safety_filter = SafetyFilter()

        self.agents = {
            "classify": ClassifyAgent(self.client, self.model, self.prompts["classify"], safety_filter),
            "opening": OpeningAgent(self.client, self.model, self.prompts["opening"], safety_filter),
            "coding": CodingAgent(self.client, self.model, self.prompts["coding"], safety_filter),
            "basic_qa": BasicQAAgent(self.client, self.model, self.prompts["basic_qa"], safety_filter),
            "project": ProjectAgent(self.client, self.model, self.prompts["project"], safety_filter),
            "summary": SummaryAgent(self.client, self.model, self.prompts["summary"], safety_filter),
        }

    def get_agent_for_stage(self, stage: InterviewStage) -> "BaseAgent":
        """根据阶段获取对应的 Agent"""
        stage_to_agent = {
            InterviewStage.OPENING: "opening",
            InterviewStage.CODING: "coding",
            InterviewStage.BASIC_QA: "basic_qa",
            InterviewStage.PROJECT_DEEP: "project",
            InterviewStage.SUMMARY: "summary",
        }
        agent_name = stage_to_agent.get(stage, "opening")
        return self.agents[agent_name]

    def format_history(self, context: List[Dict]) -> str:
        """格式化对话历史，返回完整的对话记录（借鉴闲鱼的 format_history）"""
        user_assistant_msgs = [msg for msg in context if msg['role'] in ['user', 'assistant']]
        lines = []
        for msg in user_assistant_msgs:
            role = "面试官" if msg["role"] == "assistant" else "候选人"
            lines.append(f"{role}: {msg['content']}")
        return "\n".join(lines)

    async def generate_reply(
        self,
        user_msg: str,
        stage: InterviewStage,
        context: List[Dict],
        question_count: int,
    ) -> AsyncIterator[str]:
        """
        生成面试官回复

        Args:
            user_msg: 用户消息
            stage: 当前面试阶段
            context: 对话历史
            question_count: 当前阶段已问问题数

        Yields:
            回复的 token
        """
        # 获取当前阶段的 Agent
        agent = self.get_agent_for_stage(stage)

        # 格式化上下文
        formatted_context = self.format_history(context)

        # 生成回复
        async for token in agent.generate(
            user_msg=user_msg,
            resume_summary=self.resume_summary,
            position=self.position,
            context=context,
            formatted_context=formatted_context,
            question_count=question_count,
            candidate_profile=self.candidate_profile,
        ):
            yield token

        # 更新候选人画像
        self.candidate_profile.update_from_answer(user_msg, stage)

    async def check_stage_complete(
        self,
        stage: InterviewStage,
        context: List[Dict],
        last_response: str,
    ) -> bool:
        """
        检查当前阶段是否完成（三级路由策略）

        Args:
            stage: 当前阶段
            context: 对话历史
            last_response: 面试官最后的回复

        Returns:
            是否应该切换到下一阶段
        """
        return await self.router.check_transition(stage, context, last_response)

    def reload_prompts(self):
        """重新加载所有提示词（热更新支持）"""
        logger.info("正在重新加载提示词...")
        self._load_prompts()
        self._init_agents()
        logger.info("提示词重新加载完成")


class CandidateProfile:
    """
    候选人实时画像（借鉴闲鱼的议价次数追踪思路，面试场景下追踪候选人表现）

    在面试过程中动态积累候选人信息，影响后续提问策略。
    """

    def __init__(self):
        self.answer_lengths: List[int] = []  # 每次回答的长度
        self.stage_answer_count: Dict[str, int] = {}  # 每个阶段的回答次数
        self.has_submitted_code: bool = False  # 是否提交过代码
        self.mentioned_projects: List[str] = []  # 提到的项目关键词
        self.confidence_signals: int = 0  # 自信信号计数（回答详细、主动展开）
        self.hesitation_signals: int = 0  # 犹豫信号计数（回答短、说"不太确定"等）

    def update_from_answer(self, answer: str, stage: InterviewStage):
        """根据候选人回答更新画像"""
        self.answer_lengths.append(len(answer))

        stage_key = stage.value
        self.stage_answer_count[stage_key] = self.stage_answer_count.get(stage_key, 0) + 1

        # 检测代码提交
        if "【代码提交】" in answer:
            self.has_submitted_code = True

        # 检测犹豫信号
        hesitation_keywords = ["不太确定", "不太清楚", "可能是", "大概", "好像", "不太记得", "不确定", "忘了"]
        if any(kw in answer for kw in hesitation_keywords):
            self.hesitation_signals += 1

        # 检测自信信号（回答超过100字，或使用专业术语）
        if len(answer) > 100:
            self.confidence_signals += 1

    @property
    def avg_answer_length(self) -> float:
        """平均回答长度"""
        if not self.answer_lengths:
            return 0
        return sum(self.answer_lengths) / len(self.answer_lengths)

    @property
    def engagement_level(self) -> str:
        """参与度评估"""
        avg = self.avg_answer_length
        if avg > 150:
            return "高"
        elif avg > 50:
            return "中"
        else:
            return "低"

    def get_summary(self) -> str:
        """生成画像摘要（注入到 prompt 中辅助决策）"""
        parts = [f"▲候选人画像：参与度={self.engagement_level}"]
        if self.hesitation_signals > 0:
            parts.append(f"犹豫次数={self.hesitation_signals}")
        if self.confidence_signals > 0:
            parts.append(f"自信次数={self.confidence_signals}")
        if self.has_submitted_code:
            parts.append("已提交代码")
        return "，".join(parts)


class StageRouter:
    """
    阶段路由器 —— 三级路由策略（借鉴闲鱼的 IntentRouter 设计）

    1. 关键词匹配（最快）
    2. 正则模式匹配（精准）
    3. LLM 兜底判断（最智能）
    """

    def __init__(self, classify_agent: "ClassifyAgent", client: AsyncOpenAI, model: str):
        self.classify_agent = classify_agent
        self.client = client
        self.model = model

        # 各阶段的过渡关键词和正则模式
        self.transition_rules = {
            InterviewStage.OPENING: {
                'keywords': ["进入编程环节", "编程考察", "算法题", "代码编辑器", "开始做题"],
                'patterns': [
                    r'接下来.*编程',
                    r'请看.*算法题',
                    r'进入.*编程.*环节',
                ]
            },
            InterviewStage.CODING: {
                'keywords': ["编程环节到此结束", "进入基础知识", "基础考察", "技术问题"],
                'patterns': [
                    r'编程.*结束',
                    r'进入.*基础',
                    r'接下来.*技术问题',
                ]
            },
            InterviewStage.BASIC_QA: {
                'keywords': ["项目经历", "聊聊项目", "深入了解", "项目部分", "了解.*项目"],
                'patterns': [
                    r'了解.*项目',
                    r'聊聊.*项目',
                    r'进入.*项目',
                ]
            },
            InterviewStage.PROJECT_DEEP: {
                'keywords': ["总结环节", "最后的总结", "面试即将结束"],
                'patterns': [
                    r'进入.*总结',
                    r'最后.*环节',
                    r'面试.*即将.*结束',
                ]
            },
            InterviewStage.SUMMARY: {
                'keywords': ["面试就到这里", "感谢你的参与", "祝你顺利", "后续结果"],
                'patterns': [
                    r'面试.*到.*这里',
                    r'感谢.*参与',
                    r'祝.*顺利',
                ]
            },
        }

    async def check_transition(
        self,
        stage: InterviewStage,
        context: List[Dict],
        last_response: str,
    ) -> bool:
        """
        三级路由检查是否应该切换阶段

        1. 关键词快速匹配
        2. 正则模式匹配
        3. LLM 兜底判断
        """
        rules = self.transition_rules.get(stage, {})

        # 1. 关键词匹配（最快）
        keywords = rules.get('keywords', [])
        if any(kw in last_response for kw in keywords):
            logger.info(f"[Router] 关键词匹配，阶段 {stage.value} 完成")
            return True

        # 2. 正则模式匹配（精准）
        patterns = rules.get('patterns', [])
        for pattern in patterns:
            if re.search(pattern, last_response):
                logger.info(f"[Router] 正则匹配 '{pattern}'，阶段 {stage.value} 完成")
                return True

        # 3. LLM 兜底判断（最智能，仅在前两步未匹配时启用）
        try:
            result = await self.classify_agent.classify(last_response, context)
            if result.strip().lower() == "yes":
                logger.info(f"[Router] LLM 判定阶段 {stage.value} 完成")
                return True
        except Exception as e:
            logger.warning(f"[Router] LLM 判定异常: {e}，保守不切换")

        return False


class SafetyFilter:
    """
    安全过滤模块（借鉴闲鱼的 _safe_filter 设计）

    防止面试官：
    1. 角色混乱（自我介绍、回答问题）
    2. 泄露元信息（提及 AI、阶段名等）
    3. 格式异常（LaTeX、Markdown代码块等）
    """

    def __init__(self):
        # 角色混乱检测关键词（面试官不应该说这些）
        self.role_confusion_patterns = [
            r'我叫\w+，来自',  # 面试官自我介绍
            r'我的学历是',
            r'我毕业于',
            r'我做过的项目有',
        ]

        # 元信息泄露关键词
        self.meta_leak_keywords = [
            "当前阶段是", "根据我的 prompt", "作为AI", "作为一个AI",
            "我是一个语言模型", "我的训练数据", "面试阶段为",
        ]

    def filter(self, text: str) -> str:
        """过滤不安全的输出"""
        if not text:
            return text

        # 1. 检测角色混乱
        for pattern in self.role_confusion_patterns:
            if re.search(pattern, text):
                logger.warning(f"[SafetyFilter] 检测到角色混乱: {pattern}")
                # 不直接替换，而是记录警告，让 Agent 自行纠正
                break

        # 2. 检测元信息泄露
        for keyword in self.meta_leak_keywords:
            if keyword in text:
                logger.warning(f"[SafetyFilter] 检测到元信息泄露: {keyword}")
                text = text.replace(keyword, "")

        # 3. 清理格式异常
        text = self._clean_format(text)

        return text

    def _clean_format(self, text: str) -> str:
        """清理格式异常"""
        # 移除 LaTeX \boxed{...}
        text = re.sub(r"\\boxed\{([^}]*)\}", r"\1", text)

        # 移除 Markdown 代码块标记（如果不是代码讨论场景）
        # 保留代码讨论中的代码块
        return text


class BaseAgent:
    """
    Agent 基类（借鉴闲鱼的 BaseAgent 设计，增强版）

    特性：
    1. 统一的消息构建模板
    2. 安全过滤
    3. 动态参数调整
    4. 候选人画像注入
    """

    def __init__(self, client: AsyncOpenAI, model: str, system_prompt: str, safety_filter: SafetyFilter):
        self.client = client
        self.model = model
        self.system_prompt = system_prompt
        self.safety_filter = safety_filter

    async def generate(
        self,
        user_msg: str,
        resume_summary: str,
        position: str,
        context: List[Dict],
        formatted_context: str,
        question_count: int,
        candidate_profile: CandidateProfile,
    ) -> AsyncIterator[str]:
        """生成回复（模板方法，子类可重写）"""
        messages = self._build_messages(
            user_msg, resume_summary, position,
            context, formatted_context, question_count, candidate_profile
        )
        temperature = self._calc_temperature(question_count, candidate_profile)

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=self._get_max_tokens(),
            stream=True,
        )

        buffer = []
        async for chunk in response:
            if chunk.choices[0].delta.content:
                token = chunk.choices[0].delta.content
                buffer.append(token)
                yield token

        # 流式结束后对完整文本做安全过滤（日志级别，不阻断输出）
        full_text = "".join(buffer)
        self.safety_filter.filter(full_text)

    def _build_messages(
        self,
        user_msg: str,
        resume_summary: str,
        position: str,
        context: List[Dict],
        formatted_context: str,
        question_count: int,
        candidate_profile: CandidateProfile,
    ) -> List[Dict]:
        """
        构建消息列表（借鉴闲鱼的信息注入方式）

        将简历、对话历史、候选人画像等信息全部注入到 system prompt 中，
        然后将最近的对话作为多轮消息传入。
        """
        # 构建增强版系统消息
        system_content = self.system_prompt.format(
            position=position,
            resume_summary=resume_summary,
            history=formatted_context,
            question_count=question_count,
        )

        # 注入候选人画像（借鉴闲鱼的议价次数注入方式）
        if candidate_profile:
            system_content += f"\n\n{candidate_profile.get_summary()}"

        # 注入当前阶段问答轮次
        system_content += f"\n▲当前阶段已进行 {question_count} 轮对话"

        messages = [{"role": "system", "content": system_content}]

        # 添加对话历史（作为多轮对话，保留最近10轮）
        for msg in context[-10:]:
            messages.append({"role": msg["role"], "content": msg["content"]})

        # 添加当前用户消息
        messages.append({"role": "user", "content": user_msg})

        return messages

    def _calc_temperature(self, question_count: int, candidate_profile: CandidateProfile) -> float:
        """
        动态温度策略（借鉴闲鱼 PriceAgent 的动态温度设计）

        - 面试初期（开场）: 偏高温度，更自然
        - 技术考察: 较低温度，更准确
        - 根据候选人参与度调整
        """
        return 0.7  # 基类默认值，子类可重写

    def _get_max_tokens(self) -> int:
        """最大输出 token 数，子类可重写"""
        return 500

    def _format_history(self, context: List[Dict]) -> str:
        """格式化对话历史为字符串"""
        lines = []
        for msg in context:
            role = "面试官" if msg["role"] == "assistant" else "候选人"
            lines.append(f"{role}: {msg['content']}")
        return "\n".join(lines)


class ClassifyAgent(BaseAgent):
    """
    意图分类 Agent（借鉴闲鱼的 ClassifyAgent）

    仅负责判断阶段是否完成，返回 yes/no
    """

    async def classify(self, last_response: str, context: List[Dict]) -> str:
        """分类：判断面试官的回复是否表示阶段结束"""
        # 提取最近3轮对话作为上下文
        recent_context = ""
        if context:
            recent = context[-6:]  # 最近3轮
            for msg in recent:
                role = "面试官" if msg["role"] == "assistant" else "候选人"
                recent_context += f"{role}: {msg['content']}\n"

        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": f"最近对话:\n{recent_context}\n\n面试官最新回复: {last_response}\n\n请判断这段回复是否表示当前阶段结束，仅返回 yes 或 no"},
        ]

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.1,  # 分类任务用极低温度
            max_tokens=10,
        )

        return response.choices[0].message.content.strip().lower()


class OpeningAgent(BaseAgent):
    """
    开场寒暄 Agent

    策略：
    - 高温度，自然亲切
    - 根据候选人回答长度决定是否追问
    - 短回复风格
    """

    def _calc_temperature(self, question_count: int, candidate_profile: CandidateProfile) -> float:
        """开场阶段用较高温度，更自然"""
        return 0.8

    def _get_max_tokens(self) -> int:
        """开场白要简短"""
        return 300

    def _build_messages(
        self,
        user_msg: str,
        resume_summary: str,
        position: str,
        context: List[Dict],
        formatted_context: str,
        question_count: int,
        candidate_profile: CandidateProfile,
    ) -> List[Dict]:
        """开场阶段增强消息构建"""
        messages = super()._build_messages(
            user_msg, resume_summary, position,
            context, formatted_context, question_count, candidate_profile
        )

        # 如果候选人回答太短，提示 Agent 追问
        if candidate_profile and candidate_profile.avg_answer_length < 30 and question_count > 0:
            messages[0]["content"] += "\n\n▲提示：候选人回答较简短，建议友好追问更多信息"

        return messages


class CodingAgent(BaseAgent):
    """
    编程考察 Agent

    策略：
    - 低温度，点评要准确
    - 检测代码提交
    - 追问复杂度和优化
    """

    def _calc_temperature(self, question_count: int, candidate_profile: CandidateProfile) -> float:
        """代码点评用较低温度"""
        return 0.5

    def _get_max_tokens(self) -> int:
        """代码点评需要更多空间"""
        return 600

    def _build_messages(
        self,
        user_msg: str,
        resume_summary: str,
        position: str,
        context: List[Dict],
        formatted_context: str,
        question_count: int,
        candidate_profile: CandidateProfile,
    ) -> List[Dict]:
        """编程阶段增强消息构建"""
        messages = super()._build_messages(
            user_msg, resume_summary, position,
            context, formatted_context, question_count, candidate_profile
        )

        # 检测是否提交了代码
        has_code = "【代码提交】" in user_msg
        messages[0]["content"] += f"\n\n▲候选人是否已提交代码: {'是' if has_code else '否'}"

        if has_code:
            messages[0]["content"] += "\n▲请仔细点评代码的正确性、复杂度和代码风格"
        else:
            messages[0]["content"] += "\n▲候选人尚未提交代码，请引导其在编辑器中完成"

        return messages


class BasicQAAgent(BaseAgent):
    """
    基础知识考察 Agent

    策略：
    - 中等温度
    - 根据候选人表现动态调整难度
    - 避免重复已问过的方向
    """

    def _calc_temperature(self, question_count: int, candidate_profile: CandidateProfile) -> float:
        """
        动态温度策略（借鉴闲鱼 PriceAgent 的梯度策略）

        - 第一个问题偏简单 → 低温度
        - 后续问题根据候选人表现调整
        """
        base_temp = 0.5
        # 如果候选人表现好（自信信号多），提高温度出更有挑战的问题
        if candidate_profile and candidate_profile.confidence_signals > candidate_profile.hesitation_signals:
            base_temp = min(0.5 + question_count * 0.1, 0.8)
        return base_temp

    def _build_messages(
        self,
        user_msg: str,
        resume_summary: str,
        position: str,
        context: List[Dict],
        formatted_context: str,
        question_count: int,
        candidate_profile: CandidateProfile,
    ) -> List[Dict]:
        """基础QA阶段增强消息构建"""
        messages = super()._build_messages(
            user_msg, resume_summary, position,
            context, formatted_context, question_count, candidate_profile
        )

        # 根据候选人表现调整提问策略
        if candidate_profile:
            if candidate_profile.hesitation_signals > candidate_profile.confidence_signals:
                messages[0]["content"] += "\n\n▲策略提示：候选人此前回答不太自信，建议从基础概念入手，逐步深入"
            elif candidate_profile.confidence_signals >= 2:
                messages[0]["content"] += "\n\n▲策略提示：候选人表现不错，可以提问更有深度的问题"

        return messages


class ProjectAgent(BaseAgent):
    """
    项目深挖 Agent

    策略：
    - 中高温度，追问要自然
    - 使用 STAR 法则
    - 根据候选人回答深度决定追问方向
    """

    def _calc_temperature(self, question_count: int, candidate_profile: CandidateProfile) -> float:
        """项目追问用中高温度，更自然"""
        return 0.7

    def _get_max_tokens(self) -> int:
        """项目追问可以稍长"""
        return 400

    def _build_messages(
        self,
        user_msg: str,
        resume_summary: str,
        position: str,
        context: List[Dict],
        formatted_context: str,
        question_count: int,
        candidate_profile: CandidateProfile,
    ) -> List[Dict]:
        """项目深挖阶段增强消息构建"""
        messages = super()._build_messages(
            user_msg, resume_summary, position,
            context, formatted_context, question_count, candidate_profile
        )

        # 注入 STAR 追问策略
        if question_count == 0:
            messages[0]["content"] += "\n\n▲策略：先让候选人选择一个最自豪的项目介绍"
        elif question_count <= 2:
            messages[0]["content"] += "\n\n▲策略：使用 STAR 法则追问 Situation/Task"
        else:
            messages[0]["content"] += "\n\n▲策略：追问 Action/Result，关注技术决策和个人贡献"

        return messages


class SummaryAgent(BaseAgent):
    """
    总结 Agent

    策略：
    - 高温度，语气温暖
    - 简短友好
    """

    def _calc_temperature(self, question_count: int, candidate_profile: CandidateProfile) -> float:
        """总结阶段温暖友好"""
        return 0.8

    def _get_max_tokens(self) -> int:
        """总结要简短"""
        return 300
