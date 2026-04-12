/**
 * 浏览器录音 → 16kHz mono s16le PCM（Base64），供后端 DashScope ASR 使用。
 * 使用 MediaRecorder(webm) + decodeAudioData，再重采样为 16kHz。
 */

const TARGET_RATE = 16000;

function resampleFloat32(
  input: Float32Array,
  inputRate: number,
  outputRate: number
): Float32Array {
  if (inputRate === outputRate) {
    return input;
  }
  const ratio = inputRate / outputRate;
  const outLen = Math.max(1, Math.floor(input.length / ratio));
  const out = new Float32Array(outLen);
  for (let i = 0; i < outLen; i++) {
    const srcIndex = i * ratio;
    const i0 = Math.floor(srcIndex);
    const i1 = Math.min(i0 + 1, input.length - 1);
    const t = srcIndex - i0;
    out[i] = input[i0] * (1 - t) + input[i1] * t;
  }
  return out;
}

function floatTo16BitPCM(float32: Float32Array): ArrayBuffer {
  const buf = new ArrayBuffer(float32.length * 2);
  const view = new DataView(buf);
  for (let i = 0; i < float32.length; i++) {
    const s = Math.max(-1, Math.min(1, float32[i]));
    view.setInt16(i * 2, s < 0 ? s * 0x8000 : s * 0x7fff, true);
  }
  return buf;
}

function pcmToBase64(pcm: ArrayBuffer): string {
  const bytes = new Uint8Array(pcm);
  let binary = "";
  for (let i = 0; i < bytes.byteLength; i++) {
    binary += String.fromCharCode(bytes[i]!);
  }
  return btoa(binary);
}

async function blobToPcm16kBase64(blob: Blob): Promise<string> {
  const arrayBuffer = await blob.arrayBuffer();
  const ctx = new AudioContext();
  let audioBuf: AudioBuffer;
  try {
    audioBuf = await ctx.decodeAudioData(arrayBuffer.slice(0));
  } finally {
    await ctx.close();
  }

  let mono: Float32Array;
  if (audioBuf.numberOfChannels === 1) {
    mono = audioBuf.getChannelData(0);
  } else {
    const l = audioBuf.getChannelData(0);
    const r = audioBuf.getChannelData(1);
    mono = new Float32Array(l.length);
    for (let i = 0; i < l.length; i++) {
      mono[i] = (l[i]! + r[i]!) * 0.5;
    }
  }

  const resampled = resampleFloat32(mono, audioBuf.sampleRate, TARGET_RATE);
  const pcm = floatTo16BitPCM(resampled);
  return pcmToBase64(pcm);
}

export type VoiceRecorderState = "idle" | "recording";

/** 单次录音：start() → stop() → Base64 PCM */
export class VoiceRecorder {
  private mediaRecorder: MediaRecorder | null = null;

  private chunks: Blob[] = [];

  private stream: MediaStream | null = null;

  private maxTimer: ReturnType<typeof setTimeout> | null = null;

  /** 最长录音时长（毫秒），默认 90s */
  maxDurationMs = 90_000;

  getState(): VoiceRecorderState {
    return this.mediaRecorder && this.mediaRecorder.state === "recording"
      ? "recording"
      : "idle";
  }

  async start(): Promise<void> {
    if (this.mediaRecorder?.state === "recording") {
      return;
    }

    this.chunks = [];
    this.stream = await navigator.mediaDevices.getUserMedia({ audio: true });

    const mime = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
      ? "audio/webm;codecs=opus"
      : "audio/webm";

    this.mediaRecorder = new MediaRecorder(this.stream, { mimeType: mime });
    this.mediaRecorder.ondataavailable = (e) => {
      if (e.data.size > 0) {
        this.chunks.push(e.data);
      }
    };

    this.mediaRecorder.start();

    if (this.maxDurationMs > 0) {
      this.maxTimer = setTimeout(() => {
        void this.stop().catch(() => undefined);
      }, this.maxDurationMs);
    }
  }

  /** 结束录音并返回 16kHz mono PCM 的 Base64 */
  async stop(): Promise<string> {
    if (this.maxTimer) {
      clearTimeout(this.maxTimer);
      this.maxTimer = null;
    }

    const mr = this.mediaRecorder;
    if (!mr || mr.state === "inactive") {
      this.cleanupTracks();
      throw new Error("当前未在录音");
    }

    return new Promise((resolve, reject) => {
      mr.onerror = () => {
        this.cleanupTracks();
        reject(new Error("录音失败"));
      };

      mr.onstop = () => {
        void (async () => {
          try {
            const blob = new Blob(this.chunks, { type: mr.mimeType || "audio/webm" });
            this.chunks = [];
            this.mediaRecorder = null;
            this.cleanupTracks();
            const b64 = await blobToPcm16kBase64(blob);
            resolve(b64);
          } catch (e) {
            this.cleanupTracks();
            reject(e instanceof Error ? e : new Error(String(e)));
          }
        })();
      };

      try {
        mr.stop();
      } catch (e) {
        this.cleanupTracks();
        reject(e instanceof Error ? e : new Error(String(e)));
      }
    });
  }

  /** 取消录音，不返回数据 */
  cancel(): void {
    if (this.maxTimer) {
      clearTimeout(this.maxTimer);
      this.maxTimer = null;
    }
    if (this.mediaRecorder && this.mediaRecorder.state !== "inactive") {
      this.mediaRecorder.onstop = null;
      try {
        this.mediaRecorder.stop();
      } catch {
        /* ignore */
      }
    }
    this.chunks = [];
    this.mediaRecorder = null;
    this.cleanupTracks();
  }

  private cleanupTracks(): void {
    if (this.stream) {
      this.stream.getTracks().forEach((t) => t.stop());
      this.stream = null;
    }
  }
}
