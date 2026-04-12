/**
 * WebSocket 连接管理器
 *
 * 处理与后端的 WebSocket 通信，支持：
 * - 自动连接/断开
 * - 消息回调（逐 token、完成、面试结束）
 * - 发送候选人消息
 */

const WS_BASE = process.env.NEXT_PUBLIC_WS_BASE || "ws://localhost:8000";

export interface WSCallbacks {
  /** 收到逐个 token */
  onToken: (token: string) => void;
  /** 一轮回复完成（仅文本）；TTS 通过独立的 onTts 回调下发 */
  onDone: (stage: string, state: Record<string, unknown>) => void;
  /** 收到 TTS 语音片段（按句），MP3 base64 */
  onTtsSegment?: (payload: { audioBase64: string; segmentIndex: number; text: string; roundId?: string }) => void;
  /** 语音输入经服务端 ASR 后的文本（在面试官 token 流之前） */
  onAsrResult?: (text: string) => void;
  /** 面试结束 */
  onFinished: (sessionId: number) => void;
  /** 连接错误 */
  onError: (error: string) => void;
}

export class InterviewWebSocket {
  private ws: WebSocket | null = null;
  private callbacks: WSCallbacks;
  public sessionId: number;

  constructor(sessionId: number, callbacks: WSCallbacks) {
    this.sessionId = sessionId;
    this.callbacks = callbacks;
  }

  /** 建立 WebSocket 连接 */
  connect() {
    const token = typeof window !== "undefined" ? localStorage.getItem("token") : null;
    const url = `${WS_BASE}/api/interview/chat/${this.sessionId}${token ? `?token=${token}` : ""}`;
    this.ws = new WebSocket(url);

    this.ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        switch (data.type) {
          case "token":
            this.callbacks.onToken(data.content);
            break;
          case "asr_result":
            if (data.text != null && this.callbacks.onAsrResult) {
              this.callbacks.onAsrResult(String(data.text));
            }
            break;
          case "done":
            this.callbacks.onDone(data.stage, data.state);
            break;
          case "tts_segment":
            if (data.audio_base64 && this.callbacks.onTtsSegment) {
              this.callbacks.onTtsSegment({
                audioBase64: data.audio_base64,
                segmentIndex: data.segment_index,
                text: data.text,
                roundId: data.round_id,
              });
            }
            break;
          case "finished":
            this.callbacks.onFinished(data.session_id);
            break;
          case "error":
            this.callbacks.onError(data.content);
            break;
        }
      } catch {
        console.error("[WS] 消息解析失败:", event.data);
      }
    };

    this.ws.onerror = () => {
      this.callbacks.onError("WebSocket 连接异常");
    };

    this.ws.onclose = () => {
      console.log("[WS] 连接已关闭");
    };
  }

  /** 发送候选人消息 */
  send(content: string) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ content }));
    } else {
      this.callbacks.onError("WebSocket 连接未建立");
    }
  }

  /**
   * 发送语音（16kHz mono PCM s16le 的 Base64，与后端 transcribe_to_text 一致）
   */
  sendAudioPcmBase64(audioBase64: string) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(
        JSON.stringify({ audio_base64: audioBase64, audio_format: "pcm" })
      );
    } else {
      this.callbacks.onError("WebSocket 连接未建立");
    }
  }

  /** 关闭连接 */
  close() {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }
}
