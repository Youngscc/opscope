#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
mode=dev
port=5173
for arg in "$@"; do
  case "$arg" in
    --dev) mode=dev ;;
    --preview) mode=preview ;;
    --port=*) port="${arg#*=}" ;;
    -h|--help) echo './start.sh [--dev|--preview] [--port=5173]
默认启动纯前端开发服务；--preview 构建并预览静态产物。首次先执行 ./setup.sh。'; exit 0 ;;
    *) echo "未知参数：$arg，使用 --help 查看用法。" >&2; exit 2 ;;
  esac
done
if [[ ! "$port" =~ ^[0-9]+$ ]] || ((10#$port < 1 || 10#$port > 65535)); then
  echo '端口必须为 1–65535 的整数。' >&2; exit 2
fi
if [[ ! -d frontend/node_modules ]]; then
  echo '请先执行 ./setup.sh 安装前端依赖。' >&2; exit 1
fi
if [[ "$mode" == preview ]]; then
  npm --prefix frontend run build
  exec npm --prefix frontend run preview -- --host 127.0.0.1 --port "$port" --strictPort
fi
exec npm --prefix frontend run dev -- --port "$port" --strictPort
