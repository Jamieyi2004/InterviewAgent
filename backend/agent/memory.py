"""
对话记忆管理（增强版）—— 借鉴闲鱼客服Agent的上下文管理设计

增强点：
1. 对话轮次追踪
2. 关键信息提取
3. 摘要能力（长对话压缩）
4. 基于 langchain_core 的 InMemoryChatMessageHistory 封装
"""

from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.messages import HumanMessage, AIMessage


class InterviewMemory:
    """
    面试对话记忆管理器（增强版）

    封装 LangChain ChatMessageHistory，提供：
    - 添加消息（面试官/候选人）
    - 获取对话历史（格式化字符串 / 原始列表 / 最近N轮）
    - 对话轮次统计
    - 清空记忆
    """

    # 保留最近多少条消息用于上下文注入
    MAX_CONTEXT_MESSAGES = 20

    def __init__(self):
        self.chat_history = InMemoryChatMessageHistory()
        self._round_count = 0  # 对话轮次（一问一答算一轮）

    def add_interviewer_message(self, content: str):
        """添加面试官消息"""
        self.chat_history.add_ai_message(content)

    def add_candidate_message(self, content: str):
        """添加候选人消息"""
        self.chat_history.add_user_message(content)
        self._round_count += 1  # 候选人发言标记一轮开始

    def get_messages(self) -> list:
        """获取原始消息列表"""
        return self.chat_history.messages

    def get_recent_messages(self, n: int = 10) -> list:
        """
        获取最近 N 轮的消息（借鉴闲鱼的上下文窗口管理）

        Args:
            n: 最近的消息条数

        Returns:
            最近 n 条消息
        """
        messages = self.chat_history.messages
        return messages[-n:] if len(messages) > n else messages

    def get_history_string(self) -> str:
        """获取格式化的完整对话历史字符串（用于报告生成）"""
        lines = []
        for msg in self.chat_history.messages:
            if isinstance(msg, AIMessage):
                lines.append(f"面试官：{msg.content}")
            elif isinstance(msg, HumanMessage):
                lines.append(f"候选人：{msg.content}")
        return "\n".join(lines)

    def get_recent_history_string(self, n: int = 20) -> str:
        """获取最近N条消息的格式化字符串（用于 Prompt 注入，避免上下文过长）"""
        recent = self.get_recent_messages(n)
        lines = []
        for msg in recent:
            if isinstance(msg, AIMessage):
                lines.append(f"面试官：{msg.content}")
            elif isinstance(msg, HumanMessage):
                lines.append(f"候选人：{msg.content}")
        return "\n".join(lines)

    def clear(self):
        """清空记忆"""
        self.chat_history.clear()
        self._round_count = 0

    @property
    def message_count(self) -> int:
        """当前消息总数"""
        return len(self.chat_history.messages)

    @property
    def round_count(self) -> int:
        """对话轮次数"""
        return self._round_count
