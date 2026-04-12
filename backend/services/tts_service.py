"""
TTS 语音合成服务 —— 支持阿里云 DashScope（CosyVoice / Qwen TTS）与本地 Step-Audio 等提供方。

新增提供方：在 _synthesize_with_builtin_provider 中增加分支，或调用 register_tts_provider()；
本地实现可放在 services/tts_providers/ 下。
"""

import base64
import logging
import os
import time
from pathlib import Path
from typing import Callable, Optional

import yaml
import dashscope
from dashscope.audio.tts_v2 import SpeechSynthesizer as CosyVoiceSynthesizer

from config import DASHSCOPE_API_KEY
from services.tts_providers.step_audio_local import (
    reset_step_audio_engine,
    synthesize_step_audio,
)

logger = logging.getLogger(__name__)

# 加载 TTS 配置
_tts_config: dict = {}

# 自定义提供方：fn(text, full_config_dict) -> Optional[bytes]；无需改核心分支即可挂载
TTSProviderFn = Callable[[str, dict], Optional[bytes]]
_EXTRA_TTS_PROVIDERS: dict[str, TTSProviderFn] = {}


def register_tts_provider(name: str, fn: TTSProviderFn) -> None:
    """注册自定义 TTS（如其它厂商 HTTP API）。fn 接收完整 YAML 根配置，自行读对应段落。"""
    _EXTRA_TTS_PROVIDERS[name] = fn


def _apply_tts_env_override(config: dict) -> None:
    """
    若设置环境变量 TTS_PROVIDER，覆盖 yaml 中的 provider。
    便于用不同启动脚本选择厂商而无需改配置文件。
    取值示例：step-audio | qwen-tts | cosyvoice
    """
    override = os.environ.get("TTS_PROVIDER", "").strip()
    if not override:
        return
    config["provider"] = override
    logger.info("TTS: 环境变量 TTS_PROVIDER=%s 已覆盖 yaml 中的 provider", override)


def _load_tts_config() -> dict:
    """加载 TTS 配置文件"""
    global _tts_config
    if _tts_config:
        return _tts_config

    config_path = Path(__file__).resolve().parent.parent / "tts_config.yaml"
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            _tts_config = yaml.safe_load(f) or {}
    else:
        # 默认配置
        _tts_config = {
            "provider": "cosyvoice",
            "cosyvoice": {
                "model": "cosyvoice-v3-flash",
                "voice": "longanyang",
            },
            "qwen-tts": {
                "model": "qwen3-tts-flash",
                "voice": "Cherry",
                "language_type": "Chinese",
            },
        }
    _apply_tts_env_override(_tts_config)
    return _tts_config


def _provider_needs_dashscope_key(provider: str) -> bool:
    """仅使用阿里云 DashScope 的提供方需要 DASHSCOPE_API_KEY。"""
    if provider in _EXTRA_TTS_PROVIDERS:
        return False
    if provider == "step-audio":
        return False
    return True


def _synthesize_cosyvoice(text: str) -> Optional[bytes]:
    """使用 CosyVoice 合成语音"""
    config = _load_tts_config().get("cosyvoice", {})
    model = config.get("model", "cosyvoice-v3-flash")
    voice = config.get("voice", "longanyang")

    dashscope.api_key = DASHSCOPE_API_KEY
    dashscope.base_websocket_api_url = "wss://dashscope.aliyuncs.com/api-ws/v1/inference"

    synthesizer = CosyVoiceSynthesizer(
        model=model,
        voice=voice,
    )
    audio_bytes = synthesizer.call(text.strip())
    return audio_bytes if audio_bytes else None


def _synthesize_qwen_tts(text: str, stream: bool = False) -> Optional[bytes]:
    """
    使用 Qwen TTS (qwen3-tts-flash) 合成语音

    Args:
        text: 要合成的文本
        stream: 是否使用流式输出（流式返回 base64 数据，非流式返回音频 URL）

    Returns:
        音频二进制数据（WAV 格式）
    """
    config = _load_tts_config().get("qwen-tts", {})
    model = config.get("model", "qwen3-tts-flash")
    voice = config.get("voice", "Cherry")
    language_type = config.get("language_type", "Auto")
    instructions = config.get("instructions", None)
    optimize_instructions = config.get("optimize_instructions", False)

    dashscope.api_key = DASHSCOPE_API_KEY
    dashscope.base_http_api_url = "https://dashscope.aliyuncs.com/api/v1"

    # 构建请求参数
    call_params = {
        "model": model,
        "api_key": DASHSCOPE_API_KEY,
        "text": text.strip(),
        "voice": voice,
        "stream": stream,
    }

    # 可选参数
    if language_type:
        call_params["language_type"] = language_type

    # 指令控制（仅 qwen3-tts-instruct-flash 支持）
    if instructions and "instruct" in model.lower():
        call_params["instructions"] = instructions
        if optimize_instructions:
            call_params["optimize_instructions"] = True

    if stream:
        # 流式输出：逐块读取 base64 音频数据
        response = dashscope.MultiModalConversation.call(**call_params)
        audio_chunks = []
        for chunk in response:
            if chunk and chunk.status_code == 200:
                output = chunk.output
                if output and "audio" in output:
                    audio_obj = output["audio"]
                    data = audio_obj.get("data") if isinstance(audio_obj, dict) else None
                    if data:
                        audio_chunks.append(base64.b64decode(data))
        return b"".join(audio_chunks) if audio_chunks else None
    else:
        # 非流式输出：返回音频 URL，需下载
        response = dashscope.MultiModalConversation.call(**call_params)

        if response and response.status_code == 200:
            output = response.output
            if output and "audio" in output:
                audio_obj = output["audio"]
                # 非流式返回 URL
                audio_url = audio_obj.get("url") if isinstance(audio_obj, dict) else None
                if audio_url:
                    return _download_audio_from_url(audio_url)
                # 也可能直接返回 data
                audio_data = audio_obj.get("data") if isinstance(audio_obj, dict) else audio_obj
                if audio_data:
                    if isinstance(audio_data, str):
                        return base64.b64decode(audio_data)
                    return audio_data
        else:
            error_msg = getattr(response, "message", str(response)) if response else "Unknown error"
            logger.warning("Qwen TTS 合成失败: %s", error_msg)

    return None


def _download_audio_from_url(url: str) -> Optional[bytes]:
    """从 URL 下载音频文件"""
    import requests
    try:
        resp = requests.get(url, timeout=30)
        if resp.status_code == 200:
            return resp.content
        logger.warning("下载音频失败: HTTP %d", resp.status_code)
    except Exception as e:
        logger.warning("下载音频异常: %s", e)
    return None


def _synthesize_with_builtin_provider(text: str, provider: str, config: dict) -> Optional[bytes]:
    """内置提供方分发（不含 register_tts_provider 注册的项）。"""
    if provider in ("qwen-tts", "qwen3-tts"):
        stream = config.get("qwen-tts", {}).get("stream", True)
        return _synthesize_qwen_tts(text, stream=stream)
    if provider in ("cosyvoice", "cosyvoice-v3", "ali-cosyvoice"):
        return _synthesize_cosyvoice(text)
    if provider == "step-audio":
        return synthesize_step_audio(text, config.get("step-audio", {}))
    return None


def synthesize_to_bytes(text: str, *, quiet: bool = False) -> Optional[bytes]:
    """
    将文本合成为语音，返回音频二进制；失败返回 None（不抛错，便于对话流程继续）。

    根据 tts_config.yaml 中的 provider 选择提供方。
    - CosyVoice: 通常为 MP3
    - Qwen TTS: WAV
    - step-audio: 本地 WAV

    quiet: 为 True 时不打「合成成功」类 INFO（用于连接后后台预热，避免刷屏）。
    """
    if not text or not text.strip():
        return None

    config = _load_tts_config()
    provider = config.get("provider", "cosyvoice")

    if _provider_needs_dashscope_key(provider) and not DASHSCOPE_API_KEY:
        logger.debug("TTS 未配置 DASHSCOPE_API_KEY，跳过语音合成（provider=%s）", provider)
        return None

    try:
        t0 = time.time()

        fn = _EXTRA_TTS_PROVIDERS.get(provider)
        if fn is not None:
            audio_bytes = fn(text, config)
        else:
            audio_bytes = _synthesize_with_builtin_provider(text, provider, config)
            if audio_bytes is None and provider not in (
                "qwen-tts",
                "qwen3-tts",
                "cosyvoice",
                "cosyvoice-v3",
                "ali-cosyvoice",
                "step-audio",
            ):
                logger.warning("未知 TTS provider「%s」，回退 CosyVoice", provider)
                if not DASHSCOPE_API_KEY:
                    return None
                audio_bytes = _synthesize_cosyvoice(text)

        dt = (time.time() - t0) * 1000
        if audio_bytes:
            if not quiet:
                logger.info(
                    "TTS [%s] 合成成功，耗时 %.0f ms，文本长度=%d，音频字节=%d",
                    provider,
                    dt,
                    len(text),
                    len(audio_bytes),
                )
            else:
                logger.debug(
                    "TTS [%s] 预热合成完成，耗时 %.0f ms",
                    provider,
                    dt,
                )
        else:
            logger.warning(
                "TTS [%s] 未生成音频（返回 None），耗时 %.0f ms，文本长度=%d。"
                " 若使用 step-audio：需当前环境可 import torch 并正确配置 code_path/model_path；"
                " 若使用 qwen-tts/cosyvoice：检查 DASHSCOPE_API_KEY 与网络。",
                provider,
                dt,
                len(text),
            )
        return audio_bytes
    except Exception as e:
        logger.warning("TTS [%s] 合成失败: %s", provider, e)
        return None


def reload_tts_config():
    """重新加载 TTS 配置（配置文件修改后调用）"""
    global _tts_config
    _tts_config = {}
    reset_step_audio_engine()
    _load_tts_config()


def get_current_provider() -> str:
    """获取当前 TTS 提供商"""
    return _load_tts_config().get("provider", "cosyvoice")
