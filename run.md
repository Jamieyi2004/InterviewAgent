# 🚀 Interview-Agent 运行指南

## 一、环境要求

| 依赖 | 最低版本 | 当前环境 |
|------|---------|---------|
| Python | **3.11+** | ✅ `/usr/bin/python3.11` |
| Node.js | **18+** | ✅ v20.20.0 |
| npm | **8+** | ✅ 10.8.2 |

> ⚠️ 系统默认 `python3` 是 3.6.8，**不能用**。必须使用 `python3.11` 或 `python3.12`。

**Mac（macOS）用户：**
- 若未安装 Python 3.11，可执行：`brew install python@3.11`，然后使用 `/opt/homebrew/opt/python@3.11/bin/python3.11` 或确保 `python3.11` 在 PATH 中。
- 创建虚拟环境时若出现 **「Unable to symlink」**，请改用：`python3.11 -m venv venv --copies`（用拷贝代替符号链接）。

---

## 二、后端启动

### 1. 创建虚拟环境 & 安装依赖

> ⚠️ **虚拟环境放在项目外面**，与 `Interview-Agent/` 同级，避免 venv 被提交到 Git 或影响项目结构。

```bash
# 在 Interview-Agent 的上级目录创建虚拟环境
cd ..   # 确保当前在 Interview-Agent 的父目录

# 用 python3.11 创建虚拟环境（Mac 若报 Unable to symlink，改用下一行）
python3.11 -m venv interview-agent-venv
# python3.11 -m venv interview-agent-venv --copies   # Mac 推荐：避免符号链接报错

# 激活虚拟环境
source interview-agent-venv/bin/activate

# 安装依赖
pip install -r Interview-Agent/backend/requirements.txt
```

目录结构如下：
```
父目录/
├── interview-agent-venv/    ← 虚拟环境（项目外面）
└── Interview-Agent/
    ├── backend/
    ├── frontend/
    └── ...
```

### 2. 确认 .env 配置

`.env` 文件已创建好，内容如下：

```env
# LLM 配置（阿里云 DashScope / Qwen）
LLM_API_KEY=sk-197815cf54c34528a9b863a882a4a6f3
LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
LLM_MODEL=qwen3.5-flash

# 数据库（默认 SQLite，无需修改）
DATABASE_URL=sqlite:///./interview_agent.db

# TTS 语音合成（可选，与 LLM 同用 DashScope Key 时可留空 DASHSCOPE_API_KEY）
# TTS_MODEL=cosyvoice-v3-flash
# TTS_VOICE=longanyang
# DASHSCOPE_API_KEY=   # 不填则使用上面的 LLM_API_KEY
```

> 如果需要更换模型或 API Key，直接编辑 `backend/.env` 即可。

**TTS 调通测试**：在 backend 目录下执行 `python scripts/test_tts.py`，成功后会在 `scripts/tts_output.mp3` 生成一段示例语音。需先 `pip install dashscope`（见 `requirements.txt`）。cosyvoice-v3.5-flash 无系统音色，需使用声音设计/复刻音色时再改 `TTS_MODEL`/`TTS_VOICE`。

### 3. 启动后端服务

```bash
# 激活项目外的虚拟环境
cd ..   # 确保当前在 Interview-Agent 的父目录
source interview-agent-venv/bin/activate

# 进入 backend 目录启动
cd Interview-Agent/backend

# 启动（开发模式，支持热重载）
uvicorn main:app --reload --port 8000
```

启动成功后会看到：
```
✅ 数据库表已初始化
INFO:     Uvicorn running on http://127.0.0.1:8000
```

### 4. 验证后端

浏览器打开 **http://localhost:8000** ，应返回：
```json
{
  "message": "🎯 AI 面试官系统 API 运行中",
  "docs": "/docs",
  "version": "0.1.0-mvp"
}
```

打开 **http://localhost:8000/docs** 可查看完整的 Swagger API 文档。

---

## 三、前端启动

**新开一个终端窗口**（后端保持运行）：

### 1. 安装依赖

```bash
cd ./frontend   # 或绝对路径，如 Mac: cd ~/Desktop/Interview-Agent/frontend

# 安装 Node 依赖（已有 node_modules 可跳过）
npm install
```

### 2. 启动前端开发服务器

```bash
npm run dev
```

启动成功后会看到：
```
▲ Next.js 14.x.x
- Local: http://localhost:3000
```

---

## 四、访问系统

| 页面 | 地址 | 说明 |
|------|------|------|
| 🏠 首页（简历上传） | http://localhost:3000 | 上传 PDF 简历，开始面试 |
| 💬 面试对话页 | http://localhost:3000/interview | 与 AI 面试官实时对话 |
| 📊 评估报告页 | http://localhost:3000/report | 面试结束后查看评估报告 |
| 📖 API 文档 | http://localhost:8000/docs | 后端 Swagger 接口文档 |

---

## 五、使用流程

```
上传简历 PDF  →  AI 解析简历  →  进入面试对话页  →  AI 逐阶段提问  →  面试结束  →  查看评估报告
```

1. 在首页点击上传简历（PDF 格式）
2. 上传成功后，页面自动跳转到面试对话页
3. AI 面试官会根据简历内容逐阶段提问（开场 → 技术 → 项目 → 总结）
4. 面试结束后，点击查看评估报告

---

## 六、curl 接口测试（服务器环境）

> 如果你在远程服务器上运行，无法打开浏览器，可以用以下 `curl` 命令测试所有接口。

### 1. 健康检查

```bash
curl -s http://localhost:8000/ | python3.11 -m json.tool
```

预期返回：
```json
{
    "message": "🎯 AI 面试官系统 API 运行中",
    "docs": "/docs",
    "version": "0.1.0-mvp"
}
```

### 2. 上传简历

```bash
curl -s -X POST http://localhost:8000/api/resume/upload \
  -F "file=@你的简历.pdf" | python3.11 -m json.tool
```

> ⚠️ 仅支持 PDF 格式，其他格式会返回 `{"detail":"仅支持 PDF 格式文件"}`

### 3. 创建面试会话

```bash
# resume_id 从上一步的返回中获取
curl -s -X POST http://localhost:8000/api/interview/start \
  -H "Content-Type: application/json" \
  -d '{"resume_id": 1, "position": "后端工程师"}' | python3.11 -m json.tool
```

### 4. WebSocket 面试对话

`curl` 不支持 WebSocket 协议，需要使用 `wscat`：

```bash
# 安装 wscat
npm install -g wscat

# 连接面试会话（session_id 从上一步获取）
wscat -c ws://localhost:8000/api/interview/chat/{session_id}

# 连接后发送消息：
> {"content": "你好，我准备好了"}
```

### 5. 结束面试

```bash
curl -s -X POST http://localhost:8000/api/interview/end/{session_id} | python3.11 -m json.tool
```

### 6. 生成面试报告

```bash
curl -s -X POST http://localhost:8000/api/report/generate/{session_id} | python3.11 -m json.tool
```

### 7. 查看面试报告

```bash
curl -s http://localhost:8000/api/report/{session_id} | python3.11 -m json.tool
```

### 8. 查看 Swagger API 文档（JSON 格式）

```bash
# 查看所有接口列表
curl -s http://localhost:8000/openapi.json | python3.11 -m json.tool | head -50
```

---

## 七、常见问题排查

### Q1: `pip install` 报错找不到模块

确保使用的是 **python3.11** 的虚拟环境：
```bash
which python   # 应该指向 venv/bin/python
python --version  # 应该显示 3.11.x
```

### Q2: 后端启动报 `ModuleNotFoundError`

忘记激活虚拟环境了：
```bash
# 在 Interview-Agent 的父目录下：
source ./interview-agent-venv/bin/activate
# 或绝对路径（Linux 服务器）：source /data/workspace/interview-agent-venv/bin/activate
```

### Q3: 前端页面空白 / 接口 404

- 确认后端正在运行（端口 8000）
- 前端通过 `next.config.js` 的 rewrite 规则将 `/api/*` 代理到后端
- 检查浏览器控制台是否有 CORS 或网络错误

### Q4: LLM 调用报错 401 / 403

API Key 过期或无效，去 [阿里云 DashScope 控制台](https://dashscope.console.aliyun.com/) 确认 Key 状态，更新到 `backend/.env`。

### Q5: WebSocket 连接失败

面试对话使用 WebSocket，确保：
- 后端 `uvicorn` 正在运行
- 浏览器访问地址是 `localhost`（非 `127.0.0.1` 和 `localhost` 混用）

### Q6: Mac 上前端报「EMFILE: too many open files」或访问首页 GET / 404

macOS 默认「打开文件数」上限较低，Next.js 文件监听会报错，进而可能导致首页 404。**同一终端**内先提高上限再启动：

```bash
cd ./frontend
ulimit -n 10240
npm run dev
```

或直接使用项目提供的脚本（已内置提高上限）：

```bash
cd ./frontend
npm run dev:mac
```

---

## 八、快速启动（一键命令汇总）

**Linux / 服务器：**

```bash
# ===== 终端 1：后端 =====
cd /data/workspace
python3.11 -m venv interview-agent-venv        # 首次运行才需要
source interview-agent-venv/bin/activate
pip install -r Interview-Agent/backend/requirements.txt  # 首次运行才需要
cd Interview-Agent/backend
uvicorn main:app --reload --port 8000

# ===== 终端 2：前端 =====
cd /data/workspace/Interview-Agent/frontend
npm install                     # 首次运行才需要
npm run dev
```

**Mac（macOS）：**

```bash
# ===== 终端 1：后端 =====
cd ~/Desktop                       # 或 Interview-Agent 所在的父目录
python3.11 -m venv interview-agent-venv --copies   # 首次运行，--copies 避免 symlink 报错
source interview-agent-venv/bin/activate
pip install -r Interview-Agent/backend/requirements.txt    # 首次运行才需要
cd Interview-Agent/backend
uvicorn main:app --reload --port 8000

# ===== 终端 2：前端 =====
cd ~/Desktop/Interview-Agent/frontend   # 或 Interview-Agent/frontend 的实际路径
npm install                        # 首次运行才需要
ulimit -n 10240                    # 避免 EMFILE / 首页 404，见常见问题 Q6
npm run dev
# 或直接：npm run dev:mac
```

打开浏览器访问 **http://localhost:3000** 即可开始使用 🎉
