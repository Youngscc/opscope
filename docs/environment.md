# 使用 uv 创建 OpScope 开发环境

本文档是 OpScope 环境配置的唯一入口，适用于从新克隆的仓库开始创建 Python 环境、安装前端依赖、启动服务和更新依赖。命令均在仓库根目录执行。

## 1. 环境与依赖文件

项目需要：

- Python 3.10 及以上；本项目开发和 CI 使用 Python 3.12。
- Node.js 22.12 及以上；推荐 Node.js 24。
- uv。

仓库中的依赖文件各自承担以下职责：

| 文件 | 用途 | 是否手工编辑 |
| --- | --- | --- |
| [`pyproject.toml`](../pyproject.toml) | Python 直接依赖的源声明，`uv add` 会更新它 | 通过 `uv add` 更新 |
| [`uv.lock`](../uv.lock) | Python 直接及间接依赖的完整锁定版本 | 通过 uv 更新并提交 |
| [`backend/requirements.txt`](../backend/requirements.txt) | 运行环境的完整 pip 依赖清单 | 由 `uv export` 生成 |
| [`backend/requirements-dev.txt`](../backend/requirements-dev.txt) | 开发与测试环境的完整 pip 依赖清单 | 由 `uv export` 生成 |
| [`frontend/package.json`](../frontend/package.json) | 前端直接依赖 | 使用 npm 更新 |
| [`frontend/package-lock.json`](../frontend/package-lock.json) | 前端完整锁定依赖 | 使用 npm 更新并提交 |

`pyproject.toml` 和 `uv.lock` 是 uv 用户的安装来源；两个 requirements 文件用于 CI、pip 用户和不读取 `pyproject.toml` 的工具。不要分别手工修改三套版本。

## 2. 从零创建开发环境

### 2.1 确认 uv

尚未安装时任选一种方式。macOS 使用 Homebrew：

```bash
brew install uv
```

macOS 或 Linux 使用官方安装器：

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Windows PowerShell 使用官方安装器：

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

安装命令来自 [uv 官方安装文档](https://docs.astral.sh/uv/getting-started/installation/)。重新打开终端后确认版本：

```bash
uv --version
```

### 2.2 安装项目使用的 Python

```bash
uv python install 3.12
uv python find 3.12
```

第一条命令安装 uv 管理的 Python 3.12；第二条打印实际解释器路径。仓库已经提交 `.python-version`，无需再次执行 `uv python pin`。

### 2.3 创建虚拟环境

```bash
uv venv --python 3.12 .venv
```

该命令只创建 `.venv`。删除并重建环境时执行：

```bash
rm -rf .venv
uv venv --python 3.12 .venv
```

激活环境不是必需步骤；需要在当前 shell 中直接使用 `python` 时再执行：

```bash
source .venv/bin/activate
```

### 2.4 按锁文件安装 Python 依赖

开发环境安装运行依赖和 `dev` 组：

```bash
uv sync --locked --all-groups
```

只安装服务运行所需依赖时使用：

```bash
uv sync --locked --no-dev
```

`--locked` 会在 `pyproject.toml` 与 `uv.lock` 不一致时立即报错，防止安装过程静默改写锁文件。正常开发使用 `--all-groups`。

验证 Python 环境：

```bash
.venv/bin/python --version
.venv/bin/python -c "import fastapi, uvicorn, httpx; print('Python dependencies OK')"
uv pip check --python .venv/bin/python
```

### 2.5 安装前端依赖

```bash
npm --prefix frontend ci
npm --prefix frontend run build
```

`npm ci` 严格按 `frontend/package-lock.json` 安装，适合首次创建环境和 CI。

### 2.6 可选：配置真实评估引擎

只浏览示例数据时无需创建 `.env`。需要调用本机 Roofline 或 TileSim 时执行：

```bash
cp .env.example .env
```

然后编辑 `.env` 中的解释器和引擎路径。`.env` 只保存在本机，不提交到 Git。

### 2.7 启动

生产构建模式：

```bash
./start.sh
```

开发热更新模式：

```bash
./start.sh --dev
```

默认访问地址为 <http://127.0.0.1:8768/opscope>。修改端口：

```bash
./start.sh --port=8770
./start.sh --dev --port=8769 --frontend-port=5174
```

## 3. 最短的一次性命令

仓库已包含 `pyproject.toml`、`.python-version` 和 `uv.lock`，因此日常首次配置可直接执行：

```bash
uv python install 3.12
uv venv --python 3.12 .venv
uv sync --locked --all-groups
npm --prefix frontend ci
./start.sh
```

项目也保留包装脚本，作用等价于同步 Python 依赖并安装缺失的前端依赖：

```bash
./setup.sh
./start.sh
```

## 4. 使用 requirements 文件创建环境

以下路径供 CI、pip 兼容流程或只拿到 requirements 文件的环境使用。它与上一节的 `uv sync` 是二选一的安装方式。

安装开发和测试依赖：

```bash
uv python install 3.12
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python --requirements backend/requirements-dev.txt
```

只安装后端运行依赖：

```bash
uv python install 3.12
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python --requirements backend/requirements.txt
```

也可以使用标准 pip：

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r backend/requirements-dev.txt
```

## 5. 新增或升级 Python 依赖

新增运行依赖：

```bash
uv add "package-name==版本"
```

新增开发或测试依赖：

```bash
uv add --dev "package-name==版本"
```

只升级一个依赖：

```bash
uv lock --upgrade-package package-name
```

修改依赖后，按下面的完整顺序更新环境和 requirements 文件：

```bash
uv lock
uv sync --locked --all-groups
uv export --locked --no-dev --no-hashes --output-file backend/requirements.txt
uv export --locked --all-groups --no-hashes --output-file backend/requirements-dev.txt
uv pip check --python .venv/bin/python
```

最后提交 `pyproject.toml`、`uv.lock` 和两个 requirements 文件。这样 uv、pip 与 CI 使用同一组锁定版本。

## 6. 验证项目

```bash
.venv/bin/python -B -m unittest discover -s tests -p 'test_*.py' -v
npm --prefix frontend test
npm --prefix frontend run build
node --check app.js
python3 -B build.py
git diff --check
```

只检查 uv 环境是否与锁文件一致：

```bash
uv sync --locked --all-groups --check
```

## 7. 常见问题

- `uv sync --locked` 报锁文件过期：依赖维护者执行第 5 节的更新流程；普通使用者先确认本地 `pyproject.toml` 和 `uv.lock` 来自同一个提交。
- `.venv` 使用了错误 Python：删除 `.venv`，重新执行 `uv venv --python 3.12 .venv` 和 `uv sync --locked --all-groups`。
- `.venv` 中没有 pip：这是 uv 环境的正常情况；使用 `uv sync` 或 `uv pip install --python .venv/bin/python ...`。
- `npm ci` 报 lock 不一致：先确认 `frontend/package.json` 与 `frontend/package-lock.json` 来自同一个提交。
- `./start.sh` 提示环境未就绪：先执行第 3 节的首次配置命令，或执行 `./setup.sh`。
- Roofline 或 TileSim 不可用：Web 环境与模型运行时相互隔离；检查 `.env` 中的外部解释器路径，不能把模型包直接装进 OpScope 的 `.venv` 代替配置。
