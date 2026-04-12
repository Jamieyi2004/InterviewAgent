"""
本地 Step-Audio-TTS-3B：需本机已按 stepfun-ai/Step-Audio 部署，输出 WAV bytes。

上游仓库内相对路径（speakers/ 等）依赖进程当前工作目录，初始化与推理时
会临时 chdir 到 code_path，与在仓库根目录运行 tts_inference.py 行为一致。
"""

from __future__ import annotations

import io
import logging
import os
import sys
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

# 缺少 torch 时只打一次说明，避免每句面试都刷长 traceback
_torch_missing_logged = False
# 首次合成时打印解析后的路径，便于核对是否指向本机 step-audio / 模型目录
_step_audio_paths_logged = False

_lock = threading.Lock()
# (code_dir, tts_engine) — speaker 每次调用传入，不必重建引擎
_engine: Optional[tuple[Path, Any]] = None
_config_signature: Optional[tuple[str, str]] = None
# step-audio 仓库根目录下的 utils.py（含 torchaudio_save）；与 InterviewAgent/backend/utils 包区分
_stepaudio_utils_mod: Optional[Any] = None


def _pop_utils_modules_from_sys() -> dict[str, Any]:
    """
    InterviewAgent 的 backend/utils 会注册为顶层包 `utils`，遮挡 step-audio 同名 utils.py。
    加载 Step-Audio 前暂时移出 sys.modules，加载完再恢复。
    """
    saved: dict[str, Any] = {}
    for k in list(sys.modules.keys()):
        if k == "utils" or k.startswith("utils."):
            saved[k] = sys.modules.pop(k)
    return saved


def _restore_sys_modules(saved: dict[str, Any]) -> None:
    sys.modules.update(saved)


@contextmanager
def _chdir(path: Path):
    old = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(old)


def reset_step_audio_engine() -> None:
    """配置热加载时丢弃引擎，下次合成时按新路径重建。"""
    global _engine, _config_signature, _stepaudio_utils_mod
    with _lock:
        _engine = None
        _config_signature = None
        _stepaudio_utils_mod = None


def _backend_root() -> Path:
    # backend/services/tts_providers/step_audio_local.py -> backend
    return Path(__file__).resolve().parent.parent.parent


def _resolve_path(rel_or_abs: str) -> Path:
    p = Path(rel_or_abs)
    if p.is_absolute():
        return p.resolve()
    return (_backend_root() / p).resolve()


def _require_torch() -> bool:
    """Step-Audio 依赖 PyTorch；当前进程未安装时返回 False 并记一次 ERROR。"""
    global _torch_missing_logged
    try:
        import torch  # noqa: F401
        return True
    except ImportError:
        if not _torch_missing_logged:
            _torch_missing_logged = True
            logger.error(
                "TTS step-audio: 当前 Python 环境未安装 torch，无法加载 Step-Audio。"
                "当前进程解释器: %s",
                sys.executable,
            )
            logger.error(
                "解决办法：① conda activate <含 torch 的环境> 后再启动 uvicorn；"
                "② 或在当前环境 pip 安装 torch；"
                "③ 或 tts_config.yaml 改为 provider: qwen-tts 并配置 DASHSCOPE_API_KEY。"
            )
        return False


def _ensure_engine(code_path: str, model_path: str) -> tuple[Path, Any]:
    """懒加载 StepAudioTokenizer + StepAudioTTS，单例 + 线程锁。"""
    global _engine, _config_signature
    sig = (code_path, model_path)
    with _lock:
        if _engine is not None and _config_signature == sig:
            return _engine

        code_dir = _resolve_path(code_path)
        model_dir = _resolve_path(model_path)
        if not code_dir.is_dir():
            logger.error("step-audio code_path 不存在或不是目录: %s", code_dir)
            raise FileNotFoundError(str(code_dir))
        if not model_dir.is_dir():
            logger.error("step-audio model_path 不存在或不是目录: %s", model_dir)
            raise FileNotFoundError(str(model_dir))

        tok_dir = model_dir / "Step-Audio-Tokenizer"
        tts_dir = model_dir / "Step-Audio-TTS-3B"
        if not tok_dir.is_dir() or not tts_dir.is_dir():
            logger.error(
                "model_path 下需包含 Step-Audio-Tokenizer 与 Step-Audio-TTS-3B 目录: %s",
                model_dir,
            )
            raise FileNotFoundError(str(model_dir))

        if str(code_dir) not in sys.path:
            sys.path.insert(0, str(code_dir))

        global _stepaudio_utils_mod
        _saved_utils = _pop_utils_modules_from_sys()
        try:
            with _chdir(code_dir):
                import utils as _sa_utils  # type: ignore  # noqa: F401 — step-audio/utils.py
                _stepaudio_utils_mod = _sa_utils
                from tokenizer import StepAudioTokenizer  # type: ignore
                from tts import StepAudioTTS  # type: ignore

                tokenizer = StepAudioTokenizer(str(tok_dir))
                tts = StepAudioTTS(str(tts_dir), tokenizer)
        finally:
            _restore_sys_modules(_saved_utils)

        _engine = (code_dir, tts)
        _config_signature = sig
        logger.info(
            "Step-Audio 本地引擎已加载: code=%s model=%s",
            code_dir,
            model_dir,
        )
        return _engine


def synthesize_step_audio(text: str, cfg: dict) -> Optional[bytes]:
    """
    cfg 来自 tts_config.yaml 的 step-audio 段：
      code_path, model_path, speaker（可选，默认 Tingting）
    """
    if not (text or "").strip():
        return None
    code_path = cfg.get("code_path") or ""
    model_path = cfg.get("model_path") or ""
    speaker = cfg.get("speaker") or "Tingting"
    if not code_path or not model_path:
        logger.error("step-audio 需配置 code_path 与 model_path，当前段内容: %s", cfg)
        return None

    global _step_audio_paths_logged
    if not _step_audio_paths_logged:
        _step_audio_paths_logged = True
        cd = _resolve_path(code_path)
        md = _resolve_path(model_path)
        logger.info(
            "step-audio 路径解析: code_path -> %s (is_dir=%s), model_path -> %s (is_dir=%s), "
            "解释器=%s",
            cd,
            cd.is_dir(),
            md,
            md.is_dir(),
            sys.executable,
        )

    if not _require_torch():
        return None
    try:
        code_dir, tts = _ensure_engine(code_path, model_path)
    except Exception as e:
        logger.exception("Step-Audio 引擎初始化失败: %s", e)
        return None

    if str(code_dir) not in sys.path:
        sys.path.insert(0, str(code_dir))

    with _lock:
        try:
            with _chdir(code_dir):
                output_audio, sr = tts(text.strip(), speaker)
        except Exception as e:
            logger.exception("Step-Audio 合成失败: %s", e)
            return None

        if output_audio is None:
            return None

        buf = io.BytesIO()
        try:
            if _stepaudio_utils_mod is None:
                logger.error("step-audio: 内部错误，step-audio utils 模块未初始化")
                return None
            _stepaudio_utils_mod.torchaudio_save(
                buf, output_audio, sample_rate=sr, format="wav"
            )
        except Exception as e:
            logger.exception("Step-Audio WAV 编码失败: %s", e)
            return None

    return buf.getvalue()
