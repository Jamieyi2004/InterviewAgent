"""
Token 消耗追踪器 —— 借鉴 Claude Code 的 cost-tracker 设计

核心能力：
1. 记录每次 LLM API 调用的 Token 消耗（input/output）
2. 按面试阶段分类统计
3. 计算美元成本（支持多模型定价）
4. 生成消耗报告（含优化建议）
5. 预算控制（超限预警）
"""

import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional


# 模型定价表（每百万 Token 的美元价格）
MODEL_PRICING = {
    # 阿里云 Qwen 系列
    "qwen-turbo": {"input": 0.28, "output": 0.84},
    "qwen-plus": {"input": 0.57, "output": 1.70},
    "qwen-max": {"input": 2.83, "output": 8.50},
    "qwen3.5-flash": {"input": 0.14, "output": 0.42},
    # DeepSeek 系列
    "deepseek-chat": {"input": 0.14, "output": 0.28},
    "deepseek-v3": {"input": 0.27, "output": 1.10},
    # 通用默认
    "default": {"input": 0.50, "output": 1.50},
}


@dataclass
class TokenRecord:
    """单次 API 调用的 Token 记录"""
    stage: str
    input_tokens: int
    output_tokens: int
    model: str
    cost_usd: float
    timestamp: float = field(default_factory=time.time)
    caller: str = ""  # 调用者标识（如 "evaluation_agent", "question_worker"）


@dataclass
class StageUsage:
    """某阶段的累计使用量"""
    input_tokens: int = 0
    output_tokens: int = 0
    api_calls: int = 0
    cost_usd: float = 0.0

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


class TokenTracker:
    """
    Token 消耗追踪器

    使用方式：
        tracker = TokenTracker(model="qwen3.5-flash")
        tracker.record("basic_qa", input_tokens=500, output_tokens=200)
        tracker.record("basic_qa", input_tokens=480, output_tokens=180)
        report = tracker.get_report()
    """

    def __init__(self, model: str = "default", budget_usd: Optional[float] = None):
        self.model = model
        self.budget_usd = budget_usd  # 预算上限（美元），None 表示不限制
        self.records: List[TokenRecord] = []
        self.stage_usage: Dict[str, StageUsage] = defaultdict(StageUsage)
        self._start_time = time.time()

    def record(
        self,
        stage: str,
        input_tokens: int,
        output_tokens: int,
        model: Optional[str] = None,
        caller: str = "",
    ) -> TokenRecord:
        """
        记录一次 API 调用的 Token 消耗

        Args:
            stage: 面试阶段（如 "opening", "coding", "basic_qa"）
            input_tokens: 输入 Token 数
            output_tokens: 输出 Token 数
            model: 模型名称（可选，默认使用初始化时的模型）
            caller: 调用者标识

        Returns:
            创建的 TokenRecord
        """
        model_name = model or self.model
        cost = self._calculate_cost(input_tokens, output_tokens, model_name)

        record = TokenRecord(
            stage=stage,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            model=model_name,
            cost_usd=cost,
            caller=caller,
        )
        self.records.append(record)

        # 更新阶段统计
        usage = self.stage_usage[stage]
        usage.input_tokens += input_tokens
        usage.output_tokens += output_tokens
        usage.api_calls += 1
        usage.cost_usd += cost

        return record

    def _calculate_cost(self, input_tokens: int, output_tokens: int, model: str) -> float:
        """计算单次调用的美元成本"""
        pricing = MODEL_PRICING.get(model, MODEL_PRICING["default"])
        input_cost = (input_tokens / 1_000_000) * pricing["input"]
        output_cost = (output_tokens / 1_000_000) * pricing["output"]
        return round(input_cost + output_cost, 6)

    @property
    def total_input_tokens(self) -> int:
        return sum(u.input_tokens for u in self.stage_usage.values())

    @property
    def total_output_tokens(self) -> int:
        return sum(u.output_tokens for u in self.stage_usage.values())

    @property
    def total_tokens(self) -> int:
        return self.total_input_tokens + self.total_output_tokens

    @property
    def total_cost(self) -> float:
        return round(sum(u.cost_usd for u in self.stage_usage.values()), 6)

    @property
    def total_api_calls(self) -> int:
        return sum(u.api_calls for u in self.stage_usage.values())

    @property
    def avg_tokens_per_turn(self) -> float:
        """每轮对话平均 Token 消耗"""
        if not self.total_api_calls:
            return 0.0
        return self.total_tokens / self.total_api_calls

    def is_over_budget(self) -> bool:
        """是否超过预算"""
        if self.budget_usd is None:
            return False
        return self.total_cost >= self.budget_usd

    def get_budget_remaining(self) -> Optional[float]:
        """剩余预算（美元）"""
        if self.budget_usd is None:
            return None
        return max(0, self.budget_usd - self.total_cost)

    def get_stage_breakdown(self) -> Dict[str, dict]:
        """获取各阶段消耗明细"""
        breakdown = {}
        for stage, usage in self.stage_usage.items():
            breakdown[stage] = {
                "input_tokens": usage.input_tokens,
                "output_tokens": usage.output_tokens,
                "total_tokens": usage.total_tokens,
                "api_calls": usage.api_calls,
                "cost_usd": round(usage.cost_usd, 6),
                "percentage": round(
                    (usage.total_tokens / self.total_tokens * 100) if self.total_tokens else 0, 1
                ),
            }
        return breakdown

    def get_caller_breakdown(self) -> Dict[str, dict]:
        """按调用者分类统计"""
        caller_stats: Dict[str, dict] = defaultdict(
            lambda: {"input_tokens": 0, "output_tokens": 0, "api_calls": 0, "cost_usd": 0.0}
        )
        for record in self.records:
            key = record.caller or "main"
            caller_stats[key]["input_tokens"] += record.input_tokens
            caller_stats[key]["output_tokens"] += record.output_tokens
            caller_stats[key]["api_calls"] += 1
            caller_stats[key]["cost_usd"] += record.cost_usd
        return dict(caller_stats)

    def get_suggestions(self) -> List[str]:
        """基于消耗数据生成优化建议"""
        suggestions = []

        # 1. 检查总体消耗
        if self.total_tokens > 50000:
            suggestions.append(
                f"本次面试总 Token 消耗较高（{self.total_tokens}），建议启用上下文压缩以降低成本"
            )

        # 2. 检查阶段不均衡
        breakdown = self.get_stage_breakdown()
        for stage, data in breakdown.items():
            if data["percentage"] > 40:
                suggestions.append(
                    f"'{stage}' 阶段消耗占比 {data['percentage']}%，建议优化该阶段的 Prompt 长度"
                )

        # 3. 检查单次调用的平均消耗
        if self.avg_tokens_per_turn > 3000:
            suggestions.append(
                f"平均每次 API 调用消耗 {self.avg_tokens_per_turn:.0f} tokens，"
                "建议减少上下文注入的历史消息数量"
            )

        # 4. 检查输入/输出比例
        if self.total_input_tokens and self.total_output_tokens:
            ratio = self.total_input_tokens / self.total_output_tokens
            if ratio > 10:
                suggestions.append(
                    f"输入/输出 Token 比例为 {ratio:.1f}:1，输入占比过高，"
                    "建议压缩系统提示词和对话历史"
                )

        if not suggestions:
            suggestions.append("Token 消耗在合理范围内，无需额外优化")

        return suggestions

    def get_report(self) -> dict:
        """生成完整的 Token 消耗报告"""
        elapsed = time.time() - self._start_time
        return {
            "summary": {
                "total_tokens": self.total_tokens,
                "total_input_tokens": self.total_input_tokens,
                "total_output_tokens": self.total_output_tokens,
                "total_api_calls": self.total_api_calls,
                "total_cost_usd": self.total_cost,
                "avg_tokens_per_turn": round(self.avg_tokens_per_turn, 1),
                "duration_seconds": round(elapsed, 1),
                "model": self.model,
            },
            "budget": {
                "budget_usd": self.budget_usd,
                "spent_usd": self.total_cost,
                "remaining_usd": self.get_budget_remaining(),
                "is_over_budget": self.is_over_budget(),
            },
            "stage_breakdown": self.get_stage_breakdown(),
            "caller_breakdown": self.get_caller_breakdown(),
            "optimization_suggestions": self.get_suggestions(),
        }

    def to_dict_for_db(self) -> dict:
        """序列化为可存入数据库的字典"""
        return {
            "total_tokens": self.total_tokens,
            "total_cost_usd": self.total_cost,
            "total_api_calls": self.total_api_calls,
            "stage_breakdown": self.get_stage_breakdown(),
            "model": self.model,
        }
