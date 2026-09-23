#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
mode=production
for arg in "$@"; do
  case "$arg" in
    --dev) mode=development ;;
    --port=*) export OPSCOPE_PORT="${arg#*=}" ;;
    --frontend-port=*) export OPSCOPE_FRONTEND_PORT="${arg#*=}" ;;
    -h|--help) echo './start.sh [--dev] [--port=8768] [--frontend-port=5173]
仅负责启动；环境配置请先运行 ./setup.sh（见 docs/environment.md）。'; exit 0 ;;
    *) echo "未知参数：$arg" >&2; exit 2 ;;
  esac
done
if [[ ! -x .venv/bin/python || ! -d frontend/node_modules ]]; then
  echo '环境未就绪：请先运行 ./setup.sh 安装 Python 与前端依赖。' >&2
  exit 1
fi
if [[ "$mode" == production ]]; then
  npm --prefix frontend run build
  exec .venv/bin/python -B -m backend.web
fi
backend_pid=''
frontend_pid=''
cleanup() {
  trap - EXIT INT TERM
  [[ -z "$frontend_pid" ]] || kill "$frontend_pid" 2>/dev/null || true
  [[ -z "$backend_pid" ]] || kill "$backend_pid" 2>/dev/null || true
  wait 2>/dev/null || true
}
trap cleanup EXIT INT TERM
.venv/bin/python -B -m backend.web & backend_pid=$!
(cd frontend && exec node node_modules/vite/bin/vite.js) & frontend_pid=$!
while kill -0 "$backend_pid" 2>/dev/null && kill -0 "$frontend_pid" 2>/dev/null; do sleep 1; done
exit 1
