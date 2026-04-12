// 全局 TTS 播放器：单 Audio + 按 segment_index 顺序播放
//
// 后端可能按句顺序发送，但本地 Step-Audio 等若将来改为并行合成，片段到达顺序可能乱序。
// 这里用「等待连续下标」的方式，始终按 0,1,2… 顺序入播放队列。

function guessAudioMime(bytes: Uint8Array): string {
  if (bytes.length >= 12) {
    const isRiff =
      bytes[0] === 0x52 &&
      bytes[1] === 0x49 &&
      bytes[2] === 0x46 &&
      bytes[3] === 0x46;
    const isWave =
      bytes[8] === 0x57 &&
      bytes[9] === 0x41 &&
      bytes[10] === 0x56 &&
      bytes[11] === 0x45;
    if (isRiff && isWave) {
      return "audio/wav";
    }
  }
  return "audio/mpeg";
}

let audio: HTMLAudioElement | null = null;
/** 已排好序、等待播放的音频 URL（FIFO） */
let playQueue: Array<{ url: string }> = [];
let isPlaying = false;
let activeSessionId: number | null = null;
let activeRoundId: string | null = null;
/** 当前轮次下一个应从 pending 取出的 segment_index */
let nextExpectedSegmentIndex = 0;
/** 已收到但还不能播的片段（等更早的下标先到） */
let pendingByIndex: Map<number, string> = new Map();

function revokeUrl(url: string) {
  if (url.startsWith("blob:")) {
    URL.revokeObjectURL(url);
  }
}

function clearRoundBuffers() {
  for (const url of pendingByIndex.values()) {
    revokeUrl(url);
  }
  pendingByIndex.clear();
  nextExpectedSegmentIndex = 0;
  for (const item of playQueue) {
    revokeUrl(item.url);
  }
  playQueue = [];
}

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
    playQueue = [];
    return;
  }

  if (playQueue.length === 0) {
    return;
  }

  const next = playQueue.shift()!;
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

/** 把已连续的 pending 下标移入 playQueue */
function drainPendingToPlayQueue() {
  while (pendingByIndex.has(nextExpectedSegmentIndex)) {
    const url = pendingByIndex.get(nextExpectedSegmentIndex)!;
    pendingByIndex.delete(nextExpectedSegmentIndex);
    nextExpectedSegmentIndex += 1;
    playQueue.push({ url });
  }
}

export const TtsPlayer = {
  startRound(sessionId: number, roundId: string) {
    activeSessionId = sessionId;
    activeRoundId = roundId;
    clearRoundBuffers();
    if (!isPlaying) playNext();
  },

  enqueueSegment(sessionId: number, roundId: string, segmentIndex: number, base64: string) {
    if (!activeSessionId || !activeRoundId) return;
    if (sessionId !== activeSessionId || roundId !== activeRoundId) {
      return;
    }

    try {
      const binary = atob(base64);
      const bytes = new Uint8Array(binary.length);
      for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
      const blob = new Blob([bytes], { type: guessAudioMime(bytes) });
      const url = URL.createObjectURL(blob);

      const prev = pendingByIndex.get(segmentIndex);
      if (prev) revokeUrl(prev);
      pendingByIndex.set(segmentIndex, url);
      drainPendingToPlayQueue();
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
    clearRoundBuffers();
    isPlaying = false;
    activeSessionId = null;
    activeRoundId = null;
  },
};
