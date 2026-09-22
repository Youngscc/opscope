# setup.sh 子操作记录

2026-09-22。本文档记录 `setup.sh` 创建/更新运行环境时执行的各个子操作，供维护者排查与扩展参考；面向用户的命令清单见 [环境配置命令](environment.md)。

## 子操作流程

`setup.sh` 按以下顺序执行，`set -euo pipefail` 保证任一步失败即终止：

### 1. 加载 `.env`
若根目录存在 `.env`，先 `set -a; source .env; set +a` 导出变量，使 `PYTHON_BIN`、`OPSCOPE_*` 等在后续步骤生效。`.env` 不入库。

### 2. 参数解析
仅接受 `-h`/`--help` 打印用法；其他参数报错退出 2。`setup.sh` 不接受配置参数，依赖来源由 `pyproject.toml` / `backend/requirements.txt` 固定。

### 3. Python 环境（二选一）
检测 `uv` 是否在 PATH：

- **uv 可用**：执行 `uv sync`。按 `pyproject.toml` 创建/同步 `.venv`，默认包含 dev 组（httpx）；幂等，重复运行只做增量同步。uv 创建的 `.venv` 不带 pip。
- **uv 不可用**：走 venv + pip 回退：
  1. **解释器选择**：若 `.venv/bin/python` 不存在，优先用 `PYTHON_BIN`；未设置时按 `python3.12` / `python3.11` / `python3.10` 顺序找首个可用候选。
  2. **版本断言**：选定解释器后断言 `sys.version_info >= (3,10)`，不满足则退出并提示设置 `PYTHON_BIN`。
  3. **创建 venv**：`<解释器> -m venv .venv`。
  4. **pip 守护**：若 `.venv` 无 pip（典型为 uv 创建但 uv 当前不在 PATH），提示"运行 uv sync 或删除 .venv 重试"并退出 1，避免直接调 pip 崩溃。
  5. **安装依赖**：`.venv/bin/python -m pip install --disable-pip-version-check -q -r backend/requirements.txt`。

### 4. 前端依赖
若 `frontend/node_modules` 缺失，执行 `npm --prefix frontend ci`（按 `package-lock.json` 精确安装）；已存在则跳过，不强制重装。

### 5. 就绪提示
输出"环境就绪：.venv 与 frontend/node_modules 可用，可运行 ./start.sh"。

## 失败处理

| 子操作 | 失败现象 | 处理 |
| --- | --- | --- |
| `uv sync` | 网络问题或版本冲突 | uv 报错退出；核对 `pyproject.toml` 与 `backend/requirements*.txt` 版本是否对齐 |
| 解释器选择 | 系统无 Python ≥ 3.10 | 断言失败退出；用 `PYTHON_BIN=/path/to/python3.11 ./setup.sh` 指定 |
| pip 守护 | `.venv` 无 pip | 提示运行 `uv sync` 或删除 `.venv` 重建 |
| `pip install` | 依赖解析失败 | 检查 `backend/requirements.txt` 与网络/源 |
| `npm ci` | lock 与 package.json 不同步 | npm 报错；重新生成 `package-lock.json` 后重试 |

## 与 start.sh 的边界

`setup.sh` 只负责环境就绪；`start.sh` 启动前检查 `.venv/bin/python` 与 `frontend/node_modules` 存在，缺失则提示运行 `./setup.sh` 并退出 1，不内联任何安装逻辑。CI 不依赖 `setup.sh`，直接用 `backend/requirements-dev.txt`（pip）安装。

## 扩展注意

- 新增 Python 依赖时，需同步 `pyproject.toml` 与 `backend/requirements*.txt` 两处并保持版本一致。
- `uv sync` 默认安装 dev 组；若需要分离生产/开发环境，调整 `pyproject.toml` 的 `[dependency-groups]` 并在 `setup.sh` 增加对应分支。
- 不要把环境配置逻辑回迁到 `start.sh`，保持脚本职责单一（见 [环境配置命令](environment.md) 的两步流程）。