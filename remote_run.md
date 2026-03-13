# 🖥️ Interview-Agent 远程服务器运行指南

> 适用场景：通过 **VSCode Remote SSH** 连接到远程服务器，直接在服务器上运行前后端，并通过本地浏览器访问。

---

## 一、环境要求

| 依赖 | 最低版本 | 服务器当前 |
|------|---------|-----------|
| Python | **3.11+** | ✅ `/usr/bin/python3.11` |
| Node.js | **18+** | ✅ v20.20.0 |
| npm | **8+** | ✅ 10.8.2 |

> ⚠️ 系统默认 `python3` 可能是 3.6.8，**不能用**。必须使用 `python3.11` 或以上版本。

---

## 二、首次环境搭建

### 1. 创建 Python 虚拟环境 & 安装依赖

> 虚拟环境放在项目外面，与 `Interview-Agent/` 同级。

```bash
cd /data/workspace
python3.11 -m venv interview-agent-venv
source interview-agent-venv/bin/activate
pip install -r Interview-Agent/backend/requirements.txt
```

### 2. 安装前端依赖

```bash
cd /data/workspace/Interview-Agent/frontend
npm install
```

---

## 三、启动服务

需要打开 **两个终端**（VSCode 中可以拆分终端）。

### 终端 1：启动后端

```bash
cd /data/workspace
source interview-agent-venv/bin/activate
cd Interview-Agent/backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

> 💡 `--host 0.0.0.0` 让后端监听所有网卡，支持外部访问和 VSCode 端口转发。

启动成功后会看到：
```
✅ 数据库表已初始化
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### 终端 2：启动前端

```bash
cd /data/workspace/Interview-Agent/frontend
npx next dev -H 0.0.0.0 -p 3000
```

> 💡 `-H 0.0.0.0` 让 Next.js 也监听所有网卡。

启动成功后会看到：
```
▲ Next.js 14.x.x
- Local: http://localhost:3000
- Network: http://0.0.0.0:3000
```

---

## 四、访问方式

### 方式一：VSCode 端口转发（✅ 推荐）

> 无需服务器开放防火墙端口，所有流量走 SSH 加密隧道，安全又方便。

1. 在 VSCode 底部面板中，点击 **「端口 (PORTS)」** 标签页
2. 点击 **「转发端口」** 按钮（或按 `Ctrl+Shift+P` 搜索 `Forward a Port`）
3. 分别添加端口 **3000** 和 **8000**
4. 在本地浏览器中访问：

| 页面 | 地址 |
|------|------|
| 🏠 前端首页 | `http://localhost:3000` |
| 📖 后端 API 文档 | `http://localhost:8000/docs` |

### 方式二：直接通过服务器 IP 访问

> 需要服务器防火墙开放 3000 和 8000 端口。

| 页面 | 地址 |
|------|------|
| 🏠 前端首页 | `http://<服务器IP>:3000` |
| 📖 后端 API 文档 | `http://<服务器IP>:8000/docs` |

如果使用此方式，需要将服务器 IP 加入后端 CORS 白名单（`backend/main.py`）：

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://<服务器IP>:3000",  # 服务器外部访问
    ],
    ...
)
```

---

## 五、常见问题

### Q1: 端口被占用 `[Errno 98] Address already in use`

找到占用端口的进程并杀掉：

```bash
# 查看占用 8000 端口的进程
lsof -i :8000
# 或
ss -tlnp | grep 8000

# 杀掉对应的 PID
kill <PID>
```

然后重新启动服务即可。

### Q2: 前端报 `Cannot find module '../server/require-hook'`

这是 `node_modules` 损坏导致的（通常是本地 Mac 上安装的二进制依赖与 Linux 不兼容）。删除后重新安装：

```bash
cd /data/workspace/Interview-Agent/frontend
rm -rf node_modules .next
npm install
```

### Q3: 后端启动报 `ModuleNotFoundError`

忘记激活虚拟环境了：

```bash
source /data/workspace/interview-agent-venv/bin/activate
```

### Q4: CORS 跨域错误

如果通过服务器 IP（非 localhost）访问前端，浏览器请求后端时 Origin 会被 CORS 拦截。需要把服务器 IP 加入 `backend/main.py` 的 `allow_origins` 列表（见上方「方式二」说明）。

使用 VSCode 端口转发则不会有此问题，因为浏览器访问的是 `localhost`。

---

## 六、快速启动命令汇总

```bash
# ===== 终端 1：后端 =====
cd /data/workspace
source interview-agent-venv/bin/activate
cd Interview-Agent/backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# ===== 终端 2：前端 =====
cd /data/workspace/Interview-Agent/frontend
npx next dev -H 0.0.0.0 -p 3000
```

然后在 VSCode 中转发 3000 和 8000 端口，本地浏览器打开 **http://localhost:3000** 即可 🎉
