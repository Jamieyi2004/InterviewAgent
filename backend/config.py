"""
全局配置 —— 从 .env 文件或环境变量读取
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# 加载 .env
load_dotenv(Path(__file__).resolve().parent / ".env")

# ---- LLM 配置（阿里云 DashScope / Qwen） ----
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
LLM_MODEL = os.getenv("LLM_MODEL", "qwen3.5-flash")

# ---- 数据库 ----
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./interview_agent.db")

# ---- 上传目录 ----
UPLOAD_DIR = Path(__file__).resolve().parent / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

# ---- TTS / ASR（DashScope API Key）----
# 与 LLM 共用同一 Key：只配 LLM_API_KEY 即可；若单独设置 DASHSCOPE_API_KEY 则优先使用。
# TTS：tts_config.yaml；ASR：asr_config.yaml；均可通过环境变量切换提供方（TTS_PROVIDER / ASR_PROVIDER）
DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY", "") or LLM_API_KEY

# ---- 面试默认参数 ----
DEFAULT_MAX_QUESTIONS = {
    "opening": 1,
    "coding": 1,      # 算法题环节只出一道题
    "basic_qa": 3,
    "project_deep": 3,
    "summary": 1,
}

# ---- JWT 认证 ----
SECRET_KEY = os.getenv("SECRET_KEY", "ccnu-interview-agent-dev-secret-2024")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))  # 24h
