#!/usr/bin/env python3
"""
调通 CosyVoice TTS API：非流式调用，合成一段语音并保存为 MP3。
使用前请在 backend/.env 中配置 DASHSCOPE_API_KEY 或 LLM_API_KEY（二者同源）。
"""
import sys
from pathlib import Path

# 保证能导入 backend 包
backend_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_root))

# 先加载 .env（config 会读）
from dotenv import load_dotenv
load_dotenv(backend_root / ".env")

import dashscope
from dashscope.audio.tts_v2 import SpeechSynthesizer

from config import TTS_MODEL, TTS_VOICE, DASHSCOPE_API_KEY


def main():
    if not DASHSCOPE_API_KEY:
        print("错误：未配置 DASHSCOPE_API_KEY 或 LLM_API_KEY，请在 backend/.env 中设置")
        sys.exit(1)

    dashscope.api_key = DASHSCOPE_API_KEY
    # 北京地域（新加坡需改为 wss://dashscope-intl.aliyuncs.com/...）
    dashscope.base_websocket_api_url = "wss://dashscope.aliyuncs.com/api-ws/v1/inference"

    text = "你好，我是 AI 面试官。今天天气不错，我们开始面试吧。"
    out_path = backend_root / "scripts" / "tts_output.mp3"

    print(f"模型: {TTS_MODEL}, 音色: {TTS_VOICE}")
    print(f"合成文本: {text}")
    print("正在调用 TTS API（非流式）...")

    # 非流式：不传 callback，call() 返回完整音频 bytes
    synthesizer = SpeechSynthesizer(
        model=TTS_MODEL,
        voice=TTS_VOICE,
    )
    audio_bytes = synthesizer.call(text)

    if not audio_bytes:
        print("未收到音频数据，请检查 API Key 与模型/音色配置")
        sys.exit(1)

    out_path.write_bytes(audio_bytes)
    print(f"成功，已保存: {out_path} ({len(audio_bytes)} bytes)")


if __name__ == "__main__":
    main()
