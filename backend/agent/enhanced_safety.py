"""
增强安全过滤器 —— 借鉴 Claude Code 的 Safety Filter + Permission System

核心能力：
1. Prompt 注入检测（候选人试图操控面试官）
2. AI 生成回答检测（疑似 ChatGPT/Claude 代答）
3. 敏感信息检测（候选人泄露公司机密）
4. 角色混乱检测（继承原有 SafetyFilter）
5. 元信息泄露防护（继承原有 SafetyFilter）

参考：Claude Code src/tools/BashTool/bashSecurity.ts
"""

import re
from typing import List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

from loguru import logger


class ThreatLevel(str, Enum):
    """威胁等级"""
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class SafetyCheckResult:
    """安全检查结果"""
    is_safe: bool
    threat_level: ThreatLevel
    checks: List[dict]          # 每项检查的详细结果
    filtered_text: str          # 过滤后的文本
    warnings: List[str]         # 警告信息


class EnhancedSafetyFilter:
    """
    增强安全过滤器

    使用方式：
        safety = EnhancedSafetyFilter()

        # 检查候选人输入
        result = safety.check_candidate_input("候选人的回答")
        if not result.is_safe:
            print(result.warnings)

        # 检查面试官输出
        result = safety.check_interviewer_output("面试官的回复")
        filtered_text = result.filtered_text
    """

    def __init__(self):
        # ---- Prompt 注入检测模式 ----
        self.injection_patterns = [
            # 直接指令注入
            (r'忽略.*(?:之前|以上|上面).*(?:指令|提示|要求)', "直接指令覆盖"),
            (r'你现在是', "角色替换尝试"),
            (r'(?:请|帮我|你来)扮演', "角色扮演请求"),
            (r'忘记.*(?:规则|身份|角色)', "规则遗忘尝试"),
            (r'(?:不要|别).*(?:面试|问问题|考察)', "流程干扰尝试"),
            # 英文注入
            (r'ignore\s+(?:previous|above|all)\s+instructions', "英文指令注入"),
            (r'you\s+are\s+now', "英文角色替换"),
            (r'system\s*(?:prompt|message)', "系统提示词探测"),
            (r'(?:DAN|jailbreak|bypass)', "越狱尝试"),
            # 间接注入
            (r'(?:输出|打印|显示).*(?:系统|prompt|提示词)', "提示词提取尝试"),
            (r'(?:repeat|重复).*(?:system|系统)', "系统信息泄露尝试"),
        ]

        # ---- AI 生成回答特征 ----
        self.ai_generation_patterns = [
            # 典型 AI 回答开头
            (r'^(?:好的|当然|很好的问题)[，,](?:让我来|我来)(?:详细|系统)?(?:解释|说明|回答)', "AI 典型开头"),
            # 过度结构化
            (r'(?:首先|第一)[，,].*(?:其次|第二)[，,].*(?:最后|第三)', "过度结构化"),
            # AI 自我暴露
            (r'(?:作为|身为)(?:一个)?(?:AI|人工智能|语言模型)', "AI 自我暴露"),
            # 免责声明
            (r'(?:需要注意的是|值得一提的是|这里有一个重要的)', "AI 典型过渡"),
        ]

        # ---- 敏感信息模式 ----
        self.sensitive_patterns = [
            # 公司内部信息
            (r'(?:内部|机密|保密|confidential)', "可能包含机密信息"),
            # 个人隐私
            (r'\b\d{17,18}[xX\d]\b', "疑似身份证号"),
            (r'\b1[3-9]\d{9}\b', "疑似手机号"),
            (r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', "疑似邮箱地址"),
        ]

        # ---- 角色混乱检测（继承） ----
        self.role_confusion_patterns = [
            (r'我叫\w+[，,]来自', "面试官自我介绍"),
            (r'我的学历是', "面试官暴露身份"),
            (r'我毕业于', "面试官暴露身份"),
            (r'我做过的项目有', "面试官角色混乱"),
        ]

        # ---- 元信息泄露关键词 ----
        self.meta_leak_keywords = [
            "当前阶段是", "根据我的 prompt", "作为AI", "作为一个AI",
            "我是一个语言模型", "我的训练数据", "面试阶段为",
            "system prompt", "系统提示",
        ]

    def check_candidate_input(self, text: str) -> SafetyCheckResult:
        """
        检查候选人输入的安全性

        检查项：
        1. Prompt 注入检测
        2. AI 生成回答检测
        3. 敏感信息检测
        """
        checks = []
        warnings = []
        threat_level = ThreatLevel.NONE

        # 1. Prompt 注入检测
        injection_result = self._check_patterns(text, self.injection_patterns, "prompt_injection")
        checks.append(injection_result)
        if injection_result["detected"]:
            threat_level = ThreatLevel.HIGH
            warnings.append(f"检测到可能的 Prompt 注入: {injection_result['detail']}")
            logger.warning("[Safety] Prompt注入检测: %s", injection_result["detail"])

        # 2. AI 生成回答检测
        ai_result = self._check_ai_generated(text)
        checks.append(ai_result)
        if ai_result["detected"]:
            if threat_level.value < ThreatLevel.MEDIUM.value:
                threat_level = ThreatLevel.MEDIUM
            warnings.append(f"回答疑似 AI 生成: {ai_result['detail']}")
            logger.info("[Safety] AI生成检测: %s, 分数=%.2f", ai_result["detail"], ai_result.get("score", 0))

        # 3. 敏感信息检测
        sensitive_result = self._check_patterns(text, self.sensitive_patterns, "sensitive_info")
        checks.append(sensitive_result)
        if sensitive_result["detected"]:
            if threat_level.value < ThreatLevel.LOW.value:
                threat_level = ThreatLevel.LOW
            warnings.append(f"包含敏感信息: {sensitive_result['detail']}")

        return SafetyCheckResult(
            is_safe=(threat_level.value <= ThreatLevel.LOW.value),
            threat_level=threat_level,
            checks=checks,
            filtered_text=text,  # 候选人输入不做修改，只报告
            warnings=warnings,
        )

    def check_interviewer_output(self, text: str) -> SafetyCheckResult:
        """
        检查面试官输出的安全性

        检查项：
        1. 角色混乱检测
        2. 元信息泄露检测
        3. 格式异常清理
        """
        checks = []
        warnings = []
        threat_level = ThreatLevel.NONE
        filtered_text = text

        # 1. 角色混乱检测
        confusion_result = self._check_patterns(text, self.role_confusion_patterns, "role_confusion")
        checks.append(confusion_result)
        if confusion_result["detected"]:
            threat_level = ThreatLevel.MEDIUM
            warnings.append(f"检测到角色混乱: {confusion_result['detail']}")

        # 2. 元信息泄露检测 + 过滤
        for keyword in self.meta_leak_keywords:
            if keyword in filtered_text:
                filtered_text = filtered_text.replace(keyword, "")
                warnings.append(f"已过滤元信息泄露: {keyword}")
                if threat_level.value < ThreatLevel.LOW.value:
                    threat_level = ThreatLevel.LOW

        # 3. 格式异常清理
        filtered_text = self._clean_format(filtered_text)

        return SafetyCheckResult(
            is_safe=(threat_level.value <= ThreatLevel.LOW.value),
            threat_level=threat_level,
            checks=checks,
            filtered_text=filtered_text,
            warnings=warnings,
        )

    def _check_patterns(
        self,
        text: str,
        patterns: List[Tuple[str, str]],
        check_type: str,
    ) -> dict:
        """检查文本是否匹配指定模式"""
        detected = []
        for pattern, desc in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                detected.append(desc)

        return {
            "type": check_type,
            "detected": bool(detected),
            "detail": "; ".join(detected) if detected else "未检测到",
            "matches": detected,
        }

    def _check_ai_generated(self, text: str) -> dict:
        """
        检测回答是否疑似 AI 生成

        基于多个特征的综合评分：
        - 模式匹配（典型 AI 句式）
        - 结构特征（过于整齐的列表、编号）
        - 长度特征（异常长且完美）
        """
        score = 0.0
        signals = []

        # 1. 模式匹配
        for pattern, desc in self.ai_generation_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                score += 0.3
                signals.append(desc)

        # 2. 过于整齐的编号列表
        numbered_items = re.findall(r'^\d+[.、]\s', text, re.MULTILINE)
        if len(numbered_items) >= 4:
            score += 0.2
            signals.append(f"包含{len(numbered_items)}个编号列表项")

        # 3. 异常长度（面试中单个回答超过 500 字比较异常）
        if len(text) > 500:
            score += 0.1
            signals.append(f"回答长度异常({len(text)}字)")

        # 4. Markdown 格式（面试口语中不自然）
        if re.search(r'[*#`]', text):
            score += 0.1
            signals.append("包含 Markdown 格式")

        # 5. 总结性语句
        if re.search(r'(?:综上所述|总之|总结一下|以上就是)', text):
            score += 0.15
            signals.append("包含总结性语句")

        detected = score >= 0.5

        return {
            "type": "ai_generation",
            "detected": detected,
            "score": round(score, 2),
            "detail": "; ".join(signals) if signals else "未检测到 AI 生成特征",
            "signals": signals,
        }

    @staticmethod
    def _clean_format(text: str) -> str:
        """清理格式异常"""
        # 移除 LaTeX \boxed{...}
        text = re.sub(r"\\boxed\{([^}]*)\}", r"\1", text)
        # 移除多余空行
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text.strip()

    def get_stats(self) -> dict:
        """获取安全检查统计（可用于仪表盘）"""
        return {
            "injection_patterns_count": len(self.injection_patterns),
            "ai_detection_patterns_count": len(self.ai_generation_patterns),
            "sensitive_patterns_count": len(self.sensitive_patterns),
        }
