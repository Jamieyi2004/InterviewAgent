// 简单前端日志工具：在开发环境打印到控制台，并可选上报。

export type LogLevel = "debug" | "info" | "warn" | "error";

function log(level: LogLevel, msg: string, extra?: unknown) {
  const ts = new Date().toISOString();
  const payload = extra ? [msg, extra] : [msg];

  if (process.env.NODE_ENV !== "production") {
    // 开发环境：控制台输出
    switch (level) {
      case "debug":
        console.debug(ts, msg, extra ?? "");
        break;
      case "info":
        console.info(ts, msg, extra ?? "");
        break;
      case "warn":
        console.warn(ts, msg, extra ?? "");
        break;
      case "error":
        console.error(ts, msg, extra ?? "");
        break;
    }
  }

  // 如需将前端日志打到文件，可以在这里加一个 fetch
  // 调用后端日志上报接口，例如 POST /api/logs
}

export const feLogger = {
  debug: (msg: string, extra?: unknown) => log("debug", msg, extra),
  info: (msg: string, extra?: unknown) => log("info", msg, extra),
  warn: (msg: string, extra?: unknown) => log("warn", msg, extra),
  error: (msg: string, extra?: unknown) => log("error", msg, extra),
};