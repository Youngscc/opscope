# OpScope · 算子性能观察台

项目目录名：`opscope`。OpScope 取 Operator + Scope，表示从不同方法和硬件视角观察算子性能。

用于比较同一个算子在不同硬件、不同评估方法下性能的 PC 应用。前端 Vue 3 / TypeScript / Vite / Pinia / Vue Router，后端 FastAPI / Uvicorn，与 modeling 的技术栈对齐。保留独立离线页面。

**默认离线页面展示合成示例；通过本地评估服务运行后展示 Roofline / TileSim 模型预测。TileSim 已接入矩阵、Attention、归一化、激活、逐元素和固定轴查表等已验证算子族，具体支持取决于算子契约、硬件模型与 dtype；预测不等于真机实测，Profiling 尚未接入。**

## 快速使用

安装 Python 3.10+、Node.js 22.12+（推荐 Node.js 24），在项目根目录执行：

```bash
./setup.sh    # 首次或依赖变更后运行：配置 .venv 与前端依赖
./start.sh    # 构建并启动服务
```

访问 [OpScope](http://127.0.0.1:8768/opscope)。页面与 API 共用 8768 端口，Ctrl+C 停止。改端口用 `./start.sh --port=8770`，不会自动关闭其他服务。

[uv](https://docs.astral.sh/uv/) 已安装时 Python 环境优先按已提交的 `uv.lock` 同步；未安装 uv 自动回退 `python3 -m venv` + pip。逐条创建 `.venv`、安装 requirements、更新锁文件和验证的完整命令见 [`docs/environment.md`](docs/environment.md)。

未配置计算环境时仍可浏览示例。实际运行需将 `.env.example` 复制为 `.env`，填写已有引擎的路径，详见下文；`.env` 不入库，不自动安装模型依赖。未安装 uv、使用 venv+pip 回退时，可用 `PYTHON_BIN=/path/to/python3.12 ./setup.sh` 指定 Python。

根目录 `index.html` 仍可直接用现代浏览器离线打开，不需要安装依赖；它是独立导出入口，在线应用使用 `frontend/dist/index.html`。

## 功能

- 可搜索的统一目录，共94个不重名算子，按功能分类；逐张量编辑 shape / dtype。同名算子的不同张量契约收至“输入形式”，界面不显示来源项目及训练/推理标签。6个通信条目标注为单算子入口未提供。
- 11组硬件配置（Server / POD分开），另保留6个独立合成示例硬件。支持搜索、批量选择。
- 硬件×方法二维矩阵；默认展示六个示例硬件，支持筛选、总耗时/参考偏差切换；方法3和方法4提供虚拟耗时。
- 单元格突出总耗时、参考偏差和瓶颈；下方偏差点图/耗时条形图支持行列聚焦及点击查看详情。
- 原生浮层详情包含结果概览、计算与访存、执行过程、输入与硬件、依据与数据；支持两条结果逐项比较、仅看差异及当前详情 JSON 导出。
- 导出当前筛选的 JSON，提供预览、文本选择和下载链接。
- 一个 Roofline 方法，用“已校准 / 通用估算”标注状态，来源与参数在详情中。

默认示例为 MatMul，M/N/K=4096，FP16 输入输出、FP32 累加，设备侧单 kernel 边界，30 个默认可见组合中 25 个有合成数据。修改任何输入或执行配置后，旧结果清空为“尚未评估”；精确恢复示例后才恢复原数据。新目录型号不继承旧示例数值。目录存在不代表全部方法、精度与内核兼容性已验证。配置只在当前页面内存中保留，可导出 JSON。

## 开发与验证

开发模式提供 Vite 热更新，浏览器访问 5173，API 代理到 8768：

```bash
./start.sh --dev
# 自定义两个端口
./start.sh --dev --port=8770 --frontend-port=5174
```

验证命令（环境配置见 [`docs/environment.md`](docs/environment.md)）：

```bash
./setup.sh                                                        # 或 .venv/bin/python -m pip install -r backend/requirements-dev.txt
.venv/bin/python -B -m unittest discover -s tests -p 'test_*.py' -v
npm --prefix frontend test
npm --prefix frontend run build
python3 -B build.py
```

在线组件位于 `frontend/src`；共享样式为 `styles.css`，形状/配置契约为 `configuration.js`。Python 继续负责数值、聚合和图表预处理。修改离线源文件或共享数据后运行 `build.py`，不要直接编辑根 `index.html`。生产模式修改源代码后重新构建；后端修改后重启。

[GitHub Actions CI](.github/workflows/ci.yml) 安装声明依赖，运行 Python/前端状态测试、TypeScript 检查、Vite 构建、离线 JS 检查及 `index.html` 构建一致性检查；不部署。详见 [CI 说明](docs/ci.md)。

## 项目结构

文档按主题整理在 [`docs/README.md`](docs/README.md)，维护脚本说明见 [`tools/README.md`](tools/README.md)。

| 文件 | 作用 |
| --- | --- |
| `frontend/src` | Vue 页面、Pinia 状态、API 客户端与可复用组件 |
| `backend/web` | FastAPI 应用、可挂载 APIRouter、运行配置与生命周期 |
| `opscope/offline` | 示例数据、详情、矩阵预处理和离线单文件构建 |
| `opscope/evaluation` | 请求契约、结果转换、独立 worker 与任务运行时 |
| `tests` | Python 单元测试和离线 JavaScript 契约测试 |
| `start.sh` / `.env.example` | 单端口启动、开发模式、外部引擎路径示例 |
| `setup.sh` / `pyproject.toml` / `uv.lock` | 环境配置入口：锁定同步、venv+pip 回退与前端依赖安装 |
| `index.html` | 可直接打开的完整离线页面，包含样式、脚本和数据 |
| `shell.html` / `styles.css` / `app.js` | 页面结构、样式和交互源文件 |
| `data/modeling-catalog.json` / `opscope/offline/catalog_data.py` | 内置目录快照、示例配置、无结果模板 |
| `configuration.js` / `catalog-ui.js` | 表单验证、配置隔离、目录及张量编辑窗口 |
| `tools/snapshot_catalog.py` | 按需从 modeling 的受跟踪文件刷新目录，仅标准库 |
| `build.py` / `serve.py` | 保持稳定的离线构建和服务启动入口 |
| `AGENTS.md` | Agent 首先读取的工作规则 |
| `.agent/MEMORY.md` | 已确认决策、验证边界和接入任务索引 |
| `ARCHITECTURE.md` | 当前数据流及实现边界 |
| `docs/HISTORY.md` | 提取前的原型迭代记录，早期数量以最新记忆为准 |

## 刷新目录（可选）

日常构建无需 modeling。需要更新内置目录时，明确指定源仓库：

```bash
python3 -B tools/snapshot_catalog.py /path/to/modeling
python3 -B build.py
```

来源为受版本管理的工作区文件，保留提交号和各文件内容摘要；不读取数据库、自定义资产或私有生产覆盖。更新时需复核目录数量测试。目录与配置边界见 [设计与验证记录](docs/operator-catalog-plan.md)。

## 交给 Agent 继续开发

将本目录作为工作区打开，让 Agent 首先读取 `AGENTS.md` 和 `.agent/MEMORY.md`。它们均使用相对路径，不依赖原机器上的 Skill 或 modeling 目录。可直接使用以下提示：

> 请先阅读 AGENTS.md、.agent/MEMORY.md 和 ARCHITECTURE.md，确认当前数据是合成示例，然后根据我的需求继续开发。修改后同步更新记忆中的实现状态与验证记录。

数据口径见 [.agent/data-semantics.md](.agent/data-semantics.md)，后端接入边界和待办见 [.agent/integration.md](.agent/integration.md)。

## 已验证与限制

56 项 Python 测试、2 项前端状态测试、TypeScript 检查、Vite 和离线构建通过。FastAPI 路由在独立宿主挂载验证通过；真实 Roofline / TileSim 的端到端结果和原适配器一致。桌面验证配置校验/清空、双结果比较、流水选核/翻页和完整 JSON。仅PC使用，未做真机精度认证，尚未实际合入 modeling；集成边界见 [框架对齐说明](docs/framework-alignment.md)。

本包不包含 modeling 后端、数据库、原 Git 历史、个人 Skill 或外部服务凭据。源码仓库已同步到 GitHub 的 Youngscc/opscope；未部署网站，未新增开源许可证授权。

## 本地运行算子评估

在 `.env` 配置已有环境（以下路径需替换）：

```dotenv
OPSCOPE_ENGINE_ROOT=/path/to/modeling
OPSCOPE_ENGINE_PYTHON=/path/to/modeling/.venv/bin/python
OPSCOPE_TILESIM_PYTHON=/path/to/tilesim-runtime/.venv/bin/python
OPSCOPE_PORT=8768
```

然后运行 `./start.sh`。也可通过 `./start.sh --engine-root /path/to/modeling --engine-python /path/to/python --tilesim-python /path/to/tile/python` 传入参数。`serve.py` 保留为 FastAPI 启动兼容入口，需要先安装 Web 依赖和构建前端。

服务 API 位于 `/api/opscope`；[接口文档](http://127.0.0.1:8768/docs) 和 `/api/health` 可用于检查。计算组件继续使用各自独立解释器，不装入 Web 环境、不连接任务数据库。

- 首批 Roofline 模板：MatMul（二维）、Linear（二维）、BMM、FlashAttention（Q/K/V同形BNSD）、LayerNorm、RMSNorm、融合投影SwiGLU、Embedding、SiLU、GELU、Softmax。相同浮点输入支持 FP16/BF16/FP32，Embedding索引支持 INT32/INT64。
- 仅默认执行语义；转置、非默认布局和非默认累加精度会拒绝。默认精度/布局选项并不代表模型刻画了不同kernel实现的差异。其他输入形式和目录算子明确返回暂未适配。
- 每个硬件/方法独立运行，无自动方法回退。每完成一个组合即回传并刷新卡片，可提前查看详情和对比；顶部显示已处理进度，其余卡片保留等待/运行状态。Roofline预测与实测分开，无Profiling参考时偏差为空。方法3/4虚拟数据仅用于演示，运行后整批清除。
- `--tilesim-python` 可省略；配置后使用独立安装的 msopmodeling 1.0.9。910B1/B4 的二维 MatMul 与 BNSD FlashAttention 使用 DSL 工程模式；H200 配置的 FP16 MatMul 使用理论模式、FP16 FA 使用成本模型工程模式。借用配置显式标注；缺失精度/带宽参数不填造。范围、固定分块与验证见 [覆盖记录](docs/modeling-coverage-plan.md)。
- TileSim详情提供总耗时、最慢核通道时间、搬运路径数据量、预测L2字节命中率、核周期和可选核流水；事件明细每页40条，JSON保留全部规范化事件。图中活动时间为区间并集，空白不能直接解释为等待。
- “保存结果 HTML”下载包含本次配置、预测、详情和比较图的单文件快照，可离线查看；JSON保留 `synthetic=false`、`measurement=false` 和实际引擎/版本/配置摘要。示例仍保留 `synthetic=true`。
- 服务仅监听本机。任务保存在内存，最多同时2个、保留最近12个，每批计算超时60秒；重启会清空任务。需要留存的结果请下载HTML或JSON。

实现与边界见 [本地评估方案](docs/live-evaluation-plan.md) 和 [组件复用分析](docs/modeling-reuse-analysis.md)。此功能不执行设备实测、不验证模型精度，已接入可选TileSim解释器，未接入外部测量数据库。详细范围见 [TileSim接入](docs/tilesim-integration-plan.md)。
