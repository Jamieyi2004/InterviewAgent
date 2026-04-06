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


logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：启动时初始化数据库"""
    setup_logging()
    t0 = time.time()
    init_db()
    logger.info("数据库表已初始化，用时 %.0f ms", (time.time() - t0) * 1000)
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
app.include_router(resume_router)
app.include_router(interview_router)
app.include_router(report_router)
app.include_router(enhanced_router)
app.include_router(sessions_router)
app.include_router(admin_router)


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
        ],
    }
