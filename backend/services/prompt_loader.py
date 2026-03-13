"""Prompt 加载工具：从 YAML 读取面试官 system prompt。"""

from functools import lru_cache
from pathlib import Path
from typing import Any, Dict

import yaml

from agent.prompts import INTERVIEWER_SYSTEM_PROMPT

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"


@lru_cache
def _load_interviewer_yaml() -> Dict[str, Any]:
    path = PROMPTS_DIR / "interviewer.yaml"
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, dict):
        return {}
    return data


def get_interviewer_system_prompt(profile: str | None = None) -> str:
    """获取面试官 system prompt 模板。

    优先从 prompts/interviewer.yaml 中读取，对应 key=profile（默认 default），
    读取不到时回退到硬编码的 INTERVIEWER_SYSTEM_PROMPT。
    """
    data = _load_interviewer_yaml()
    key = profile or "default"

    try:
        conf = data.get(key)  # type: ignore[assignment]
        if isinstance(conf, dict):
            tmpl = conf.get("system_prompt")
            if isinstance(tmpl, str) and tmpl.strip():
                return tmpl
    except Exception:
        pass

    return INTERVIEWER_SYSTEM_PROMPT
