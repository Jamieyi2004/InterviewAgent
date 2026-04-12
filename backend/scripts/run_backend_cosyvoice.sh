#!/usr/bin/env bash
# 阿里云 CosyVoice（需 DASHSCOPE_API_KEY）
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export TTS_PROVIDER=cosyvoice
PORT="${PORT:-8000}"
HOST="${HOST:-0.0.0.0}"
exec uvicorn main:app --reload --host "$HOST" --port "$PORT"
