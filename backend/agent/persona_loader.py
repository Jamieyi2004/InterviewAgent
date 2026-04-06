"""
面试官人设系统 —— 借鉴 Claude Code 的 Agent Definition 设计

核心设计：
1. 通过 YAML 配置文件定义不同面试官风格
2. 运行时动态加载和切换人设
3. 每个人设有独立的 system_prompt 增强、温度偏移、追问策略
4. 支持自定义扩展

参考：Claude Code src/tools/AgentTool/loadAgentsDir.ts
"""

import os
from typing import Dict, List, Optional
from dataclasses import dataclass

import yaml
from loguru import logger


# ======================== 数据模型 ========================

@dataclass
class InterviewerPersona:
    """面试官人设"""
    name: str                       # 人设名称（如"严格型面试官"）
    style: str                      # 风格描述
    description: str                # 详细描述
    system_prompt_addon: str        # 注入到 system prompt 的额外指令
    temperature_bias: float         # 温度偏移（正值更随机，负值更确定）
    follow_up_aggressiveness: str   # 追问激进程度：low/medium/high/very_high
    max_tokens_bias: int            # max_tokens 偏移
    evaluation_strictness: str      # 评估严格度：lenient/balanced/strict
    file_path: str = ""             # 配置文件路径

    @property
    def aggressiveness_score(self) -> float:
        """追问激进度数值（0-1）"""
        mapping = {"low": 0.2, "medium": 0.5, "high": 0.8, "very_high": 1.0}
        return mapping.get(self.follow_up_aggressiveness, 0.5)

    def apply_temperature(self, base_temperature: float) -> float:
        """应用温度偏移"""
        return max(0.1, min(1.0, base_temperature + self.temperature_bias))

    def apply_max_tokens(self, base_max_tokens: int) -> int:
        """应用 max_tokens 偏移"""
        return max(100, base_max_tokens + self.max_tokens_bias)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "style": self.style,
            "description": self.description,
            "temperature_bias": self.temperature_bias,
            "follow_up_aggressiveness": self.follow_up_aggressiveness,
            "evaluation_strictness": self.evaluation_strictness,
        }


# ======================== 默认人设（无 YAML 配置时使用） ========================

DEFAULT_PERSONA = InterviewerPersona(
    name="标准面试官",
    style="专业、均衡、标准流程",
    description="标准技术面试官，按标准流程进行面试",
    system_prompt_addon="",
    temperature_bias=0.0,
    follow_up_aggressiveness="medium",
    max_tokens_bias=0,
    evaluation_strictness="balanced",
)


# ======================== 人设加载器 ========================

class PersonaLoader:
    """
    面试官人设加载器

    使用方式：
        loader = PersonaLoader()
        personas = loader.load_all()           # 加载所有人设
        strict = loader.get_persona("严格型面试官")  # 获取指定人设
        names = loader.list_persona_names()     # 获取所有人设名称
    """

    def __init__(self, personas_dir: Optional[str] = None):
        if personas_dir is None:
            personas_dir = os.path.join(
                os.path.dirname(__file__), "personas"
            )
        self.personas_dir = personas_dir
        self._cache: Dict[str, InterviewerPersona] = {}
        self._loaded = False

    def load_all(self) -> List[InterviewerPersona]:
        """加载所有人设配置"""
        personas = []

        if not os.path.isdir(self.personas_dir):
            logger.warning("[Persona] 人设目录不存在: %s", self.personas_dir)
            self._cache["标准面试官"] = DEFAULT_PERSONA
            return [DEFAULT_PERSONA]

        for filename in os.listdir(self.personas_dir):
            if not filename.endswith(('.yaml', '.yml')):
                continue

            filepath = os.path.join(self.personas_dir, filename)
            persona = self._load_yaml(filepath)
            if persona:
                personas.append(persona)
                self._cache[persona.name] = persona
                logger.info("[Persona] 已加载人设: %s (%s)", persona.name, filename)

        # 确保至少有默认人设
        if not personas:
            personas.append(DEFAULT_PERSONA)
            self._cache["标准面试官"] = DEFAULT_PERSONA

        self._loaded = True
        logger.info("[Persona] 共加载 %d 个面试官人设", len(personas))
        return personas

    def get_persona(self, name: str) -> InterviewerPersona:
        """
        获取指定名称的人设

        Args:
            name: 人设名称

        Returns:
            InterviewerPersona，如果不存在则返回默认人设
        """
        if not self._loaded:
            self.load_all()

        return self._cache.get(name, DEFAULT_PERSONA)

    def get_persona_by_style(self, style_keyword: str) -> InterviewerPersona:
        """
        根据风格关键词模糊匹配人设

        Args:
            style_keyword: 风格关键词（如"严格"、"友好"、"压力"）

        Returns:
            匹配的 InterviewerPersona
        """
        if not self._loaded:
            self.load_all()

        for persona in self._cache.values():
            if style_keyword in persona.name or style_keyword in persona.style:
                return persona

        return DEFAULT_PERSONA

    def list_persona_names(self) -> List[str]:
        """获取所有可用的人设名称"""
        if not self._loaded:
            self.load_all()
        return list(self._cache.keys())

    def list_personas_info(self) -> List[dict]:
        """获取所有人设的简要信息（用于前端展示）"""
        if not self._loaded:
            self.load_all()
        return [p.to_dict() for p in self._cache.values()]

    def _load_yaml(self, filepath: str) -> Optional[InterviewerPersona]:
        """从 YAML 文件加载单个人设"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)

            if not data or not isinstance(data, dict):
                logger.warning("[Persona] 无效的 YAML 文件: %s", filepath)
                return None

            return InterviewerPersona(
                name=data.get("name", "未命名面试官"),
                style=data.get("style", ""),
                description=data.get("description", ""),
                system_prompt_addon=data.get("system_prompt_addon", ""),
                temperature_bias=float(data.get("temperature_bias", 0.0)),
                follow_up_aggressiveness=data.get("follow_up_aggressiveness", "medium"),
                max_tokens_bias=int(data.get("max_tokens_bias", 0)),
                evaluation_strictness=data.get("evaluation_strictness", "balanced"),
                file_path=filepath,
            )

        except Exception as e:
            logger.error("[Persona] 加载 YAML 失败: %s, 错误: %s", filepath, e)
            return None


# ======================== 全局单例 ========================

_persona_loader: Optional[PersonaLoader] = None


def get_persona_loader() -> PersonaLoader:
    """获取全局人设加载器（单例）"""
    global _persona_loader
    if _persona_loader is None:
        _persona_loader = PersonaLoader()
        _persona_loader.load_all()
    return _persona_loader
