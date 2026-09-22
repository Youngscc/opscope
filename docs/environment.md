# 环境配置命令

2026-09-22。环境配置从 `start.sh` 拆出：`./setup.sh` 负责一次性/按需配置，`./start.sh` 只负责启动。本文档集中记录 Python 与前端环境的配置命令、依赖来源和常见问题。

## 一键配置

```bash
./setup.sh
```

uv 可用时走 `uv sync`；否则创建 `.venv` 并 pip 安装；前端 `node_modules` 缺失时执行 `npm ci`。脚本可重复运行（幂等），依赖变更后再次运行即可。

## Python 环境

### 方式一：uv（推荐）

```bash
uv sync
```

- 依赖声明：根目录 `pyproject.toml`（fastapi==0.141.1、uvicorn==0.52.4，dev 组 httpx==0.28.1），与 `backend/requirements*.txt` 版本精确一致。
- 默认创建并同步 `.venv`，包含 dev 组；重复运行只做增量同步。
- uv 创建的 `.venv` 不带 pip：后续安装用 `uv pip install` 或 `uv sync`，不要直接 `.venv/bin/python -m pip`。
- `uv.lock` 由本地生成，不入库；CI 与 pip 用户以 `backend/requirements*.txt` 为准。

### 方式二：venv + pip（未安装 uv 时）

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r backend/requirements.txt
.venv/bin/python -m pip install -r backend/requirements-dev.txt   # 开发（含 httpx）
```

Python 不在默认路径时：`PYTHON_BIN=/path/to/python3.11 ./setup.sh`。

## 前端依赖

```bash
npm --prefix frontend ci     # 按 package-lock.json 精确安装
```

## 验证命令

```bash
.venv/bin/python -B -m unittest discover -s tests -p 'test_*.py' -v
npm --prefix frontend test
npm --prefix frontend run build                                # vue-tsc --noEmit && vite build
npm --prefix frontend exec vue-tsc -- --noEmit                 # 仅类型检查
node --check app.js
python3 -B build.py && git diff --exit-code -- index.html      # 离线构建一致性
```

`vue-tsc` 位于 `frontend/node_modules/.bin`，不是全局命令，必须经 npm 脚本或 `npm exec` 调用。

## 常见问题

- **`.venv` 缺少 pip**：环境由 uv 创建但 uv 不在 PATH。运行 `uv sync`，或删除 `.venv` 后重新 `./setup.sh`。
- **`./start.sh` 提示环境未就绪**：先运行 `./setup.sh`；启动本身不再安装依赖。
- CI 安装仍走 `backend/requirements-dev.txt`（pip），不依赖 uv 或 setup.sh。