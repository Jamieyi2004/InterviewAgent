#!/usr/bin/env bash
# Step-Audio 本地 TTS 专用：强制使用 conda 环境中已安装 PyTorch 的解释器启动 uvicorn。
# 用法（在任意目录）：
#   bash /path/to/InterviewAgent/backend/scripts/run_backend_step_audio.sh
# 指定 conda 环境名（默认 stepaudio）：
#   STEPAUDIO_CONDA_ENV=myenv bash ...
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

export TTS_PROVIDER="${TTS_PROVIDER:-step-audio}"
PORT="${PORT:-8000}"
HOST="${HOST:-0.0.0.0}"
ENV_NAME="${STEPAUDIO_CONDA_ENV:-stepaudio}"

if ! command -v conda &>/dev/null; then
  echo "ERROR: 未找到 conda 命令。Step-Audio 需要 PyTorch，请先安装 Anaconda/Miniconda，或手动执行："
  echo "  conda activate ${ENV_NAME}"
  echo "  cd $(pwd) && python -m uvicorn main:app --reload --host ${HOST} --port ${PORT}"
  exit 1
fi

# 非交互 shell 也能 activate
eval "$(conda shell.bash hook)"
conda activate "$ENV_NAME"

if ! python -c "import torch" 2>/dev/null; then
  echo "ERROR: conda 环境「${ENV_NAME}」无法 import torch。"
  echo "  请确认环境名正确：conda env list"
  echo "  或设置：STEPAUDIO_CONDA_ENV=你的环境名"
  exit 1
fi

echo "Step-Audio 后端：python=$(command -v python) torch OK"
exec python -m uvicorn main:app --reload --host "$HOST" --port "$PORT"
