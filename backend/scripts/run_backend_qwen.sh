#!/usr/bin/env bash
# 阿里云 Qwen TTS（需 DASHSCOPE_API_KEY）
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export TTS_PROVIDER=qwen-tts
PORT="${PORT:-8000}"
HOST="${HOST:-0.0.0.0}"
exec uvicorn main:app --reload --host "$HOST" --port "$PORT"
