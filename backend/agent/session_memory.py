"""
结构化面试会话记忆 —— 借鉴 Claude Code 的 SessionMemory 设计

核心设计：
1. 维护一份结构化的面试笔记，包含固定章节
2. 每个章节有独立的 Token 预算管理
3. 实时更新各章节内容
4. 模板保护机制（不修改章节标题和描述）
5. 自动膨胀检测与压缩提醒

参考：Claude Code src/services/SessionMemory/prompts.ts
"""

import re
import time
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field


# ======================== Token 预算配置 ========================

MAX_SECTION_TOKENS = 500       # 每个 Section 最多 500 tokens
MAX_TOTAL_MEMORY_TOKENS = 4000 # 总记忆最多 4000 tokens
CHARS_PER_TOKEN = 2.5          # 中文大约 2.5 字符 ≈ 1 token


# ======================== 记忆模板 ========================

INTERVIEW_SESSION_MEMORY_TEMPLATE = """# 面试标题
_{title}_

# 当前状态
_{current_state}_

# 候选人档案
_{candidate_profile}_

# 各阶段表现记录
## 开场（自我介绍）
_{opening_record}_

## 编程考察
_{coding_record}_

## 基础知识
_{basic_qa_record}_

## 项目深挖
_{project_record}_

# 候选人能力画像
_{ability_profile}_

# 已发现的优势
_{strengths}_

# 已发现的不足
_{weaknesses}_

# 待追问方向
_{follow_up_directions}_

# 面试策略调整记录
_{strategy_adjustments}_
"""

# 各 Section 的默认占位描述
SECTION_DEFAULTS = {
    "面试标题": "候选人姓名 - 目标岗位 - 面试日期",
    "当前状态": "当前正在进行的面试阶段，下一步计划",
    "候选人档案": "姓名、学校、专业、学历、核心技能栈",
    "开场（自我介绍）": "候选人介绍要点、第一印象",
    "编程考察": "题目名称、解题思路、代码质量评价、时间复杂度、是否有优化思路",
    "基础知识": "问答记录：问题→回答质量(好/中/差)→关键知识点",
    "项目深挖": "项目名称、技术栈、个人角色、STAR分析、追问记录",
    "候选人能力画像": "技术深度(1-5)、沟通表达(1-5)、逻辑思维(1-5)、学习能力(1-5)、抗压能力(1-5)",
    "已发现的优势": "具体的、可引用的优势列表",
    "已发现的不足": "具体的、可引用的不足列表",
    "待追问方向": "基于当前表现，下一步应该追问什么方向",
    "面试策略调整记录": "难度调整、方向切换、策略变更的原因和效果",
}

# 阶段名称到 Section 名称的映射
STAGE_TO_SECTION = {
    "opening": "开场（自我介绍）",
    "coding": "编程考察",
    "basic_qa": "基础知识",
    "project_deep": "项目深挖",
    "summary": "当前状态",  # 总结阶段更新当前状态
}


@dataclass
class SectionInfo:
    """单个 Section 的信息"""
    name: str
    content: str = ""
    default_description: str = ""
    estimated_tokens: int = 0
    last_updated: float = 0.0

    @property
    def is_empty(self) -> bool:
        """是否还是默认空模板"""
        return not self.content or self.content == self.default_description

    @property
    def is_over_budget(self) -> bool:
        return self.estimated_tokens > MAX_SECTION_TOKENS


class InterviewSessionMemory:
    """
    面试结构化会话记忆

    使用方式：
        memory = InterviewSessionMemory()
        memory.initialize("张三", "Java后端开发", "2026-04-05")

        # 更新特定 section
        memory.update_section("当前状态", "正在进行基础知识考察，已问2个问题")
        memory.update_section("基础知识", "Q1: HashMap原理 → 回答良好，理解底层结构")

        # 追加内容
        memory.append_to_section("已发现的优势", "- 对JVM内存模型理解深入")

        # 获取完整记忆（用于注入到 Prompt）
        prompt_text = memory.get_memory_for_prompt()

        # 获取指定 section
        section = memory.get_section("候选人能力画像")
    """

    def __init__(self):
        self.sections: Dict[str, SectionInfo] = {}
        self._initialized = False
        self._init_sections()

    def _init_sections(self):
        """初始化所有 Section"""
        for name, default_desc in SECTION_DEFAULTS.items():
            self.sections[name] = SectionInfo(
                name=name,
                content="",
                default_description=default_desc,
            )

    def initialize(self, candidate_name: str, position: str, date: str):
        """初始化面试记忆（面试开始时调用）"""
        self.update_section("面试标题", f"{candidate_name} - {position} - {date}")
        self.update_section("当前状态", "面试刚开始，正在进行开场自我介绍阶段")
        self.update_section("候选人档案", f"姓名：{candidate_name}，目标岗位：{position}")
        self._initialized = True

    def update_section(self, section_name: str, content: str):
        """
        更新指定 Section 的内容（完全替换）

        Args:
            section_name: Section 名称
            content: 新内容
        """
        if section_name not in self.sections:
            return

        section = self.sections[section_name]
        section.content = content
        section.estimated_tokens = self._estimate_tokens(content)
        section.last_updated = time.time()

    def append_to_section(self, section_name: str, content: str):
        """
        向指定 Section 追加内容

        Args:
            section_name: Section 名称
            content: 追加的内容
        """
        if section_name not in self.sections:
            return

        section = self.sections[section_name]
        if section.content:
            section.content += "\n" + content
        else:
            section.content = content
        section.estimated_tokens = self._estimate_tokens(section.content)
        section.last_updated = time.time()

    def update_from_turn(self, stage: str, question: str, answer: str,
                         evaluation: Optional[dict] = None):
        """
        从一轮对话中更新记忆（便捷方法）

        Args:
            stage: 当前面试阶段
            question: 面试官的问题
            answer: 候选人的回答
            evaluation: 评估结果（可选）
        """
        section_name = STAGE_TO_SECTION.get(stage)
        if not section_name:
            return

        # 构建记录内容
        quality = ""
        if evaluation:
            verdict = evaluation.get("verdict", "")
            score = evaluation.get("overall_score", "")
            quality = f" → {verdict}({score}分)"

        record = f"Q: {question[:80]}... | A质量{quality}"
        self.append_to_section(section_name, record)

        # 更新当前状态
        self.update_section("当前状态", f"正在进行 {stage} 阶段")

        # 如果有评估结果，更新优势和不足
        if evaluation:
            strengths = evaluation.get("strengths", [])
            weaknesses = evaluation.get("weaknesses", [])
            for s in strengths:
                self.append_to_section("已发现的优势", f"- {s}")
            for w in weaknesses:
                self.append_to_section("已发现的不足", f"- {w}")

            follow_up = evaluation.get("follow_up_suggestion", "")
            if follow_up:
                self.update_section("待追问方向", follow_up)

    def get_section(self, section_name: str) -> str:
        """获取指定 Section 的内容"""
        section = self.sections.get(section_name)
        if not section or section.is_empty:
            return ""
        return section.content

    def get_memory_for_prompt(self) -> str:
        """
        生成用于注入到 Prompt 中的记忆文本

        自动处理：
        1. 跳过空 section
        2. 超预算 section 添加压缩标记
        3. 总体超预算时截断
        """
        parts = []
        total_tokens = 0

        for name, section in self.sections.items():
            if section.is_empty:
                continue

            content = section.content
            tokens = section.estimated_tokens

            # 超预算警告
            if section.is_over_budget:
                content = self._truncate_to_budget(content, MAX_SECTION_TOKENS)
                tokens = MAX_SECTION_TOKENS

            # 总预算检查
            if total_tokens + tokens > MAX_TOTAL_MEMORY_TOKENS:
                parts.append(f"\n## {name}\n[内容已省略，总 Token 预算已满]")
                break

            parts.append(f"\n## {name}\n{content}")
            total_tokens += tokens

        if not parts:
            return ""

        return "# 面试会话记忆\n" + "\n".join(parts)

    def is_empty(self) -> bool:
        """检查记忆是否还是空模板"""
        return all(s.is_empty for s in self.sections.values())

    def get_section_sizes(self) -> Dict[str, int]:
        """获取各 Section 的估算 Token 数"""
        return {
            name: section.estimated_tokens
            for name, section in self.sections.items()
            if not section.is_empty
        }

    def get_total_tokens(self) -> int:
        """获取总估算 Token 数"""
        return sum(s.estimated_tokens for s in self.sections.values() if not s.is_empty)

    def get_over_budget_sections(self) -> List[str]:
        """获取超预算的 Section 列表"""
        return [
            name for name, section in self.sections.items()
            if section.is_over_budget
        ]

    def to_dict(self) -> dict:
        """序列化为字典"""
        return {
            "initialized": self._initialized,
            "total_estimated_tokens": self.get_total_tokens(),
            "sections": {
                name: {
                    "content": section.content,
                    "estimated_tokens": section.estimated_tokens,
                    "is_empty": section.is_empty,
                    "is_over_budget": section.is_over_budget,
                    "last_updated": section.last_updated,
                }
                for name, section in self.sections.items()
            },
        }

    # ======================== 私有方法 ========================

    @staticmethod
    def _estimate_tokens(text: str) -> int:
        """估算文本的 Token 数（中文约 2.5 字符 ≈ 1 token）"""
        if not text:
            return 0
        return int(len(text) / CHARS_PER_TOKEN)

    @staticmethod
    def _truncate_to_budget(text: str, max_tokens: int) -> str:
        """截断文本以符合 Token 预算"""
        max_chars = int(max_tokens * CHARS_PER_TOKEN)
        if len(text) <= max_chars:
            return text
        return text[:max_chars] + "\n...[已截断]"


# ======================== 记忆更新 Prompt ========================

MEMORY_UPDATE_PROMPT = """
你是面试记忆管理器。请根据最新一轮对话更新面试会话记忆。

当前记忆状态：
{current_memory}

最新一轮对话：
面试官：{question}
候选人：{answer}

当前面试阶段：{stage}

请输出更新后的各 Section 内容（JSON格式）：
{{
    "当前状态": "更新后的当前状态描述",
    "候选人能力画像": "更新后的能力评价",
    "已发现的优势": "追加的优势（如有）",
    "已发现的不足": "追加的不足（如有）",
    "待追问方向": "下一步追问建议"
}}

规则：
1. 只返回需要更新的 Section
2. 每个 Section 内容不超过 200 字
3. 保持客观，引用具体对话内容
4. 能力画像用 1-5 分制评价
"""
