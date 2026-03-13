// 全局 TTS 播放器：单 Audio + 队列 + 会话/轮次归属

let audio: HTMLAudioElement | null = null;
let queue: Array<{ url: string; sessionId: number; roundId: string; segmentIndex: number }> = [];
let isPlaying = false;
let activeSessionId: number | null = null;
let activeRoundId: string | null = null;

function ensureAudio() {
  if (!audio) {
    audio = new Audio();
    audio.onended = () => {
      if (audio && audio.src.startsWith("blob:")) {
        URL.revokeObjectURL(audio.src);
      }
      isPlaying = false;
      playNext();
    };
    audio.onerror = () => {
      if (audio && audio.src.startsWith("blob:")) {
        URL.revokeObjectURL(audio.src);
      }
      isPlaying = false;
      playNext();
    };
  }
}

function playNext() {
  if (isPlaying) return;
  if (!activeSessionId || !activeRoundId) {
    queue = [];
    return;
  }

  const idx = queue.findIndex(
    (item) => item.sessionId === activeSessionId && item.roundId === activeRoundId
  );
  if (idx === -1) {
    // 当前轮已无待播片段
    queue = queue.filter((item) => item.sessionId !== activeSessionId || item.roundId !== activeRoundId);
    return;
  }

  const next = queue.splice(idx, 1)[0];
  ensureAudio();
  if (!audio) return;

  audio.src = next.url;
  isPlaying = true;
  audio
    .play()
    .catch(() => {
      isPlaying = false;
      playNext();
    });
}

export const TtsPlayer = {
  startRound(sessionId: number, roundId: string) {
    activeSessionId = sessionId;
    activeRoundId = roundId;
    // 丢弃其他会话/轮次的残留
    queue = queue.filter(
      (item) => item.sessionId === activeSessionId && item.roundId === activeRoundId
    );
    // 如当前在播其他轮，也不中断，播完后不会再播旧轮片段
    if (!isPlaying) playNext();
  },

  enqueueSegment(sessionId: number, roundId: string, segmentIndex: number, base64: string) {
    if (!activeSessionId || !activeRoundId) return;
    if (sessionId !== activeSessionId || roundId !== activeRoundId) {
      // 旧轮/旧会话的片段直接丢弃
      return;
    }

    try {
      const binary = atob(base64);
      const bytes = new Uint8Array(binary.length);
      for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
      const blob = new Blob([bytes], { type: "audio/mpeg" });
      const url = URL.createObjectURL(blob);
      queue.push({ url, sessionId, roundId, segmentIndex });
      if (!isPlaying) playNext();
    } catch {
      // 解码失败直接忽略该片段
    }
  },

  stopAll() {
    if (audio) {
      audio.pause();
      if (audio.src && audio.src.startsWith("blob:")) {
        URL.revokeObjectURL(audio.src);
      }
      audio = null;
    }
    queue = [];
    isPlaying = false;
    activeSessionId = null;
    activeRoundId = null;
  },
};
