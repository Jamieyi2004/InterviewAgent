# TTS 语音合成参考文档

本项目使用阿里云 DashScope 的语音合成服务，支持两种模型方案。

---

## 方案一：CosyVoice（当前使用）

**推荐模型**: `cosyvoice-v3.5-flash`

### 快速示例（单向流式）

```python
import os
import dashscope
from dashscope.audio.tts_v2 import *

dashscope.api_key = os.environ.get('DASHSCOPE_API_KEY')

class Callback(ResultCallback):
    def on_open(self):
        self.file = open("output.mp3", "wb")

    def on_data(self, data: bytes) -> None:
        self.file.write(data)

    def on_complete(self):
        print("合成完成")

    def on_error(self, message: str):
        print(f"异常：{message}")

    def on_close(self):
        self.file.close()

# 每次调用 call 前需重新初始化 SpeechSynthesizer
synthesizer = SpeechSynthesizer(
    model="cosyvoice-v3.5-flash",
    voice="longanyang",      # 音色
    callback=Callback(),
)
synthesizer.call("今天天气怎么样？")
```

### 核心参数

| 参数 | 类型 | 必须 | 说明 |
|------|------|:----:|------|
| `model` | str | 是 | 模型名称，如 `cosyvoice-v3.5-flash` |
| `voice` | str | 是 | 音色 ID，系统音色或复刻音色 |
| `format` | enum | 否 | 音频格式，默认 mp3/22.05kHz。支持 wav/mp3/pcm/opus |
| `volume` | int | 否 | 音量 0-100，默认 50 |
| `speech_rate` | float | 否 | 语速 0.5-2.0，默认 1.0 |
| `pitch_rate` | float | 否 | 音高 0.5-2.0，默认 1.0 |
| `instruction` | str | 否 | 控制方言/情感/角色（≤100字符，仅 v3.5/v3-flash 复刻音色） |
| `language_hints` | list | 否 | 目标语言，如 `["zh"]`（仅取第一个值） |

### 三种调用方式

| 方式 | 方法 | 适用场景 |
|------|------|----------|
| 非流式 | `call(text)` 不传 callback | 短文本，阻塞返回完整音频 |
| 单向流式 | `call(text)` 传 callback | 短文本，回调接收音频分片 |
| 双向流式 | `streaming_call(text)` × N + `streaming_complete()` | 长文本实时合成 |

**文本限制**: 单次 ≤ 20000 字符（汉字算 2 字符），双向流式累计 ≤ 20 万字符。

### 关键回调方法

| 方法 | 触发时机 |
|------|----------|
| `on_open()` | WebSocket 连接建立 |
| `on_data(data: bytes)` | 收到音频数据分片 |
| `on_complete()` | 全部合成完成 |
| `on_error(message)` | 发生异常 |
| `on_close()` | 连接关闭 |

### 常见问题

- **首包延迟**: 复用连接 ~500ms，首次连接 ~1500-2000ms
- **音频无法播放**: 检查 format 参数与文件后缀是否一致
- **流式播放卡顿**: 回调中避免阻塞逻辑，音频数据写入 buffer 后由独立线程处理
- **合成语音缺尾**: 双向流式必须调用 `streaming_complete()`
- **SSL 证书错误**: `pip install ca-certificates` 或手动设置 `SSL_CERT_FILE`
- **WebSocket 报错**: `pip uninstall websocket-client websocket && pip install websocket-client`

---

## 方案二：Qwen3-TTS（备选）

**模型**: `qwen3-tts-flash`（指令控制版: `qwen3-tts-instruct-flash`）

### 快速示例

```python
import os
import dashscope

dashscope.base_http_api_url = 'https://dashscope.aliyuncs.com/api/v1'

response = dashscope.MultiModalConversation.call(
    model="qwen3-tts-flash",
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    text="今天天气怎么样？",
    voice="Cherry",
    stream=True,  # 流式输出 Base64 音频
)
for chunk in response:
    print(chunk)
```

### 核心参数

| 参数 | 类型 | 必须 | 说明 |
|------|------|:----:|------|
| `model` | str | 是 | `qwen3-tts-flash` 或 `qwen3-tts-instruct-flash` |
| `text` | str | 是 | 待合成文本（≤512 Token） |
| `voice` | str | 是 | 音色，如 `Cherry` |
| `language_type` | str | 否 | 语种，默认 `Auto`。可选: Chinese/English/Japanese 等 |
| `instructions` | str | 否 | 指令控制（仅 instruct 模型，≤1600 Token） |
| `optimize_instructions` | bool | 否 | 是否优化指令以提升自然度 |
| `stream` | bool | 否 | 是否流式输出 Base64 音频，默认 false |

### 返回结构

```json
{
  "status_code": 200,
  "request_id": "xxx",
  "output": {
    "finish_reason": "stop",
    "audio": {
      "url": "https://...",    // 非流式: 完整音频 URL（24h 有效）
      "data": "...",           // 流式: Base64 音频片段
      "id": "audio_xxx"
    }
  },
  "usage": {
    "characters": 195          // qwen3-tts-flash 按字符计费
  }
}
```

---

## 两种方案对比

| 特性 | CosyVoice | Qwen3-TTS |
|------|-----------|-----------|
| 协议 | WebSocket | HTTP/SSE |
| 流式方式 | 回调接收二进制音频 | SSE 返回 Base64 |
| 文本上限 | 20000 字符 | 512 Token |
| 音色定制 | 声音复刻/设计 | 系统音色 |
| 情感控制 | instruction 参数 | instructions 参数（instruct 模型） |
| 适用场景 | 长文本实时合成 | 短句快速合成 |

**本项目当前使用 CosyVoice 方案**，通过 WebSocket 双向流式实现面试对话的实时语音合成。
