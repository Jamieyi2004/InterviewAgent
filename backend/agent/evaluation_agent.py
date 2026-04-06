"""
实时评估 Agent —— 借鉴 Claude Code 的 Verification Agent 设计

核心设计：
1. 独立的评估 Agent，与主对话流解耦
2. 每轮回答后异步评估（不阻塞主对话流）
3. 输出结构化评分（多维度 + 证据链）
4. 反偏差 Prompt 设计（对抗光环效应、宽容偏差等）
5. 最终报告生成（综合所有轮次评估）

参考：
- Claude Code src/tools/AgentTool/built-in/verificationAgent.ts
- 其中的"反自我欺骗"机制
"""

import json
import asyncio
from typing import Dict, List, Optional
from dataclasses import dataclass, field

from openai import AsyncOpenAI
from loguru import logger

from config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL


# ======================== 评估维度定义 ========================

@dataclass
class DimensionScore:
    """单维度评分"""
    dimension: str      # 维度名称
    score: int          # 分数 (0-100)
    evidence: str       # 评分依据（必须引用对话内容）
    confidence: str     # 置信度：high/medium/low


@dataclass
class TurnEvaluation:
    """单轮评估结果"""
    turn_number: int
    stage: str
    question: str
    answer_summary: str
    dimensions: List[DimensionScore]
    verdict: str                    # EXCELLENT / GOOD / FAIR / POOR
    overall_score: int              # 综合分 (0-100)
    strengths: List[str]            # 本轮亮点
    weaknesses: List[str]           # 本轮不足
    follow_up_suggestion: str       # 追问建议
    raw_response: str = ""          # LLM 原始响应


@dataclass
class FinalEvaluationReport:
    """最终评估报告"""
    total_turns: int
    overall_score: int
    verdict: str
    dimension_averages: Dict[str, float]
    stage_scores: Dict[str, int]
    top_strengths: List[str]
    top_weaknesses: List[str]
    hiring_recommendation: str
    detailed_feedback: str
    turn_evaluations: List[TurnEvaluation]


# ======================== 反偏差 Prompt ========================

EVALUATION_SYSTEM_PROMPT = """你是一位严格客观的面试评估专家。你的唯一职责是评估候选人的回答质量。

## 已知偏差模式 — 请主动对抗

你有以下已知的评估偏差，必须主动对抗：

1. **光环效应**：候选人某一方面表现好，就倾向于给其他方面也打高分
   → 对抗方法：每个维度独立评分，必须引用具体证据

2. **首因效应**：被候选人的第一印象（自我介绍）过度影响
   → 对抗方法：重点关注技术回答的质量，而非表达流畅度

3. **宽容偏差**：倾向于给出偏高的分数，避免"伤害"候选人
   → 对抗方法：严格按照评分标准。60分以下就是不及格，不要客气

4. **确认偏差**：一旦形成初步判断，就只关注支持该判断的证据
   → 对抗方法：主动寻找反面证据

5. **近因效应**：被最近的回答过度影响，忽略早期表现
   → 对抗方法：参考历史评估结果

## 识别你自己的合理化

你会感到想给高分的冲动。这些是你常用的借口——识别它们并做相反的事：
- "回答基本正确" — "基本"不是"完全"，扣分
- "候选人表达流利" — 流利不等于正确，检查技术准确性
- "虽然不完整但方向对" — 不完整就是不完整，按实际打分
- "考虑到这是面试紧张环境" — 评分标准不因环境调整

## 评分标准

- **90-100**: 超出预期，回答全面深入，有独到见解
- **75-89**: 良好，回答正确完整，有一定深度
- **60-74**: 及格，回答基本正确但缺乏深度
- **40-59**: 不及格，回答有明显错误或严重不完整
- **0-39**: 很差，回答完全错误或无法回答

## 输出规则

1. 每个评分**必须**附带具体的对话引用（"候选人说了'XXX'"）
2. 如果没有足够证据，该维度标记为"证据不足"并给 50 分（中立分）
3. verdict **必须**是 EXCELLENT/GOOD/FAIR/POOR 之一，不允许模糊判定
4. 严格输出 JSON 格式，不要有其他内容
"""

EVALUATION_USER_PROMPT = """请评估候选人在以下面试问答中的表现：

**面试阶段：** {stage}
**面试官问题：** {question}
**候选人回答：** {answer}
**当前是第 {turn_number} 轮对话**

{history_context}

请以严格 JSON 格式输出评估结果：
{{
    "dimensions": [
        {{
            "dimension": "技术准确性",
            "score": 0-100,
            "evidence": "候选人说了'...'，这说明..."
        }},
        {{
            "dimension": "回答完整度",
            "score": 0-100,
            "evidence": "..."
        }},
        {{
            "dimension": "表达清晰度",
            "score": 0-100,
            "evidence": "..."
        }},
        {{
            "dimension": "思维深度",
            "score": 0-100,
            "evidence": "..."
        }}
    ],
    "verdict": "EXCELLENT/GOOD/FAIR/POOR",
    "overall_score": 0-100,
    "strengths": ["亮点1", "亮点2"],
    "weaknesses": ["不足1", "不足2"],
    "follow_up_suggestion": "建议追问的方向"
}}
"""

FINAL_REPORT_PROMPT = """基于以下所有轮次的评估数据，生成最终面试评估报告。

候选人面试岗位：{position}

各轮评估结果：
{evaluations_json}

请以严格 JSON 格式输出最终报告：
{{
    "overall_score": 0-100,
    "verdict": "EXCELLENT/GOOD/FAIR/POOR",
    "dimension_averages": {{
        "技术准确性": 平均分,
        "回答完整度": 平均分,
        "表达清晰度": 平均分,
        "思维深度": 平均分
    }},
    "stage_scores": {{
        "opening": 分数,
        "coding": 分数,
        "basic_qa": 分数,
        "project_deep": 分数
    }},
    "top_strengths": ["最大优势1", "最大优势2", "最大优势3"],
    "top_weaknesses": ["最大不足1", "最大不足2", "最大不足3"],
    "hiring_recommendation": "强烈推荐/推荐/待定/不推荐",
    "detailed_feedback": "详细的综合评价，200字以内"
}}
"""


class RealTimeEvaluationAgent:
    """
    实时评估 Agent

    使用方式：
        evaluator = RealTimeEvaluationAgent()

        # 每轮对话后异步评估
        eval_result = await evaluator.evaluate(
            question="请解释HashMap的工作原理",
            answer="HashMap使用数组+链表的结构...",
            stage="basic_qa",
            turn_number=3
        )

        # 面试结束后生成最终报告
        report = await evaluator.generate_final_report(position="Java后端")
    """

    def __init__(self):
        self.client = AsyncOpenAI(api_key=LLM_API_KEY, base_url=LLM_BASE_URL)
        self.model = LLM_MODEL
        self.evaluations: List[TurnEvaluation] = []
        self._eval_count = 0

    async def evaluate(
        self,
        question: str,
        answer: str,
        stage: str,
        turn_number: int,
        history_evaluations: Optional[List[TurnEvaluation]] = None,
    ) -> TurnEvaluation:
        """
        评估单轮回答（异步，不阻塞主流程）

        Args:
            question: 面试官问题
            answer: 候选人回答
            stage: 当前面试阶段
            turn_number: 对话轮次
            history_evaluations: 历史评估结果（用于对抗近因效应）

        Returns:
            TurnEvaluation 评估结果
        """
        # 构建历史上下文（防止近因效应）
        history_context = ""
        if history_evaluations:
            prev_scores = [
                f"第{e.turn_number}轮({e.stage}): {e.verdict}({e.overall_score}分)"
                for e in history_evaluations[-5:]  # 最近5轮
            ]
            history_context = f"\n**历史评估参考（防止近因效应）：** {'; '.join(prev_scores)}"

        user_prompt = EVALUATION_USER_PROMPT.format(
            stage=stage,
            question=question,
            answer=answer,
            turn_number=turn_number,
            history_context=history_context,
        )

        # RAG: 检索参考答案，注入评估 prompt 辅助对照评分
        try:
            from services.rag_service import KnowledgeRAGService
            rag = KnowledgeRAGService.get_instance()
            refs = rag.search_reference_answer(question, k=2)
            if refs:
                ref_text = "\n".join([
                    f"- {r['title']}: {r['answer'][:200]}\n  考点: {', '.join(r['key_points'])}"
                    for r in refs
                ])
                user_prompt += f"\n\n**【参考答案】**（用于对照评分，不要求候选人完全一致）：\n{ref_text}"
        except Exception as e:
            logger.warning(f"RAG 检索参考答案失败（不影响评估）: {e}")

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": EVALUATION_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.2,  # 评估任务用极低温度保证一致性
                max_tokens=800,
            )

            raw = response.choices[0].message.content or "{}"
            eval_data = self._parse_evaluation(raw)

            evaluation = TurnEvaluation(
                turn_number=turn_number,
                stage=stage,
                question=question[:200],
                answer_summary=answer[:300],
                dimensions=[
                    DimensionScore(
                        dimension=d["dimension"],
                        score=d.get("score", 50),
                        evidence=d.get("evidence", "证据不足"),
                        confidence="high" if d.get("evidence") else "low",
                    )
                    for d in eval_data.get("dimensions", [])
                ],
                verdict=eval_data.get("verdict", "FAIR"),
                overall_score=eval_data.get("overall_score", 50),
                strengths=eval_data.get("strengths", []),
                weaknesses=eval_data.get("weaknesses", []),
                follow_up_suggestion=eval_data.get("follow_up_suggestion", ""),
                raw_response=raw,
            )

            self.evaluations.append(evaluation)
            self._eval_count += 1

            logger.info(
                "[Evaluator] 第%d轮评估完成: %s (%d分)",
                turn_number, evaluation.verdict, evaluation.overall_score
            )

            return evaluation

        except Exception as e:
            logger.error("[Evaluator] 评估失败: %s", e)
            # 返回默认评估
            return self._default_evaluation(turn_number, stage, question, answer)

    async def evaluate_async(
        self,
        question: str,
        answer: str,
        stage: str,
        turn_number: int,
    ) -> TurnEvaluation:
        """
        异步评估包装器（用于 asyncio.create_task）

        与 evaluate() 相同，但确保异常不会传播
        """
        try:
            return await self.evaluate(
                question, answer, stage, turn_number,
                history_evaluations=self.evaluations,
            )
        except Exception as e:
            logger.error("[Evaluator] 异步评估异常: %s", e)
            return self._default_evaluation(turn_number, stage, question, answer)

    async def generate_final_report(self, position: str) -> FinalEvaluationReport:
        """
        基于所有轮次评估生成最终报告

        Args:
            position: 面试岗位

        Returns:
            FinalEvaluationReport
        """
        if not self.evaluations:
            return self._empty_report()

        # 序列化评估历史
        evals_json = json.dumps([
            {
                "turn": e.turn_number,
                "stage": e.stage,
                "question": e.question,
                "verdict": e.verdict,
                "score": e.overall_score,
                "strengths": e.strengths,
                "weaknesses": e.weaknesses,
                "dimensions": [
                    {"name": d.dimension, "score": d.score}
                    for d in e.dimensions
                ],
            }
            for e in self.evaluations
        ], ensure_ascii=False, indent=2)

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "你是面试评估专家，请输出严格 JSON 格式的最终报告。"},
                    {"role": "user", "content": FINAL_REPORT_PROMPT.format(
                        position=position,
                        evaluations_json=evals_json,
                    )},
                ],
                temperature=0.2,
                max_tokens=1000,
            )

            raw = response.choices[0].message.content or "{}"
            report_data = self._parse_evaluation(raw)

            return FinalEvaluationReport(
                total_turns=len(self.evaluations),
                overall_score=report_data.get("overall_score", 50),
                verdict=report_data.get("verdict", "FAIR"),
                dimension_averages=report_data.get("dimension_averages", {}),
                stage_scores=report_data.get("stage_scores", {}),
                top_strengths=report_data.get("top_strengths", []),
                top_weaknesses=report_data.get("top_weaknesses", []),
                hiring_recommendation=report_data.get("hiring_recommendation", "待定"),
                detailed_feedback=report_data.get("detailed_feedback", ""),
                turn_evaluations=self.evaluations,
            )

        except Exception as e:
            logger.error("[Evaluator] 最终报告生成失败: %s", e)
            return self._calculate_report_from_turns()

    def get_current_summary(self) -> dict:
        """获取当前评估摘要（实时状态）"""
        if not self.evaluations:
            return {"turns_evaluated": 0}

        scores = [e.overall_score for e in self.evaluations]
        return {
            "turns_evaluated": len(self.evaluations),
            "average_score": round(sum(scores) / len(scores), 1),
            "latest_verdict": self.evaluations[-1].verdict,
            "latest_score": self.evaluations[-1].overall_score,
            "all_strengths": list({s for e in self.evaluations for s in e.strengths}),
            "all_weaknesses": list({w for e in self.evaluations for w in e.weaknesses}),
        }

    # ======================== 私有方法 ========================

    @staticmethod
    def _parse_evaluation(raw: str) -> dict:
        """解析 LLM 返回的 JSON"""
        # 尝试直接解析
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            pass

        # 尝试提取 JSON 块
        import re
        json_match = re.search(r'\{[\s\S]*\}', raw)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass

        logger.warning("[Evaluator] JSON 解析失败，使用空结果")
        return {}

    @staticmethod
    def _default_evaluation(
        turn_number: int, stage: str, question: str, answer: str
    ) -> TurnEvaluation:
        """默认评估结果（LLM 调用失败时的降级）"""
        return TurnEvaluation(
            turn_number=turn_number,
            stage=stage,
            question=question[:200],
            answer_summary=answer[:300],
            dimensions=[
                DimensionScore("技术准确性", 50, "评估服务暂时不可用", "low"),
                DimensionScore("回答完整度", 50, "评估服务暂时不可用", "low"),
                DimensionScore("表达清晰度", 50, "评估服务暂时不可用", "low"),
                DimensionScore("思维深度", 50, "评估服务暂时不可用", "low"),
            ],
            verdict="FAIR",
            overall_score=50,
            strengths=[],
            weaknesses=[],
            follow_up_suggestion="",
        )

    def _empty_report(self) -> FinalEvaluationReport:
        """空报告"""
        return FinalEvaluationReport(
            total_turns=0,
            overall_score=0,
            verdict="POOR",
            dimension_averages={},
            stage_scores={},
            top_strengths=[],
            top_weaknesses=[],
            hiring_recommendation="无法评估",
            detailed_feedback="面试对话为空，无法生成评估报告",
            turn_evaluations=[],
        )

    def _calculate_report_from_turns(self) -> FinalEvaluationReport:
        """从轮次评估直接计算报告（LLM 调用失败时的降级）"""
        if not self.evaluations:
            return self._empty_report()

        scores = [e.overall_score for e in self.evaluations]
        avg_score = sum(scores) / len(scores)

        # 按维度计算平均分
        dim_scores: Dict[str, List[int]] = {}
        for e in self.evaluations:
            for d in e.dimensions:
                dim_scores.setdefault(d.dimension, []).append(d.score)
        dim_averages = {
            k: round(sum(v) / len(v), 1) for k, v in dim_scores.items()
        }

        # 按阶段计算平均分
        stage_scores_map: Dict[str, List[int]] = {}
        for e in self.evaluations:
            stage_scores_map.setdefault(e.stage, []).append(e.overall_score)
        stage_scores = {
            k: round(sum(v) / len(v)) for k, v in stage_scores_map.items()
        }

        # 判定
        if avg_score >= 80:
            verdict, rec = "EXCELLENT", "强烈推荐"
        elif avg_score >= 65:
            verdict, rec = "GOOD", "推荐"
        elif avg_score >= 50:
            verdict, rec = "FAIR", "待定"
        else:
            verdict, rec = "POOR", "不推荐"

        return FinalEvaluationReport(
            total_turns=len(self.evaluations),
            overall_score=round(avg_score),
            verdict=verdict,
            dimension_averages=dim_averages,
            stage_scores=stage_scores,
            top_strengths=list({s for e in self.evaluations for s in e.strengths})[:3],
            top_weaknesses=list({w for e in self.evaluations for w in e.weaknesses})[:3],
            hiring_recommendation=rec,
            detailed_feedback=f"候选人共完成 {len(self.evaluations)} 轮面试，综合评分 {avg_score:.0f} 分。",
            turn_evaluations=self.evaluations,
        )
