#!/usr/bin/env bash
# Mac 上提高「打开文件数」上限，避免 Next.js 报 EMFILE / Watchpack 错误
ulimit -n 10240 2>/dev/null || true
exec node_modules/.bin/next dev
