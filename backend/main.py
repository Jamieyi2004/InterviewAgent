"""
FastAPI 应用入口

启动命令: uvicorn main:app --reload --port 8000
"""

from contextlib import asynccontextmanager
import logging
import time

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from logging_config import setup_logging
from models.database import init_db
from api.resume import router as resume_router
from api.interview import router as interview_router
from api.report import router as report_router
from api.enhanced import router as enhanced_router
from api.sessions import router as sessions_router
from api.admin import router as admin_router
from api.resume_analysis import router as resume_analysis_router
from api.coaching import router as coaching_router
from api.knowledge import router as knowledge_router
from api.auth import router as auth_router
from api.asr import router as asr_router

# 确保新模型被导入（init_db 需要）
import models.resume_analysis  # noqa: F401
import models.coaching  # noqa: F401
import models.user  # noqa: F401


logger = logging.getLogger(__name__)


def _check_step_audio_can_import_torch() -> None:
    """provider=step-audio 时必须在当前进程内能 import torch，否则 TTS 永远无声。"""
    import os

    try:
        from services.tts_service import _load_tts_config
    except Exception:
        return
    cfg = _load_tts_config()
    override = (os.environ.get("TTS_PROVIDER") or "").strip()
    provider = override if override else cfg.get("provider", "")
    if provider != "step-audio":
        return
    try:
        import torch

        logger.info("TTS step-audio: 已检测到 torch %s", torch.__version__)
    except ImportError:
        msg = (
            "TTS 为 step-audio，但当前 Python 无法 import torch，语音将不可用。\n"
            "请用带 PyTorch 的 conda 环境启动后端，例如：\n"
            "  bash backend/scripts/run_backend_step_audio.sh\n"
            "或：conda activate stepaudio && cd backend && python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000\n"
            "勿使用未安装 torch 的 interview-agent-venv 直接跑 step-audio。"
        )
        logger.critical(msg)
        raise RuntimeError(
            "step-audio 需要 PyTorch：当前解释器无法 import torch，进程已中止。"
        )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：启动时初始化数据库"""
    setup_logging()
    _check_step_audio_can_import_torch()
    t0 = time.time()
    init_db()
    logger.info("数据库表已初始化，用时 %.0f ms", (time.time() - t0) * 1000)

    # 初始化 RAG 面试题库
    from services.rag_service import KnowledgeRAGService
    try:
        rag = KnowledgeRAGService.get_instance()
        rag.init_knowledge_base()
    except Exception as e:
        logger.warning(f"RAG 知识库初始化失败（不影响核心功能）: {e}")

    yield
    logger.info("应用关闭")


app = FastAPI(
    title="🎯 AI 面试官系统",
    description="基于 LLM 的智能模拟面试系统 —— 上传简历 → AI面试对话 → 生成评估报告",
    version="0.1.0-mvp",
    lifespan=lifespan,
)

# ---- CORS 配置（允许前端跨域访问）----
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://21.91.202.205:3000",  # 服务器外部访问
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---- 注册路由 ----
app.include_router(auth_router)
app.include_router(resume_router)
app.include_router(interview_router)
app.include_router(report_router)
app.include_router(enhanced_router)
app.include_router(sessions_router)
app.include_router(admin_router)
app.include_router(resume_analysis_router)
app.include_router(coaching_router)
app.include_router(knowledge_router)
app.include_router(asr_router)


# ---- 根路由（健康检查）----
@app.get("/", tags=["系统"])
async def root():
    return {
        "message": "🎯 AI 面试官系统 API 运行中",
        "docs": "/docs",
        "version": "0.2.0-enhanced",
        "features": [
            "面试策略规划器",
            "结构化会话记忆",
            "上下文压缩",
            "实时评估Agent",
            "后台洞察提取",
            "Token消耗追踪",
            "面试官人设系统",
            "技能系统",
            "生命周期钩子",
            "增强安全过滤",
            "多用户认证与权限管理",
            "简历分析优化",
            "面试辅导教练",
            "面试题库与技巧",
            "RAG 知识库检索增强",
        ],
    }
