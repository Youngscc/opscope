#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
if [[ $# -gt 0 ]]; then
  if [[ "$1" == '-h' || "$1" == '--help' ]]; then
    echo '用法：./setup.sh — 使用 npm ci 安装前端锁定依赖；需要 Node.js 22.12+。'
    exit 0
  fi
  echo '当前为纯前端项目，安装命令不接受后端参数。见 README.md。' >&2
  exit 2
fi
node -e 'const [a,b]=process.versions.node.split(".").map(Number);if(a<22||(a===22&&b<12)){console.error("需要 Node.js 22.12+");process.exit(1)}'
exec npm --prefix frontend ci
