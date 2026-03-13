"""
算法题库加载器
"""

import re
from pathlib import Path
from typing import Optional
import random

PROBLEMS_DIR = Path(__file__).resolve().parent.parent / "problems"


def load_problem_bank() -> list[dict]:
    """加载题库，返回题目列表"""
    bank_file = PROBLEMS_DIR / "problem_bank.md"
    if not bank_file.exists():
        return []

    content = bank_file.read_text(encoding="utf-8")
    problems = []

    # 按 ## problem_ 分割
    sections = re.split(r"(?=## problem_)", content)

    for section in sections:
        if not section.strip() or not section.startswith("## problem_"):
            continue

        problem = {}

        # 提取 ID
        id_match = re.search(r"## (problem_\d+)", section)
        if id_match:
            problem["id"] = id_match.group(1)

        # 提取题目名称
        title_match = re.search(r"### 题目：(.+)", section)
        if title_match:
            problem["title"] = title_match.group(1).strip()

        # 提取难度
        diff_match = re.search(r"### 难度：(.+)", section)
        if diff_match:
            problem["difficulty"] = diff_match.group(1).strip()

        # 提取描述
        desc_match = re.search(r"### 描述\n([\s\S]*?)(?=### 示例|### 函数签名|$)", section)
        if desc_match:
            problem["description"] = desc_match.group(1).strip()

        # 提取示例
        example_match = re.search(r"### 示例\n```([\s\S]*?)```", section)
        if example_match:
            problem["example"] = example_match.group(1).strip()

        # 提取函数签名（支持 python 和 cpp）
        sig_match = re.search(r"### 函数签名\n```(?:python|cpp|c\+\+)?\n([\s\S]*?)```", section)
        if sig_match:
            problem["signature"] = sig_match.group(1).strip()

        # 提取参考答案（支持 python 和 cpp）
        answer_match = re.search(r"### 参考答案\n```(?:python|cpp|c\+\+)?\n([\s\S]*?)```", section)
        if answer_match:
            problem["reference_answer"] = answer_match.group(1).strip()

        if problem.get("id"):
            problems.append(problem)

    return problems


def get_random_problem() -> Optional[dict]:
    """随机获取一道题目"""
    problems = load_problem_bank()
    if not problems:
        return None
    return random.choice(problems)


def get_problem_by_id(problem_id: str) -> Optional[dict]:
    """根据 ID 获取题目"""
    problems = load_problem_bank()
    for p in problems:
        if p.get("id") == problem_id:
            return p
    return None
