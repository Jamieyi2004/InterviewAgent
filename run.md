# InterviewAgent 运行指南

文档说明：本机开发、远程 Linux（如 VSCode SSH）都适用；差别主要在监听地址 `127.0.0.1` 与 `0.0.0.0`。

---

## 1. 环境要求

| 依赖 | 版本 | 备注 |
|------|------|------|
| Python | 3.11+ | 不要用系统自带的 3.6 |
| Node.js | 18+（推荐 20+） | 过旧会报 `Cannot find module 'node:fs'` |

Mac 若建 venv 报 symlink 错误，用：`python3.11 -m venv venv --copies`。

---

## 2. 后端装什么：先选对场景

| 场景 | Python 环境 | 安装命令（在对应环境里执行） |
|------|----------------|------------------------------|
| **常用**：只用阿里云 TTS（Qwen / CosyVoice） | 项目外 venv，如 `interview-agent-venv` | `pip install -r backend/requirements.txt` |
| **本地 Step-Audio 语音** | 已装 **PyTorch** 的 conda，如 `stepaudio` | 先按 [PyTorch 官网](https://pytorch.org/get-started/locally/) 装 `torch` / `torchaudio`，再 `pip install -r backend/requirements-step-audio.txt` |

说明：

- 项目目录名是 **`InterviewAgent`**；虚拟环境常建在**与它同级**的目录，例如 **`~/yjm/interview-agent-venv`**（不是 `~/interview-agent-venv`，除非你特意建在家目录下）。
- Step-Audio 需要 GPU 推理链，**不要用「只有 requirements.txt」的轻量 venv 去跑本地 TTS**。
- 依赖文件都在 **`InterviewAgent/backend/`** 下：`requirements.txt`、`requirements-step-audio.txt`。

---

## 3. 第一次：安装步骤（按上表选一种后端）

**（1）后端依赖** — 进入 `InterviewAgent/backend`，在**已激活**的目标环境中：

```bash
# 场景：仅阿里云 TTS
pip install -r requirements.txt

# 场景：本地 Step-Audio（需先装好 PyTorch）
# pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu128   # 按你的 CUDA 改
pip install -r requirements-step-audio.txt
```

**（2）配置** — 编辑 `backend/.env`（可参考 `.env.example`），至少填 LLM 的 Key、地址、模型名。

**（3）TTS（可选）** — 编辑 `backend/tts_config.yaml` 里的 `provider` 及各段参数。也可用环境变量覆盖：`export TTS_PROVIDER=qwen-tts`。`backend/scripts/` 下有按厂商启动的脚本（内部会设 `TTS_PROVIDER`）。

**（4）前端** — 在 `InterviewAgent/frontend`：

```bash
npm install
```

---

## 4. 每天怎么启动

需要 **两个终端**（后端 + 前端）。下面 `~/yjm` 可改成你的项目父路径。

**默认 TTS 为本地 Step-Audio 时**：后端必须用 **带 PyTorch 的 conda 环境**（如 `stepaudio`），**不要**用 `interview-agent-venv` 直接跑 `uvicorn`（无 torch 则无声音；进程也会在启动时被拒绝）。

**终端 1 — 后端（推荐：一键脚本）**

```bash
# 自动：conda activate stepaudio → 检查 import torch → uvicorn（默认 0.0.0.0:8000）
bash ~/yjm/InterviewAgent/backend/scripts/run_backend_step_audio.sh
```

本机仅 `127.0.0.1` 时可设：`HOST=127.0.0.1 PORT=8000 bash ~/yjm/InterviewAgent/backend/scripts/run_backend_step_audio.sh`。conda 环境名不是 `stepaudio` 时：`STEPAUDIO_CONDA_ENV=你的环境名 bash ...`。

**终端 2 — 前端**

```bash
cd ~/yjm/InterviewAgent/frontend
npm run dev
# 本机打开 http://localhost:3000
```

**远程 SSH + 本机浏览器**：后端仍用上面脚本；前端用 `npx next dev -H 0.0.0.0 -p 3000`。VSCode **端口**转发 **3000** 与 **8000**。若用公网 IP 访问，需在 `backend/main.py` 配好 CORS。

**若临时改用 qwen-tts**（仅阿里云、不要本地 GPU），可用 venv：

```bash
source ~/yjm/interview-agent-venv/bin/activate
cd ~/yjm/InterviewAgent/backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

---

## 5. 页面地址

| 说明 | 地址 |
|------|------|
| 前端首页 | http://localhost:3000 |
| 面试对话 | http://localhost:3000/interview |
| 后端 API 文档 | http://localhost:8000/docs |

---

## 6. 使用流程（简述）

上传简历 → 进入面试页 → 多轮对话 → 结束 → 查看报告。

---

## 7. 无浏览器时：curl 测接口

在能访问到后端的机器上执行（示例端口 8000）：

```bash
curl -s http://localhost:8000/ | python3.11 -m json.tool
```

WebSocket 需安装 `wscat`：`wscat -c ws://localhost:8000/api/interview/chat/{session_id}`。其余上传简历、开始面试、结束、报告等接口见 http://localhost:8000/docs 。

---

## 8. 常见问题（精简）

| 现象 | 处理 |
|------|------|
| `pip` / `python` 不对 | 确认已 `source` 正确的 venv 或 `conda activate`，`which python` 指向预期环境 |
| `ModuleNotFoundError` | 未激活环境，或该环境里没执行过对应的 `pip install -r ...` |
| `npm install` 报 `node:fs` | Node 太旧，升级到 18+（推荐 20），删 `node_modules` 重装 |
| 端口被占用 | `lsof -i :8000` 找到进程后 `kill` |
| 远程 CORS | 非 localhost 访问时，把前端 Origin 加到 `main.py` 的 CORS；用端口转发访问 localhost 通常无此问题 |
| LLM 401/403 | 检查 `.env` 里 Key |
| Mac `EMFILE` / 首页异常 | `ulimit -n 10240` 后 `npm run dev`，或 `npm run dev:mac` |

**DashScope TTS 自测**：`backend` 下 `python scripts/test_tts.py`（需已配置 Key）。

---

## 9. 补充：先激活 Python 再启动后端

若用 venv：`source ~/yjm/interview-agent-venv/bin/activate`（路径按你实际放置修改）。若用本地 Step-Audio：`conda activate stepaudio` 且已 `pip install -r requirements-step-audio.txt`。具体启动命令见 **第 4 节**。
