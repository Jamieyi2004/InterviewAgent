"""
上下文压缩器 + 对话精简器 —— 借鉴 Claude Code 的 Compact + Snip 机制

核心能力：
1. 全量压缩（Compact）：对话过长时生成 9 段式结构化摘要
2. 增量精简（Snip）：轻量级裁剪，保留关键信息去除冗余
3. Token 预算管理：自动判断何时需要压缩
4. 分析-摘要两阶段：先 <analysis> 思考，再 <summary> 输出

参考：
- Claude Code src/services/compact/prompt.ts（375行）
- Claude Code src/services/compact/snipCompact.ts
"""

import re
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

from openai import AsyncOpenAI
from loguru import logger

from config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL


# ======================== 配置 ========================

MAX_CONTEXT_TOKENS = 6000    # 上下文 Token 上限，超过则触发压缩
KEEP_RECENT_TURNS = 4        # 压缩后保留最近 4 轮（8条消息）原始对话
CHARS_PER_TOKEN = 2.5        # 中文约 2.5 字符 ≈ 1 token
COMPACT_THRESHOLD_RATIO = 0.8  # 达到上限的 80% 就开始压缩


# ======================== 压缩 Prompt ========================

INTERVIEW_COMPACT_PROMPT = """你的任务是为面试对话创建详细摘要。这份摘要将替代原始对话历史，作为后续面试的上下文。

请严格按以下步骤执行：

**第一步：** 在 <analysis> 标签中整理思路，分析对话中的关键信息。
**第二步：** 在 <summary> 标签中输出最终摘要。

<summary> 必须包含以下 9 个章节（不可省略任何章节）：

## 1. 面试基本信息
候选人姓名、目标岗位、当前面试进度（第几阶段，共几阶段）

## 2. 各阶段问答记录
- 每个问题的核心内容
- 候选人回答的质量评价（好/中/差）
- 涉及的关键技术知识点

## 3. 候选人能力画像
- 技术深度（1-5分）
- 沟通表达（1-5分）
- 逻辑思维（1-5分）
- 当前整体评价

## 4. 已发现的优势和不足
- 优势：具体引用对话中的例子
- 不足：具体引用对话中的例子

## 5. 面试策略调整记录
- 难度调整记录
- 方向切换原因
- 策略变更效果

## 6. 关键技术细节
- 保留所有具体的技术术语、框架名称、算法名称
- 保留候选人提到的代码片段或技术方案

## 7. 候选人原始表述（重要）
保留候选人的关键原话（用于最终报告引用），格式：
- "原话内容" —— 出现在哪个阶段的回答中

## 8. 当前状态
- 正在进行的阶段
- 最近 1 轮的完整问答

## 9. 下一步计划
- 基于当前表现，接下来应该考察什么方向
- 建议的问题难度

**重要规则：**
- 不要遗漏任何面试官的提问
- 保留所有具体的技术细节
- 第 8 节"当前状态"要最详细（因为它直接影响下一轮对话）
- 摘要总长度控制在 1500 字以内
"""


# ======================== 核心类 ========================

@dataclass
class CompactResult:
    """压缩结果"""
    summary: str                    # 压缩后的摘要
    original_message_count: int     # 原始消息数
    kept_recent_count: int          # 保留的最近消息数
    estimated_tokens_before: int    # 压缩前估算 Token 数
    estimated_tokens_after: int     # 压缩后估算 Token 数
    compression_ratio: float        # 压缩比


class ContextCompactor:
    """
    上下文压缩器 —— 借鉴 Claude Code 的 Compact 机制

    当对话历史超过阈值时，自动将早期对话压缩为结构化摘要，
    保留最近 N 轮原始对话 + 结构化摘要。

    使用方式：
        compactor = ContextCompactor()

        # 每轮对话后检查是否需要压缩
        messages, was_compacted = await compactor.compact_if_needed(
            messages=conversation_messages,
            session_memory_text="当前会话记忆..."
        )

        # 强制压缩
        result = await compactor.compact(messages)
    """

    def __init__(
        self,
        max_tokens: int = MAX_CONTEXT_TOKENS,
        keep_recent: int = KEEP_RECENT_TURNS,
    ):
        self.max_tokens = max_tokens
        self.keep_recent_messages = keep_recent * 2  # 每轮 2 条消息
        self.client = AsyncOpenAI(api_key=LLM_API_KEY, base_url=LLM_BASE_URL)
        self.model = LLM_MODEL
        self._compact_count = 0
        self._last_summary = ""

    def estimate_tokens(self, messages: List[Dict]) -> int:
        """估算消息列表的 Token 数"""
        total_chars = sum(len(m.get("content", "")) for m in messages)
        return int(total_chars / CHARS_PER_TOKEN)

    def needs_compact(self, messages: List[Dict]) -> bool:
        """判断是否需要压缩"""
        tokens = self.estimate_tokens(messages)
        threshold = int(self.max_tokens * COMPACT_THRESHOLD_RATIO)
        return tokens > threshold

    async def compact_if_needed(
        self,
        messages: List[Dict],
        session_memory_text: str = "",
    ) -> Tuple[List[Dict], bool]:
        """
        检查是否需要压缩，如需要则执行

        Args:
            messages: 对话消息列表
            session_memory_text: 当前会话记忆文本（辅助压缩）

        Returns:
            (压缩后的消息列表, 是否执行了压缩)
        """
        if not self.needs_compact(messages):
            return messages, False

        logger.info(
            "[Compactor] 触发上下文压缩：消息数=%d, 估算tokens=%d",
            len(messages), self.estimate_tokens(messages)
        )

        result = await self.compact(messages, session_memory_text)

        # 构建压缩后的消息列表：摘要 + 最近 N 条原始消息
        compacted_messages = self._build_compacted_context(
            result.summary, messages
        )

        logger.info(
            "[Compactor] 压缩完成：%d→%d tokens, 压缩比=%.1f%%",
            result.estimated_tokens_before,
            result.estimated_tokens_after,
            result.compression_ratio * 100,
        )

        return compacted_messages, True

    async def compact(
        self,
        messages: List[Dict],
        session_memory_text: str = "",
    ) -> CompactResult:
        """
        执行全量压缩

        Args:
            messages: 完整的对话消息列表
            session_memory_text: 辅助信息

        Returns:
            CompactResult
        """
        tokens_before = self.estimate_tokens(messages)

        # 需要压缩的消息（排除最近 N 条）
        messages_to_compress = messages[:-self.keep_recent_messages] if len(messages) > self.keep_recent_messages else messages

        # 格式化为对话文本
        conversation_text = self._format_messages_for_compact(messages_to_compress)

        # 调用 LLM 生成摘要
        summary = await self._generate_summary(conversation_text, session_memory_text)

        # 清理摘要（移除 <analysis> 标签）
        summary = self._extract_summary(summary)

        self._compact_count += 1
        self._last_summary = summary

        # 计算压缩后的 Token 数
        recent_messages = messages[-self.keep_recent_messages:]
        tokens_after = (
            int(len(summary) / CHARS_PER_TOKEN)
            + self.estimate_tokens(recent_messages)
        )

        return CompactResult(
            summary=summary,
            original_message_count=len(messages),
            kept_recent_count=len(recent_messages),
            estimated_tokens_before=tokens_before,
            estimated_tokens_after=tokens_after,
            compression_ratio=1 - (tokens_after / tokens_before) if tokens_before else 0,
        )

    def _build_compacted_context(
        self, summary: str, original_messages: List[Dict]
    ) -> List[Dict]:
        """构建压缩后的上下文：摘要作为系统消息 + 最近 N 条原始消息"""
        compacted = []

        # 摘要作为 system 消息
        compacted.append({
            "role": "system",
            "content": f"[以下是此前面试对话的结构化摘要]\n\n{summary}\n\n[摘要结束，以下是最近的对话]",
        })

        # 保留最近 N 条原始消息
        recent = original_messages[-self.keep_recent_messages:]
        compacted.extend(recent)

        return compacted

    async def _generate_summary(
        self, conversation_text: str, session_memory_text: str
    ) -> str:
        """调用 LLM 生成 9 段式摘要"""
        user_content = f"请为以下面试对话生成结构化摘要：\n\n{conversation_text}"

        if session_memory_text:
            user_content += f"\n\n当前会话记忆参考：\n{session_memory_text}"

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": INTERVIEW_COMPACT_PROMPT},
                    {"role": "user", "content": user_content},
                ],
                temperature=0.3,  # 摘要任务用低温度
                max_tokens=2000,
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            logger.error("[Compactor] LLM 摘要生成失败: %s", e)
            # 降级：返回简单的截断摘要
            return self._fallback_summary(conversation_text)

    @staticmethod
    def _format_messages_for_compact(messages: List[Dict]) -> str:
        """将消息列表格式化为对话文本"""
        lines = []
        for msg in messages:
            role = "面试官" if msg["role"] == "assistant" else "候选人"
            lines.append(f"{role}: {msg['content']}")
        return "\n\n".join(lines)

    @staticmethod
    def _extract_summary(raw_response: str) -> str:
        """从 LLM 响应中提取 <summary> 部分，移除 <analysis>"""
        # 优先提取 <summary> 标签内容
        summary_match = re.search(
            r"<summary>(.*?)</summary>", raw_response, re.DOTALL
        )
        if summary_match:
            return summary_match.group(1).strip()

        # 如果没有标签，移除 <analysis> 部分
        cleaned = re.sub(
            r"<analysis>.*?</analysis>", "", raw_response, flags=re.DOTALL
        )
        return cleaned.strip() or raw_response.strip()

    @staticmethod
    def _fallback_summary(conversation_text: str) -> str:
        """降级摘要：简单截取关键部分"""
        lines = conversation_text.split("\n\n")
        # 取前5条和后5条
        if len(lines) > 10:
            summary_lines = lines[:5] + ["...[中间对话已省略]..."] + lines[-5:]
        else:
            summary_lines = lines
        return "\n\n".join(summary_lines)

    def get_stats(self) -> dict:
        """获取压缩统计信息"""
        return {
            "compact_count": self._compact_count,
            "max_tokens": self.max_tokens,
            "keep_recent_messages": self.keep_recent_messages,
            "has_summary": bool(self._last_summary),
        }


# ======================== 对话精简器（Snip） ========================

class InterviewSnip:
    """
    面试对话精简器 —— 借鉴 Claude Code 的 Snip 机制

    轻量级优化，不调用 LLM，纯规则处理：
    1. 保留所有面试官的问题
    2. 精简候选人回答（去除语气词、重复）
    3. 去除面试官的纯过渡语（"好的"、"嗯"）
    4. 合并连续的短消息
    """

    # 面试官的纯过渡语（可以安全删除）
    TRANSITION_PHRASES = {
        "好的", "嗯", "不错", "明白了", "好", "嗯嗯",
        "好的好的", "行", "可以", "了解", "OK", "ok",
    }

    # 候选人回答中的语气词（可以删除）
    FILLER_PATTERNS = [
        r'(嗯+\s*)',
        r'(啊+\s*)',
        r'(那个+\s*)',
        r'(就是说\s*)',
        r'(然后的话\s*)',
        r'(怎么说呢\s*)',
        r'(其实就是\s*)',
    ]

    def snip(self, messages: List[Dict]) -> List[Dict]:
        """
        精简对话，保留核心信息

        Args:
            messages: 原始消息列表

        Returns:
            精简后的消息列表
        """
        snipped = []

        for msg in messages:
            if msg["role"] == "assistant":
                # 面试官消息：过滤纯过渡语
                if self._is_transition_only(msg["content"]):
                    continue
                snipped.append(msg)
            elif msg["role"] == "user":
                # 候选人消息：清理语气词
                cleaned_content = self._clean_answer(msg["content"])
                if cleaned_content.strip():
                    snipped.append({**msg, "content": cleaned_content})
            else:
                # system 消息保留
                snipped.append(msg)

        # 合并连续的短消息
        snipped = self._merge_short_messages(snipped)

        return snipped

    def _is_transition_only(self, text: str) -> bool:
        """判断是否是纯过渡语"""
        stripped = text.strip().rstrip("。，！？.!?,")
        return stripped in self.TRANSITION_PHRASES

    def _clean_answer(self, text: str) -> str:
        """清理候选人回答中的冗余内容"""
        cleaned = text
        for pattern in self.FILLER_PATTERNS:
            cleaned = re.sub(pattern, '', cleaned)
        # 清理多余空格
        cleaned = re.sub(r'\s+', ' ', cleaned)
        return cleaned.strip()

    @staticmethod
    def _merge_short_messages(messages: List[Dict], threshold: int = 15) -> List[Dict]:
        """
        合并同一角色的连续短消息

        Args:
            messages: 消息列表
            threshold: 短消息的字符数阈值

        Returns:
            合并后的消息列表
        """
        if not messages:
            return messages

        merged = [messages[0]]

        for msg in messages[1:]:
            prev = merged[-1]
            # 如果角色相同且前一条是短消息，合并
            if (
                msg["role"] == prev["role"]
                and len(prev["content"]) < threshold
                and msg["role"] != "system"
            ):
                merged[-1] = {
                    **prev,
                    "content": prev["content"] + " " + msg["content"],
                }
            else:
                merged.append(msg)

        return merged

    def get_savings(self, original: List[Dict], snipped: List[Dict]) -> dict:
        """计算精简节省的资源"""
        orig_chars = sum(len(m.get("content", "")) for m in original)
        snip_chars = sum(len(m.get("content", "")) for m in snipped)
        return {
            "original_messages": len(original),
            "snipped_messages": len(snipped),
            "messages_removed": len(original) - len(snipped),
            "original_chars": orig_chars,
            "snipped_chars": snip_chars,
            "chars_saved": orig_chars - snip_chars,
            "reduction_percentage": round(
                (1 - snip_chars / orig_chars) * 100 if orig_chars else 0, 1
            ),
        }
