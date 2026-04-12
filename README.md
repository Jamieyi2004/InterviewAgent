# AI 面试官 —— 华中师范大学智能模拟面试系统

基于大语言模型的智能模拟面试系统，支持简历解析、多阶段实时对话、代码考核、自动评估报告。

## 系统架构

```
┌──────────────────────────────────────────────────────────────┐
│                     前端 (Next.js 14)                         │
│                                                              │
│  ┌──────┐ ┌──────────┐ ┌────────┐ ┌─────────┐ ┌──────────┐  │
│  │ 首页  │ │ 面试对话  │ │ 报告页 │ │ 会话管理 │ │ 仪表盘   │  │
│  └──────┘ └──────────┘ └────────┘ └─────────┘ └──────────┘  │
│  ┌──────────┐                                                │
│  │ 后台管理  │   WebSocket(流式对话) / REST API               │
│  └──────────┘                                                │
├──────────────────────────────────────────────────────────────┤
│                     后端 (FastAPI)                            │
│                                                              │
│  ┌─────────────────────── API Layer ────────────────────────┐│
│  │ resume  │ interview  │ report │ enhanced │ sessions│admin ││
│  └─────────────────────────────────────────────────────────┘│
│  ┌──────────────────── Service Layer ───────────────────────┐│
│  │ InterviewAgent │ ResumeParser │ ReportGen │ TokenTracker  ││
│  └─────────────────────────────────────────────────────────┘│
│  ┌──────────────────── Agent Layer ─────────────────────────┐│
│  │ InterviewEngine │ EvaluationAgent │ SessionMemory         ││
│  │ InterviewPlanner│ InsightExtractor│ ContextCompactor      ││
│  │ PersonaLoader   │ HookSystem      │ EnhancedSafety        ││
│  └─────────────────────────────────────────────────────────┘│
│  ┌──────────────────── Skill System ────────────────────────┐│
│  │ STAR追问 │ 难度自适应 │ 代码评审 │ 知识图谱追问            ││
│  └─────────────────────────────────────────────────────────┘│
│                                                              │
│  SQLite (ORM: SQLAlchemy)  │  LLM API (Qwen / DeepSeek)     │
└──────────────────────────────────────────────────────────────┘
```

## 技术栈

| 层级 | 技术 | 说明 |
|------|------|------|
| 前端框架 | Next.js 14 + React 18 + TypeScript | App Router, SSR/SSG |
| 状态管理 | Zustand | 轻量级全局状态 |
| 样式 | Tailwind CSS | 自定义主题色系 |
| 图表 | Recharts | 仪表盘数据可视化 |
| 图标 | Lucide React | 300+ SVG 图标 |
| 代码编辑器 | CodeMirror | C++ 语法高亮 |
| 后端框架 | FastAPI | 异步支持, 自动 OpenAPI 文档 |
| ORM | SQLAlchemy | SQLite 数据库 |
| AI 框架 | LangChain | 对话记忆, Prompt 管理 |
| LLM | Qwen3.5-flash / DeepSeek | 通义千问 / DeepSeek API |
| TTS | 阿里云 / Edge-TTS | 语音合成 |

## 项目目录结构

```
InterviewAgent/
├── backend/                        # 后端 (FastAPI + Python)
│   ├── main.py                     #   应用入口, 路由注册
│   ├── config.py                   #   配置管理
│   ├── api/                        #   API 路由层
│   │   ├── interview.py            #     面试会话 + WebSocket
│   │   ├── resume.py               #     简历上传解析
│   │   ├── report.py               #     评估报告生成
│   │   ├── enhanced.py             #     增强 API (评估/Token/洞察/人设/技能)
│   │   ├── sessions.py             #     会话列表 + 详情查询
│   │   └── admin.py                #     管理后台统计
│   ├── agent/                      #   AI Agent 核心
│   │   ├── interview_engine.py     #     面试引擎 (Coordinator-Worker)
│   │   ├── interview_bot.py        #     面试对话生成
│   │   ├── evaluation_agent.py     #     实时评估 (反偏差机制)
│   │   ├── interview_planner.py    #     面试策略规划器
│   │   ├── session_memory.py       #     结构化会话记忆 (10段式)
│   │   ├── context_compactor.py    #     上下文压缩器 (9段式)
│   │   ├── insight_extractor.py    #     后台洞察提取
│   │   ├── persona_loader.py       #     面试官人设系统
│   │   ├── hooks.py                #     生命周期钩子
│   │   ├── enhanced_safety.py      #     安全过滤 (注入检测/代答检测)
│   │   ├── state_machine.py        #     面试状态机 (FSM)
│   │   ├── memory.py               #     对话记忆
│   │   ├── chains.py               #     LangChain 链
│   │   ├── prompts.py              #     Prompt 模板
│   │   └── personas/               #     人设配置 (YAML)
│   │       ├── strict.yaml         #       严格型面试官
│   │       ├── friendly.yaml       #       友好型面试官
│   │       ├── pressure.yaml       #       压力型面试官
│   │       └── mentor.yaml         #       导师型面试官
│   ├── skills/                     #   可扩展技能系统
│   │   └── base.py                 #     技能基类 + 4个内置技能
│   ├── services/                   #   业务服务层
│   │   ├── interview_agent.py      #     Agent 生命周期管理
│   │   ├── report_generator.py     #     报告生成服务
│   │   ├── resume_parser.py        #     简历 PDF 解析
│   │   ├── token_tracker.py        #     Token 消耗追踪
│   │   ├── tts_service.py          #     语音合成服务
│   │   ├── text_utils.py           #     文本工具函数
│   │   └── problem_loader.py       #     题库加载
│   ├── models/                     #   数据模型层
│   │   ├── database.py             #     数据库连接 & 会话
│   │   ├── interview.py            #     面试会话/消息/报告 ORM
│   │   ├── resume.py               #     简历 ORM
│   │   └── schemas.py              #     Pydantic 请求/响应模型
│   └── utils/                      #   工具函数
│       └── pdf_utils.py            #     PDF 解析工具
│
├── frontend/                       # 前端 (Next.js 14 + TypeScript)
│   ├── src/
│   │   ├── app/                    #   页面路由 (App Router)
│   │   │   ├── page.tsx            #     首页 (面试配置入口)
│   │   │   ├── interview/page.tsx  #     面试对话页 (WebSocket 实时)
│   │   │   ├── report/page.tsx     #     评估报告页
│   │   │   ├── sessions/page.tsx   #     会话管理列表
│   │   │   ├── sessions/[id]/      #     会话详情 (对话回放)
│   │   │   ├── dashboard/page.tsx  #     数据分析仪表盘
│   │   │   ├── admin/page.tsx      #     后台管理
│   │   │   ├── layout.tsx          #     根布局
│   │   │   └── globals.css         #     全局样式
│   │   ├── components/             #   可复用组件
│   │   │   ├── index.ts            #     组件统一导出
│   │   │   ├── ChatInput.tsx       #     消息输入框
│   │   │   ├── ChatMessage.tsx     #     消息气泡
│   │   │   ├── ChatWindow.tsx      #     消息流容器
│   │   │   ├── CodeEditor.tsx      #     代码编辑器 (CodeMirror)
│   │   │   ├── InterviewProgress.tsx #   面试进度指示器
│   │   │   ├── ResumeUploader.tsx  #     简历上传 (拖拽)
│   │   │   ├── ReportCard.tsx      #     评估报告卡片
│   │   │   ├── SidebarNav.tsx      #     侧边栏导航组件
│   │   │   ├── StatCard.tsx        #     统计卡片
│   │   │   ├── StatusBadge.tsx     #     状态标签
│   │   │   ├── Pagination.tsx      #     分页控件
│   │   │   ├── CollapsibleSection.tsx # 可折叠面板
│   │   │   ├── ConversationReplay.tsx # 对话回放
│   │   │   └── LoadingSpinner.tsx  #     加载状态
│   │   ├── lib/                    #   工具库
│   │   │   ├── api.ts              #     REST API 客户端
│   │   │   ├── websocket.ts        #     WebSocket 管理器
│   │   │   └── constants.ts        #     全局常量 (STAGE_LABELS等)
│   │   ├── store/
│   │   │   └── useInterviewStore.ts #    Zustand 全局状态
│   │   ├── logger.ts               #   前端日志工具
│   │   └── ttsPlayer.ts            #   TTS 音频播放队列
│   ├── public/logo.png             #   校徽 Logo
│   ├── package.json
│   ├── tailwind.config.ts
│   ├── tsconfig.json
│   └── next.config.js
│
├── readme.md                       # 本文件
├── REFACTOR_PROGRESS.md            # 改造进度追踪
└── .gitignore
```

## 功能页面

| 页面 | 路由 | 功能 |
|------|------|------|
| 首页 | `/` | 面试配置：上传简历、选择岗位、开始面试 |
| 面试对话 | `/interview` | WebSocket 实时对话、流式输出、代码编辑器、TTS 语音 |
| 评估报告 | `/report` | 综合评分环、5维雷达、优缺点分析、逐题回顾 |
| 会话管理 | `/sessions` | 历史面试列表、状态筛选、岗位搜索、分页 |
| 会话详情 | `/sessions/[id]` | 对话回放、评估摘要、Token 消耗、候选人洞察 |
| 数据仪表盘 | `/dashboard` | Token 分布饼图、得分趋势折线、维度雷达、洞察标签 |
| 后台管理 | `/admin` | 统计概览、人设管理、技能列表、岗位分布图 |

## API 端点

| 模块 | 端点 | 说明 |
|------|------|------|
| 简历 | `POST /api/resume/upload` | 上传解析 PDF 简历 |
| 面试 | `POST /api/interview/start` | 创建面试会话 |
| 面试 | `WS /api/interview/chat/{id}` | WebSocket 实时对话 |
| 面试 | `POST /api/interview/end/{id}` | 结束面试 |
| 报告 | `POST /api/report/generate/{id}` | 生成评估报告 |
| 报告 | `GET /api/report/{id}` | 获取报告 |
| 增强 | `GET /api/enhanced/evaluation/{id}` | 实时评估数据 |
| 增强 | `GET /api/enhanced/token-usage/{id}` | Token 消耗分析 |
| 增强 | `GET /api/enhanced/insights/{id}` | 候选人洞察 |
| 增强 | `GET /api/enhanced/personas` | 面试官人设列表 |
| 增强 | `GET /api/enhanced/skills` | 技能列表 |
| 会话 | `GET /api/sessions` | 会话列表（分页筛选） |
| 会话 | `GET /api/sessions/{id}/detail` | 会话详情 + 消息 |
| 管理 | `GET /api/admin/stats` | 系统统计概览 |

## 快速启动

### 环境要求

- Python 3.10+
- Node.js 18+
- LLM API Key（通义千问 / DeepSeek）

### 后端

```bash
cd backend
cp .env.example .env           # 编辑 .env 填入 API Key
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

访问 http://localhost:8000/docs 查看 API 文档。

### 前端

```bash
cd frontend
npm install
npm run dev
```

访问 http://localhost:3000 开始使用。

## 面试流程

```
上传简历 → 选择岗位 → 开始面试
                         ↓
               ┌─ 自我介绍 (opening)
               ├─ 算法编程 (coding)
               ├─ 基础考察 (basic_qa)
               ├─ 项目深挖 (project_deep)
               └─ 面试总结 (summary)
                         ↓
                    生成评估报告
```

## 技术亮点

1. **Coordinator-Worker 架构** — InterviewEngine 协调评估、洞察、规划等 Worker 并行处理
2. **结构化会话记忆** — 10段式模板 + Section 级 Token 预算管理
3. **9段式上下文压缩** — 分析-摘要两阶段 + 增量 Snip 精简
4. **反偏差评估机制** — 5种已知偏差的主动对抗策略 + 证据链要求
5. **面试策略规划** — 基于简历分析的决策树 + 追问路径预设
6. **生命周期钩子** — pre/post 事件、优先级排序、中断机制
7. **可扩展技能系统** — 抽象基类 + 工厂模式 + 注册发现
8. **面试官人设系统** — YAML 配置化 + 运行时切换
9. **数据可视化仪表盘** — Recharts 图表（饼图/折线/雷达/柱图）
10. **增强安全过滤** — Prompt 注入检测 + AI 代答检测

## 代码统计

| 模块 | 文件数 | 代码行数 |
|------|:------:|:-------:|
| 后端 Agent 核心 | 14 | ~4,500 |
| 后端 API + Services | 12 | ~1,800 |
| 后端 Models | 4 | ~120 |
| 前端页面 | 7 | ~2,900 |
| 前端组件 | 15 | ~1,100 |
| 前端工具库 | 5 | ~650 |
| **总计** | **~57** | **~11,000+** |
