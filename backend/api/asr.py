"""
ASR 语音识别 HTTP API —— 与 services/asr_service 配置一致，支持 DashScope 与本地占位。
"""

import logging

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from auth import get_current_user
from models.schemas import ASRTranscribeResponse
from models.user import User
from services.asr_service import get_current_asr_provider, transcribe_to_text

router = APIRouter(prefix="/api/asr", tags=["语音识别 ASR"])
logger = logging.getLogger(__name__)


@router.get("/provider", response_model=dict)
async def asr_provider(current_user: User = Depends(get_current_user)):
    """当前 ASR 提供方（来自 asr_config.yaml 或环境变量 ASR_PROVIDER）。"""
    return {"provider": get_current_asr_provider()}


@router.post("/transcribe", response_model=ASRTranscribeResponse)
async def asr_transcribe(
    file: UploadFile = File(..., description="音频文件：WAV（推荐 16kHz mono 16-bit）或原始 PCM"),
    raw_pcm: bool = Form(
        False,
        description="为 True 时将正文视为 16kHz mono s16le 裸 PCM（非 WAV 头）",
    ),
    language: str | None = Form(
        None,
        description="可选，覆盖 asr_config 中的识别语言（如 zh、en）",
    ),
    current_user: User = Depends(get_current_user),
):
    """
    上传音频并返回识别文本（同步阻塞至 OmniRealtime 会话结束）。

    需要配置 `DASHSCOPE_API_KEY`（或与 LLM 共用的阿里云 Key），且 `asr_config.yaml` 中
    `provider` 为 `qwen3-asr-flash-realtime`（默认）。
    """
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="空文件")

    overrides = {}
    if language and language.strip():
        overrides["language"] = language.strip()

    try:
        text = transcribe_to_text(
            data,
            raw_pcm=raw_pcm,
            overrides=overrides if overrides else None,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    provider = get_current_asr_provider()
    if text is None:
        logger.warning(
            "ASR 未得到文本: user_id=%s provider=%s filename=%s",
            current_user.id,
            provider,
            file.filename,
        )
        raise HTTPException(
            status_code=503,
            detail="语音识别失败或未配置有效引擎（请检查 DASHSCOPE_API_KEY、网络与 asr_config.yaml）",
        )

    return ASRTranscribeResponse(text=text, provider=provider)
