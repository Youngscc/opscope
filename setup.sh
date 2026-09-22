#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
if [[ -f .env ]]; then set -a; source .env; set +a; fi
for arg in "$@"; do
  case "$arg" in
    -h|--help) echo './setup.sh [--help]
配置运行环境（首次或依赖变更后运行）：
- Python：uv 可用时走 uv sync，否则创建 .venv 并 pip 安装 backend/requirements.txt
- 前端：frontend/node_modules 缺失时执行 npm ci
详见 docs/environment.md。'; exit 0 ;;
    *) echo "未知参数：$arg（setup.sh 不接受参数）" >&2; exit 2 ;;
  esac
done
if command -v uv >/dev/null 2>&1; then
  uv sync
else
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
  if ! .venv/bin/python -m pip --version >/dev/null 2>&1; then
    echo '.venv 缺少 pip：该环境由 uv 创建但 uv 不在 PATH。请运行 uv sync，或删除 .venv 后重试。' >&2
    exit 1
  fi
  .venv/bin/python -m pip install --disable-pip-version-check -q -r backend/requirements.txt
fi
if [[ ! -d frontend/node_modules ]]; then npm --prefix frontend ci; fi
echo '环境就绪：.venv 与 frontend/node_modules 可用，可运行 ./start.sh。'