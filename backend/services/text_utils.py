"""文本相关工具：分句、清理 LLM 输出等。"""

import re
from typing import List, Tuple

# 简单中文分句：按句号/问号/感叹号（中英文）分隔，保留标点
SENTENCE_DELIMITERS = r"[。！？!?]"

# 阶段切换标记
NEXT_STAGE_MARKER = "[[NEXT_STAGE]]"


def extract_stage_marker(text: str) -> Tuple[str, bool]:
    """
    提取并移除阶段切换标记

    Returns:
        (清理后的文本, 是否包含切换标记)
    """
    has_marker = NEXT_STAGE_MARKER in text
    clean_text = text.replace(NEXT_STAGE_MARKER, "").strip()
    return clean_text, has_marker


def clean_llm_output(text: str) -> str:
    """
    清理 LLM 输出中的不需要的格式标记

    - 移除 LaTeX \boxed{...} 包装
    - 移除 Markdown 代码块标记（如果整个输出被包在里面）
    - 移除多余的空白行
    """
    if not text:
        return text

    # 移除 \boxed{...} 包装（可能嵌套或跨多行）
    # 模式1: \boxed{content} - 单行
    text = re.sub(r"\\boxed\{([^}]*)\}", r"\1", text)

    # 模式2: \boxed{\n content \n} - 多行，贪婪匹配
    while "\\boxed{" in text:
        start = text.find("\\boxed{")
        if start == -1:
            break
        # 找到匹配的闭合括号
        depth = 0
        end = start + 7  # len("\\boxed{")
        for i in range(start + 7, len(text)):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                if depth == 0:
                    end = i
                    break
                depth -= 1
        # 提取内容
        content = text[start + 7 : end]
        text = text[:start] + content + text[end + 1 :]

    # 移除首尾空白行
    text = text.strip()

    return text


def split_sentences(text: str) -> List[str]:
    parts = re.split(f"({SENTENCE_DELIMITERS})", text)
    sentences: List[str] = []
    buf = ""
    for p in parts:
        if not p:
            continue
        buf += p
        if re.match(SENTENCE_DELIMITERS, p):
            if buf.strip():
                sentences.append(buf.strip())
            buf = ""
    if buf.strip():
        sentences.append(buf.strip())
    return sentences
