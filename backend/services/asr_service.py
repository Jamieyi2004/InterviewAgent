"""
ASR 语音识别 —— 支持阿里云 DashScope Qwen3 ASR Flash Realtime 与本地部署（可插拔）。

本地实现：在 asr_providers 中扩展，或调用 register_asr_provider() 注册。
"""

from __future__ import annotations

import audioop
import base64
import io
import logging
import os
import threading
import wave
from pathlib import Path
from typing import Callable, Optional

import dashscope
import yaml
from dashscope.audio.qwen_omni import MultiModality, OmniRealtimeCallback, OmniRealtimeConversation
from dashscope.audio.qwen_omni.omni_realtime import TranscriptionParams

from config import DASHSCOPE_API_KEY

logger = logging.getLogger(__name__)

_asr_config: dict = {}

ASRProviderFn = Callable[[bytes, dict], Optional[str]]
_EXTRA_ASR_PROVIDERS: dict[str, ASRProviderFn] = {}

_URL_CN = "wss://dashscope.aliyuncs.com/api-ws/v1/realtime"
_URL_INTL = "wss://dashscope-intl.aliyuncs.com/api-ws/v1/realtime"


def register_asr_provider(name: str, fn: ASRProviderFn) -> None:
    """注册自定义 ASR（例如本机 HTTP 服务或其它厂商）。fn(pcm_s16le_mono_bytes, full_yaml_root) -> 文本。"""
    _EXTRA_ASR_PROVIDERS[name] = fn


def _apply_asr_env_override(config: dict) -> None:
    override = os.environ.get("ASR_PROVIDER", "").strip()
    if not override:
        return
    config["provider"] = override
    logger.info("ASR: 环境变量 ASR_PROVIDER=%s 已覆盖 yaml 中的 provider", override)


def _load_asr_config() -> dict:
    global _asr_config
    if _asr_config:
        return _asr_config

    config_path = Path(__file__).resolve().parent.parent / "asr_config.yaml"
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            _asr_config = yaml.safe_load(f) or {}
    else:
        _asr_config = {
            "provider": "qwen3-asr-flash-realtime",
            "qwen3-asr-flash-realtime": {
                "model": "qwen3-asr-flash-realtime",
                "region": "cn",
                "language": "zh",
                "sample_rate": 16000,
                "input_audio_format": "pcm",
                "enable_turn_detection": False,
            },
        }
    _apply_asr_env_override(_asr_config)
    return _asr_config


def reload_asr_config() -> None:
    global _asr_config
    _asr_config = {}
    _load_asr_config()


def get_current_asr_provider() -> str:
    return _load_asr_config().get("provider", "qwen3-asr-flash-realtime")


def _resolve_realtime_url(section: dict) -> str:
    if section.get("url"):
        return section["url"].rstrip("/")
    region = (section.get("region") or "cn").lower()
    return _URL_INTL if region == "intl" else _URL_CN


def _pcm_16k_mono_s16le_from_wav(wav_bytes: bytes) -> bytes:
    """将 WAV 转为 16kHz mono 16-bit little-endian PCM（与 Qwen 文档一致）。"""
    with wave.open(io.BytesIO(wav_bytes), "rb") as wf:
        channels = wf.getnchannels()
        sampwidth = wf.getsampwidth()
        framerate = wf.getframerate()
        frames = wf.readframes(wf.getnframes())

    if sampwidth != 2:
        raise ValueError(f"仅支持 16-bit WAV，当前 width={sampwidth}")

    if channels == 2:
        frames = audioop.tomono(frames, sampwidth, 0.5, 0.5)
    elif channels != 1:
        raise ValueError(f"不支持的声道数: {channels}")

    if framerate != 16000:
        frames, _ = audioop.ratecv(frames, sampwidth, 1, framerate, 16000, None)

    return frames


def normalize_audio_to_pcm_16k_mono(audio_bytes: bytes, *, hint_pcm: bool = False) -> bytes:
    """
    将上传内容规范为 16kHz mono s16le PCM。
    - hint_pcm=True 或内容非 RIFF：按 raw PCM 处理（须已为 16k/mono/s16le）。
    - 否则按 WAV 解析并必要时重采样。
    """
    if hint_pcm or len(audio_bytes) < 12 or audio_bytes[:4] != b"RIFF":
        return audio_bytes
    return _pcm_16k_mono_s16le_from_wav(audio_bytes)


class _QwenRealtimeASRCallback(OmniRealtimeCallback):
    """收集 OmniRealtime 转写事件（与官方文档事件名一致）。"""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.final_segments: list[str] = []
        self.last_stash: str = ""
        self.session_closed_code: Optional[int] = None
        self.session_created = threading.Event()

    def on_open(self) -> None:
        logger.debug("ASR OmniRealtime: WebSocket 已连接")

    def on_close(self, close_status_code, close_msg) -> None:
        self.session_closed_code = close_status_code
        logger.debug("ASR OmniRealtime: 连接关闭 code=%s msg=%s", close_status_code, close_msg)

    def on_event(self, message) -> None:
        if not isinstance(message, dict):
            return
        et = message.get("type", "")
        try:
            if et == "session.created":
                self.session_created.set()
            elif et == "conversation.item.input_audio_transcription.completed":
                tr = message.get("transcript") or ""
                with self._lock:
                    self.final_segments.append(tr)
            elif et == "conversation.item.input_audio_transcription.text":
                self.last_stash = message.get("stash") or ""
            elif et == "error":
                err = message.get("error") or message
                logger.warning("ASR OmniRealtime 服务端 error 事件: %s", err)
        except Exception as e:
            logger.warning("ASR 回调处理异常: %s", e)


def transcribe_pcm_bytes_with_qwen(pcm_bytes: bytes, overrides: Optional[dict] = None) -> Optional[str]:
    """
    使用 DashScope Qwen3 ASR Flash Realtime 识别整段 PCM（16kHz mono s16le）。

    流程：OmniRealtime 连接 → update_session（手动 commit）→ 分块 append → commit → end_session。
    """
    if not pcm_bytes:
        return None
    if not DASHSCOPE_API_KEY:
        logger.warning("ASR: 未配置 DASHSCOPE_API_KEY，跳过识别")
        return None

    cfg_root = _load_asr_config()
    section = dict(cfg_root.get("qwen3-asr-flash-realtime", {}))
    if overrides:
        section.update(overrides)

    model = section.get("model", "qwen3-asr-flash-realtime")
    url = _resolve_realtime_url(section)
    language = section.get("language", "zh")
    sample_rate = int(section.get("sample_rate", 16000))
    input_audio_format = section.get("input_audio_format", "pcm")
    enable_turn_detection = bool(section.get("enable_turn_detection", False))
    turn_detection_type = section.get("turn_detection_type", "server_vad")
    turn_detection_threshold = float(section.get("turn_detection_threshold", 0.0))
    turn_detection_silence_duration_ms = int(section.get("turn_detection_silence_duration_ms", 400))
    chunk_bytes = int(section.get("pcm_chunk_bytes", 3200))
    end_timeout = int(section.get("end_session_timeout_sec", 120))

    dashscope.api_key = DASHSCOPE_API_KEY

    cb = _QwenRealtimeASRCallback()
    conv: Optional[OmniRealtimeConversation] = OmniRealtimeConversation(
        model=model,
        url=url,
        callback=cb,
        api_key=DASHSCOPE_API_KEY,
    )

    transcription_params = TranscriptionParams(
        language=language,
        sample_rate=sample_rate,
        input_audio_format=input_audio_format,
    )

    try:
        conv.connect()
        if not cb.session_created.wait(timeout=15):
            raise TimeoutError("ASR: 等待 session.created 超时，请检查网络与 API Key")
        conv.update_session(
            output_modalities=[MultiModality.TEXT],
            enable_turn_detection=enable_turn_detection,
            turn_detection_type=turn_detection_type,
            turn_detection_threshold=turn_detection_threshold,
            turn_detection_silence_duration_ms=turn_detection_silence_duration_ms,
            enable_input_audio_transcription=True,
            transcription_params=transcription_params,
        )

        for i in range(0, len(pcm_bytes), chunk_bytes):
            chunk = pcm_bytes[i : i + chunk_bytes]
            conv.append_audio(base64.b64encode(chunk).decode("ascii"))

        if not enable_turn_detection:
            conv.commit()

        conv.end_session(timeout=end_timeout)

        with cb._lock:
            parts = list(cb.final_segments)
        text = "".join(parts).strip()
        if not text and cb.last_stash:
            text = cb.last_stash.strip()
        return text if text else None
    except Exception as e:
        logger.warning("ASR Qwen Realtime 识别失败: %s", e)
        return None
    finally:
        if conv is not None:
            try:
                conv.close()
            except Exception:
                pass


def transcribe_to_text(
    audio_bytes: bytes,
    *,
    raw_pcm: bool = False,
    overrides: Optional[dict] = None,
) -> Optional[str]:
    """
    根据 asr_config.yaml 的 provider 将音频转为文本。

    - raw_pcm=True：将 audio_bytes 视为已是 16kHz mono s16le PCM。
    - raw_pcm=False：若为 WAV（RIFF）则自动转 PCM；否则仍按原始 PCM 解析（与旧行为兼容）。
    """
    if not audio_bytes:
        return None

    cfg = _load_asr_config()
    provider = cfg.get("provider", "qwen3-asr-flash-realtime")

    pcm = normalize_audio_to_pcm_16k_mono(audio_bytes, hint_pcm=raw_pcm)

    fn = _EXTRA_ASR_PROVIDERS.get(provider)
    if fn is not None:
        return fn(pcm, cfg)

    if provider in ("qwen3-asr-flash-realtime", "qwen3-asr-flash", "dashscope-asr", "qwen-asr"):
        if not DASHSCOPE_API_KEY:
            logger.debug("ASR: 未配置 DASHSCOPE_API_KEY，跳过（provider=%s）", provider)
            return None
        merged = dict(cfg.get("qwen3-asr-flash-realtime", {}))
        if overrides:
            merged.update(overrides)
        return transcribe_pcm_bytes_with_qwen(pcm, overrides=merged)

    if provider == "local":
        logger.info("ASR provider=local 尚未实现具体引擎（可 register_asr_provider 或接入 asr_providers）")
        return None

    logger.warning("未知 ASR provider「%s」，尝试 Qwen Realtime", provider)
    if not DASHSCOPE_API_KEY:
        return None
    return transcribe_pcm_bytes_with_qwen(pcm, overrides=overrides)
