#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
if [[ -f .env ]]; then set -a; source .env; set +a; fi
mode=production
args=()
for arg in "$@"; do
  case "$arg" in
    --dev) mode=development ;;
    --port=*) export OPSCOPE_PORT="${arg#*=}" ;;
    --frontend-port=*) export OPSCOPE_FRONTEND_PORT="${arg#*=}" ;;
    -h|--help) echo './start.sh [--dev] [--port=8768] [--frontend-port=5173] [backend arguments]'; exit 0 ;;
    *) args+=("$arg") ;;
  esac
done
if [[ ! -x .venv/bin/python ]]; then
  runtime_python="${PYTHON_BIN:-python3}"
  if [[ -z "${PYTHON_BIN:-}" ]] && ! "$runtime_python" -c 'import sys; sys.exit(sys.version_info < (3,10))'; then
    for candidate in python3.12 python3.11 python3.10; do
      if command -v "$candidate" >/dev/null; then runtime_python="$candidate"; break; fi
    done
  fi
  "$runtime_python" -c 'import sys; assert sys.version_info >= (3,10), "Python >= 3.10 required; set PYTHON_BIN"'
  "$runtime_python" -m venv .venv
fi
.venv/bin/python -m pip install --disable-pip-version-check -q -r backend/requirements.txt
if [[ ! -d frontend/node_modules ]]; then npm --prefix frontend ci; fi
if [[ "$mode" == production ]]; then
  npm --prefix frontend run build
  exec .venv/bin/python -B -m backend.web "${args[@]}"
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
.venv/bin/python -B -m backend.web "${args[@]}" & backend_pid=$!
(cd frontend && exec node node_modules/vite/bin/vite.js) & frontend_pid=$!
while kill -0 "$backend_pid" 2>/dev/null && kill -0 "$frontend_pid" 2>/dev/null; do sleep 1; done
exit 1
