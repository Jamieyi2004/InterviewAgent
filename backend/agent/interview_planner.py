"""
面试策略规划器 —— 借鉴 Claude Code 的 Plan Mode 设计

核心设计：
1. 面试开始前，基于简历分析生成个性化面试计划
2. 识别简历亮点和疑点
3. 为每个阶段规划具体问题方向
4. 设定难度梯度
5. 预设追问路径（决策树）

参考：Claude Code src/tools/EnterPlanModeTool/prompt.ts
"""

import json
from typing import Dict, List, Optional
from dataclasses import dataclass, field

from openai import AsyncOpenAI
from loguru import logger

from config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL


# ======================== 数据模型 ========================

@dataclass
class StagePlan:
    """单阶段面试计划"""
    stage: str                              # 阶段名称
    focus_areas: List[str]                  # 重点考察方向
    planned_questions: List[str]            # 预设问题池
    follow_up_tree: Dict[str, List[str]]    # 追问决策树 {回答情况: [追问问题]}
    max_questions: int                      # 本阶段最大问题数
    difficulty_level: str                   # 难度级别：easy/medium/hard
    time_allocation_minutes: int            # 预估时间（分钟）


@dataclass
class InterviewPlan:
    """完整面试计划"""
    candidate_name: str
    position: str
    resume_highlights: List[str]            # 简历亮点（值得深挖）
    resume_concerns: List[str]              # 简历疑点（需要验证）
    resume_skill_tags: List[str]            # 技能标签提取
    stage_plans: Dict[str, StagePlan]       # 每阶段的具体计划
    difficulty_curve: str                   # 难度曲线策略描述
    estimated_duration_minutes: int         # 预估总时长
    opening_strategy: str                   # 开场策略
    key_evaluation_points: List[str]        # 核心评估要点

    def get_stage_plan(self, stage: str) -> Optional[StagePlan]:
        return self.stage_plans.get(stage)

    def get_focus_areas(self, stage: str) -> List[str]:
        plan = self.get_stage_plan(stage)
        return plan.focus_areas if plan else []

    def to_prompt_text(self) -> str:
        """将计划转换为可注入到 Prompt 中的文本"""
        lines = [
            "## 面试策略计划",
            f"候选人：{self.candidate_name} | 岗位：{self.position}",
            f"预估时长：{self.estimated_duration_minutes} 分钟",
            f"难度策略：{self.difficulty_curve}",
            "",
            "### 简历亮点（值得深挖）",
        ]
        for h in self.resume_highlights:
            lines.append(f"  - {h}")

        lines.append("\n### 简历疑点（需验证）")
        for c in self.resume_concerns:
            lines.append(f"  - {c}")

        lines.append("\n### 核心评估要点")
        for p in self.key_evaluation_points:
            lines.append(f"  - {p}")

        return "\n".join(lines)

    def to_dict(self) -> dict:
        """序列化为字典"""
        return {
            "candidate_name": self.candidate_name,
            "position": self.position,
            "resume_highlights": self.resume_highlights,
            "resume_concerns": self.resume_concerns,
            "resume_skill_tags": self.resume_skill_tags,
            "difficulty_curve": self.difficulty_curve,
            "estimated_duration_minutes": self.estimated_duration_minutes,
            "opening_strategy": self.opening_strategy,
            "key_evaluation_points": self.key_evaluation_points,
            "stage_plans": {
                stage: {
                    "focus_areas": sp.focus_areas,
                    "planned_questions": sp.planned_questions,
                    "follow_up_tree": sp.follow_up_tree,
                    "max_questions": sp.max_questions,
                    "difficulty_level": sp.difficulty_level,
                    "time_allocation_minutes": sp.time_allocation_minutes,
                }
                for stage, sp in self.stage_plans.items()
            },
        }


# ======================== 规划 Prompt ========================

PLANNING_PROMPT = """你是一位经验丰富的技术面试策略规划师。请根据候选人的简历信息，生成一份结构化的面试计划。

## 候选人信息
**目标岗位：** {position}

**简历内容：**
{resume_summary}

## 要求

请以严格 JSON 格式输出面试计划：

{{
    "resume_highlights": ["简历亮点1", "简历亮点2", "简历亮点3"],
    "resume_concerns": ["简历疑点1", "简历疑点2"],
    "resume_skill_tags": ["技能标签1", "技能标签2", "技能标签3"],
    "difficulty_curve": "难度曲线策略描述（如：先易后难，逐步提升）",
    "estimated_duration_minutes": 25,
    "opening_strategy": "开场策略描述",
    "key_evaluation_points": ["核心评估要点1", "核心评估要点2", "核心评估要点3"],
    "stage_plans": {{
        "opening": {{
            "focus_areas": ["了解候选人背景", "评估沟通表达"],
            "planned_questions": ["请简单介绍一下你自己"],
            "follow_up_tree": {{
                "回答详细": ["你对XX方向特别感兴趣，能展开说说吗？"],
                "回答简短": ["能说说你为什么选择XX专业吗？"]
            }},
            "max_questions": 2,
            "difficulty_level": "easy",
            "time_allocation_minutes": 3
        }},
        "coding": {{
            "focus_areas": ["编程基本功", "算法思维", "代码风格"],
            "planned_questions": ["算法编程题"],
            "follow_up_tree": {{
                "代码正确": ["时间复杂度是多少？有没有更优的解法？"],
                "代码有误": ["你觉得哪里可能有问题？再想想边界情况"]
            }},
            "max_questions": 3,
            "difficulty_level": "medium",
            "time_allocation_minutes": 8
        }},
        "basic_qa": {{
            "focus_areas": ["根据简历技能栈选择方向"],
            "planned_questions": ["问题1", "问题2", "问题3"],
            "follow_up_tree": {{
                "回答好": ["更深入的追问"],
                "回答不好": ["换一个方向"]
            }},
            "max_questions": 4,
            "difficulty_level": "medium",
            "time_allocation_minutes": 8
        }},
        "project_deep": {{
            "focus_areas": ["技术选型", "个人贡献", "问题解决能力"],
            "planned_questions": ["请介绍你最有成就感的项目"],
            "follow_up_tree": {{
                "有亮点": ["STAR追问：具体遇到什么挑战？"],
                "描述模糊": ["你在这个项目中具体负责哪部分？"]
            }},
            "max_questions": 4,
            "difficulty_level": "hard",
            "time_allocation_minutes": 8
        }}
    }}
}}

## 规划原则
1. **简历驱动**：问题方向必须基于候选人简历中的技能和经历
2. **难度梯度**：从简单到困难，给候选人适应面试节奏的机会
3. **追问灵活性**：根据回答好坏设计不同的追问路径
4. **时间管控**：总时间控制在 {estimated_minutes} 分钟左右
5. **全面覆盖**：技术深度 + 项目经验 + 编程能力 + 沟通表达
"""


# ======================== 核心类 ========================

class InterviewPlanner:
    """
    面试策略规划器

    使用方式：
        planner = InterviewPlanner()
        plan = await planner.generate_plan(
            resume_summary="候选人简历...",
            position="Java后端开发",
            candidate_name="张三"
        )

        # 注入到面试 Prompt
        prompt_text = plan.to_prompt_text()

        # 获取特定阶段的计划
        basic_qa_plan = plan.get_stage_plan("basic_qa")
    """

    def __init__(self):
        self.client = AsyncOpenAI(api_key=LLM_API_KEY, base_url=LLM_BASE_URL)
        self.model = LLM_MODEL

    async def generate_plan(
        self,
        resume_summary: str,
        position: str,
        candidate_name: str = "候选人",
        estimated_minutes: int = 25,
    ) -> InterviewPlan:
        """
        生成面试策略计划

        Args:
            resume_summary: 简历摘要
            position: 目标岗位
            candidate_name: 候选人姓名
            estimated_minutes: 预估面试时长

        Returns:
            InterviewPlan 结构化面试计划
        """
        logger.info("[Planner] 开始生成面试计划: position=%s", position)

        prompt = PLANNING_PROMPT.format(
            position=position,
            resume_summary=resume_summary,
            estimated_minutes=estimated_minutes,
        )

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "你是面试策略规划师。请输出严格 JSON 格式的面试计划。"},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.5,
                max_tokens=2000,
            )

            raw = response.choices[0].message.content or "{}"
            plan_data = self._parse_json(raw)

            plan = self._build_plan(plan_data, candidate_name, position)

            logger.info(
                "[Planner] 面试计划生成完成: 亮点=%d, 疑点=%d, 阶段=%d",
                len(plan.resume_highlights),
                len(plan.resume_concerns),
                len(plan.stage_plans),
            )

            return plan

        except Exception as e:
            logger.error("[Planner] 面试计划生成失败: %s", e)
            return self._default_plan(candidate_name, position)

    def _build_plan(self, data: dict, candidate_name: str, position: str) -> InterviewPlan:
        """从解析的 JSON 构建 InterviewPlan"""
        stage_plans = {}
        for stage_name, sp_data in data.get("stage_plans", {}).items():
            stage_plans[stage_name] = StagePlan(
                stage=stage_name,
                focus_areas=sp_data.get("focus_areas", []),
                planned_questions=sp_data.get("planned_questions", []),
                follow_up_tree=sp_data.get("follow_up_tree", {}),
                max_questions=sp_data.get("max_questions", 3),
                difficulty_level=sp_data.get("difficulty_level", "medium"),
                time_allocation_minutes=sp_data.get("time_allocation_minutes", 5),
            )

        return InterviewPlan(
            candidate_name=candidate_name,
            position=position,
            resume_highlights=data.get("resume_highlights", []),
            resume_concerns=data.get("resume_concerns", []),
            resume_skill_tags=data.get("resume_skill_tags", []),
            stage_plans=stage_plans,
            difficulty_curve=data.get("difficulty_curve", "先易后难"),
            estimated_duration_minutes=data.get("estimated_duration_minutes", 25),
            opening_strategy=data.get("opening_strategy", "标准开场"),
            key_evaluation_points=data.get("key_evaluation_points", []),
        )

    def _default_plan(self, candidate_name: str, position: str) -> InterviewPlan:
        """默认面试计划（LLM 调用失败时的降级）"""
        return InterviewPlan(
            candidate_name=candidate_name,
            position=position,
            resume_highlights=["待面试中发现"],
            resume_concerns=["待面试中验证"],
            resume_skill_tags=[],
            stage_plans={
                "opening": StagePlan(
                    stage="opening",
                    focus_areas=["自我介绍", "沟通能力"],
                    planned_questions=["请简单介绍一下自己"],
                    follow_up_tree={},
                    max_questions=2,
                    difficulty_level="easy",
                    time_allocation_minutes=3,
                ),
                "coding": StagePlan(
                    stage="coding",
                    focus_areas=["编程能力", "算法思维"],
                    planned_questions=["算法编程题"],
                    follow_up_tree={},
                    max_questions=3,
                    difficulty_level="medium",
                    time_allocation_minutes=8,
                ),
                "basic_qa": StagePlan(
                    stage="basic_qa",
                    focus_areas=["基础知识", "技术深度"],
                    planned_questions=["基础技术问题"],
                    follow_up_tree={},
                    max_questions=4,
                    difficulty_level="medium",
                    time_allocation_minutes=8,
                ),
                "project_deep": StagePlan(
                    stage="project_deep",
                    focus_areas=["项目经验", "技术选型"],
                    planned_questions=["请介绍你的项目经历"],
                    follow_up_tree={},
                    max_questions=4,
                    difficulty_level="hard",
                    time_allocation_minutes=8,
                ),
            },
            difficulty_curve="先易后难，逐步提升",
            estimated_duration_minutes=25,
            opening_strategy="标准开场，让候选人放松",
            key_evaluation_points=["技术基础", "编程能力", "项目经验", "沟通表达"],
        )

    @staticmethod
    def _parse_json(raw: str) -> dict:
        """解析 LLM 返回的 JSON"""
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

        logger.warning("[Planner] JSON 解析失败")
        return {}
