"""
LangChain Chain 定义 —— 封装 LLM 调用逻辑
"""

import json
import logging
import time
from typing import AsyncIterator

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, BaseMessage

from config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL

logger = logging.getLogger(__name__)


def get_llm(
    temperature: float = 0.7,
    streaming: bool = False,
    max_tokens: int | None = None,
) -> ChatOpenAI:
    """获取 LLM 实例"""
    kwargs = {
        "model": LLM_MODEL,
        "api_key": LLM_API_KEY,
        "base_url": LLM_BASE_URL,
        "temperature": temperature,
        "streaming": streaming,
    }
    if max_tokens is not None:
        kwargs["max_tokens"] = max_tokens
    return ChatOpenAI(**kwargs)


async def call_llm(system_prompt: str, user_message: str) -> str:
    """同步调用 LLM，返回完整回复"""
    llm = get_llm(temperature=0.7)
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_message),
    ]
    response = await llm.ainvoke(messages)
    return response.content


async def call_llm_stream(
    system_prompt: str,
    user_message: str,
    history: list[BaseMessage] | None = None,
) -> AsyncIterator[str]:
    """
    流式调用 LLM，逐 token 返回（用于 WebSocket 打字机效果）

    Args:
        system_prompt: 系统提示词
        user_message: 当前用户消息
        history: 对话历史消息列表（可选）
    """
    logger.info("[LLM] 开始流式调用，user_message 长度=%d, history 长度=%d",
                len(user_message), len(history) if history else 0)
    llm = get_llm(temperature=0.7, streaming=True)

    # 构建消息列表：系统消息 + 历史消息 + 当前用户消息
    messages: list[BaseMessage] = [SystemMessage(content=system_prompt)]
    if history:
        messages.extend(history)
    messages.append(HumanMessage(content=user_message))

    token_count = 0
    t0 = time.time()
    first_token_time = None
    try:
        async for chunk in llm.astream(messages):
            if chunk.content:
                if first_token_time is None:
                    first_token_time = time.time()
                token_count += 1
                yield chunk.content

        total_time = (time.time() - t0) * 1000
        ttft = (first_token_time - t0) * 1000 if first_token_time else 0
        logger.info(
            "[LLM] 流式调用完成: tokens=%d, 总耗时=%.0fms, 首token=%.0fms",
            token_count, total_time, ttft
        )
    except Exception as e:
        logger.exception("[LLM] 流式调用异常: %s", e)
        raise


async def call_llm_json(
    system_prompt: str,
    user_message: str,
    max_tokens: int | None = None,
) -> dict:
    """
    调用 LLM 并解析 JSON 返回
    用于简历解析、报告生成等需要结构化输出的场景
    """
    llm = get_llm(temperature=0.3, max_tokens=max_tokens)  # JSON 用低温度
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_message),
    ]
    response = await llm.ainvoke(messages)
    text = response.content.strip()

    # 尝试提取 JSON（LLM 有时会包裹在 ```json ... ``` 中）
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0].strip()
    elif "```" in text:
        text = text.split("```")[1].split("```")[0].strip()

    return json.loads(text)
