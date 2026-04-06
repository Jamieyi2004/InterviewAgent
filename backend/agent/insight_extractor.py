"""
面试洞察提取 Agent —— 借鉴 Claude Code 的 Memory Extraction Agent 设计

核心设计：
1. 后台异步运行，从对话中提取长期有价值的洞察
2. 增量提取（每 N 轮对话提取一次，避免重复）
3. 洞察分类：技术能力信号、沟通模式、思维特征、策略建议
4. 实时反馈给面试策略，影响后续提问方向
5. 写入候选人档案，用于最终报告生成

参考：
- Claude Code src/services/extractMemories/prompts.ts
- Claude Code src/services/extractMemories/extractMemories.ts

关键设计借鉴：
- Fork 机制：洞察提取与主对话流解耦
- 有限轮次：只做 1 轮 LLM 调用
- 去重机制：与现有洞察合并，不重复提取
"""

import json
import asyncio
from typing import Dict, List, Optional
from dataclasses import dataclass, field

from openai import AsyncOpenAI
from loguru import logger

from config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL


# ======================== 数据模型 ========================

@dataclass
class InsightCategory:
    """洞察类别"""
    category: str           # 类别名
    items: List[str]        # 洞察条目
    confidence: str = "medium"  # 置信度：high/medium/low


@dataclass
class CandidateInsights:
    """候选人洞察集合"""
    technical_signals: List[str] = field(default_factory=list)      # 技术能力信号
    knowledge_gaps: List[str] = field(default_factory=list)          # 知识盲区
    communication_style: List[str] = field(default_factory=list)     # 沟通风格特征
    thinking_patterns: List[str] = field(default_factory=list)       # 思维模式特征
    strategy_suggestions: List[str] = field(default_factory=list)    # 面试策略建议
    notable_quotes: List[str] = field(default_factory=list)          # 值得记录的原话

    _extraction_count: int = 0       # 已提取次数
    _last_message_index: int = 0     # 上次提取时的消息索引

    def merge(self, new_insights: "CandidateInsights"):
        """合并新洞察（去重）"""
        self.technical_signals = self._deduplicate(
            self.technical_signals + new_insights.technical_signals
        )
        self.knowledge_gaps = self._deduplicate(
            self.knowledge_gaps + new_insights.knowledge_gaps
        )
        self.communication_style = self._deduplicate(
            self.communication_style + new_insights.communication_style
        )
        self.thinking_patterns = self._deduplicate(
            self.thinking_patterns + new_insights.thinking_patterns
        )
        self.strategy_suggestions = new_insights.strategy_suggestions or self.strategy_suggestions
        self.notable_quotes = self._deduplicate(
            self.notable_quotes + new_insights.notable_quotes
        )
        self._extraction_count += 1

    @staticmethod
    def _deduplicate(items: List[str]) -> List[str]:
        """去重（保持顺序）"""
        seen = set()
        result = []
        for item in items:
            normalized = item.strip().lower()
            if normalized not in seen:
                seen.add(normalized)
                result.append(item.strip())
        return result

    def to_dict(self) -> dict:
        return {
            "technical_signals": self.technical_signals,
            "knowledge_gaps": self.knowledge_gaps,
            "communication_style": self.communication_style,
            "thinking_patterns": self.thinking_patterns,
            "strategy_suggestions": self.strategy_suggestions,
            "notable_quotes": self.notable_quotes,
            "extraction_count": self._extraction_count,
        }

    def to_prompt_text(self) -> str:
        """转换为可注入 Prompt 的文本"""
        parts = ["## 候选人洞察（后台分析）"]

        if self.technical_signals:
            parts.append("**技术能力信号：** " + "；".join(self.technical_signals[:5]))
        if self.knowledge_gaps:
            parts.append("**知识盲区：** " + "；".join(self.knowledge_gaps[:5]))
        if self.communication_style:
            parts.append("**沟通风格：** " + "；".join(self.communication_style[:3]))
        if self.thinking_patterns:
            parts.append("**思维特征：** " + "；".join(self.thinking_patterns[:3]))
        if self.strategy_suggestions:
            parts.append("**策略建议：** " + "；".join(self.strategy_suggestions[:3]))

        return "\n".join(parts) if len(parts) > 1 else ""


# ======================== 提取 Prompt ========================

INSIGHT_EXTRACTION_PROMPT = """你是面试洞察分析师。请分析最近的面试对话，提取有价值的候选人洞察。

**注意：**
- 只提取新的洞察（已有洞察不要重复）
- 每个洞察要有具体的对话证据
- 策略建议要可操作

**已有洞察（避免重复）：**
{existing_insights}

**最近的面试对话：**
{recent_conversation}

**当前面试阶段：** {stage}

请以严格 JSON 格式输出新发现的洞察：
{{
    "technical_signals": [
        "候选人展示了XX能力，证据：回答了'...'",
        "候选人对YY理解较深，主动提到了底层原理"
    ],
    "knowledge_gaps": [
        "候选人对XX概念理解模糊，回答时说了'不太确定'"
    ],
    "communication_style": [
        "回答风格：结构化/发散/简洁/冗长",
        "是否主动展开还是需要追问"
    ],
    "thinking_patterns": [
        "分析问题的方式：自顶向下/自底向上",
        "是否考虑边界情况和异常处理"
    ],
    "strategy_suggestions": [
        "建议接下来追问XX方向",
        "建议调整难度到XX级别"
    ],
    "notable_quotes": [
        "候选人说的值得记录的原话"
    ]
}}

**规则：**
- 每个类别最多 3 条新洞察
- 只返回新发现的（不要重复已有洞察）
- 如果某个类别没有新发现，返回空列表 []
"""


# ======================== 核心类 ========================

class InterviewInsightExtractor:
    """
    面试洞察提取 Agent

    使用方式：
        extractor = InterviewInsightExtractor()

        # 每 N 轮对话后提取洞察
        if extractor.should_extract(current_message_count):
            insights = await extractor.extract_insights(
                recent_messages=messages[-10:],
                stage="basic_qa"
            )

        # 获取当前所有洞察（用于注入 Prompt）
        prompt_text = extractor.insights.to_prompt_text()

        # 获取洞察字典（用于报告）
        insight_dict = extractor.insights.to_dict()
    """

    EXTRACT_INTERVAL = 6  # 每 6 条消息（3轮对话）提取一次

    def __init__(self):
        self.client = AsyncOpenAI(api_key=LLM_API_KEY, base_url=LLM_BASE_URL)
        self.model = LLM_MODEL
        self.insights = CandidateInsights()
        self._last_extracted_at = 0  # 上次提取时的消息数

    def should_extract(self, total_message_count: int) -> bool:
        """判断是否应该提取洞察"""
        messages_since = total_message_count - self._last_extracted_at
        return messages_since >= self.EXTRACT_INTERVAL

    async def extract_insights(
        self,
        recent_messages: List[Dict],
        stage: str,
    ) -> CandidateInsights:
        """
        从最近的对话中提取洞察

        Args:
            recent_messages: 最近的消息列表
            stage: 当前面试阶段

        Returns:
            新提取的 CandidateInsights
        """
        logger.info(
            "[InsightExtractor] 开始提取洞察: messages=%d, stage=%s",
            len(recent_messages), stage
        )

        # 格式化对话
        conversation = self._format_messages(recent_messages)

        # 格式化已有洞察（用于去重）
        existing = json.dumps(self.insights.to_dict(), ensure_ascii=False, indent=2)

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "你是面试洞察分析师。请输出严格 JSON 格式。"},
                    {"role": "user", "content": INSIGHT_EXTRACTION_PROMPT.format(
                        existing_insights=existing,
                        recent_conversation=conversation,
                        stage=stage,
                    )},
                ],
                temperature=0.3,
                max_tokens=800,
            )

            raw = response.choices[0].message.content or "{}"
            data = self._parse_json(raw)

            new_insights = CandidateInsights(
                technical_signals=data.get("technical_signals", []),
                knowledge_gaps=data.get("knowledge_gaps", []),
                communication_style=data.get("communication_style", []),
                thinking_patterns=data.get("thinking_patterns", []),
                strategy_suggestions=data.get("strategy_suggestions", []),
                notable_quotes=data.get("notable_quotes", []),
            )

            # 合并到已有洞察
            self.insights.merge(new_insights)
            self._last_extracted_at += len(recent_messages)

            logger.info(
                "[InsightExtractor] 提取完成: 技术信号=%d, 知识盲区=%d, 策略建议=%d",
                len(new_insights.technical_signals),
                len(new_insights.knowledge_gaps),
                len(new_insights.strategy_suggestions),
            )

            return new_insights

        except Exception as e:
            logger.error("[InsightExtractor] 提取失败: %s", e)
            return CandidateInsights()

    async def extract_async(
        self,
        recent_messages: List[Dict],
        stage: str,
    ) -> CandidateInsights:
        """
        异步提取包装器（用于 asyncio.create_task 后台执行）
        """
        try:
            return await self.extract_insights(recent_messages, stage)
        except Exception as e:
            logger.error("[InsightExtractor] 异步提取异常: %s", e)
            return CandidateInsights()

    def get_strategy_suggestion(self) -> str:
        """获取最新的策略建议（用于主 Agent）"""
        if self.insights.strategy_suggestions:
            return self.insights.strategy_suggestions[-1]
        return ""

    def get_knowledge_gaps(self) -> List[str]:
        """获取已发现的知识盲区"""
        return self.insights.knowledge_gaps

    @staticmethod
    def _format_messages(messages: List[Dict]) -> str:
        lines = []
        for msg in messages:
            role = "面试官" if msg["role"] == "assistant" else "候选人"
            lines.append(f"{role}: {msg['content']}")
        return "\n\n".join(lines)

    @staticmethod
    def _parse_json(raw: str) -> dict:
        import re
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            pass
        json_match = re.search(r'\{[\s\S]*\}', raw)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass
        return {}
