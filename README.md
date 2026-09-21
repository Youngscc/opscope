# OpScope · 算子性能观察台

项目目录名：`opscope`。OpScope 取 Operator + Scope，表示从不同方法和硬件视角观察算子性能。

用于比较同一个算子在不同硬件、不同评估方法下性能的 PC 前端原型。已从 modeling 提取，运行和开发均不依赖原仓库。

**当前所有结果都是合成示例，包括名称为“真机 Profiling”的结果；尚未连接任何评估后端、真机、校准库或仿真器。**

## 快速使用

直接用现代浏览器打开根目录 `index.html`，可离线使用，无需安装依赖。

也可以在项目根目录启动本地服务：

```bash
python3 -m http.server 8767 --bind 127.0.0.1
```

然后访问 http://127.0.0.1:8767/ 。Ctrl+C 停止服务。端口占用时更换端口；此服务仅用于本地预览。

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

Python 3.9+，仅标准库。本次使用 Python 3.9.6 验证。Node.js 用于 JS 语法及表单状态测试（未安装时 Python 测试会明确跳过这项），不是运行或构建依赖。无需 npm install 或 pip install。

```bash
python3 -B build.py
python3 -B -m unittest discover -s . -p 'test_*.py' -v
node --check app.js
node --check configuration.js
node --check catalog-ui.js
```

修改 `shell.html`、`styles.css`、JS 或 Python 数据文件后，运行 `build.py` 并刷新页面。不要直接修改生成的 `index.html`。生成器相对自身定位源文件，不依赖原仓库路径。

[GitHub Actions CI](.github/workflows/ci.yml) 在推送、PR 和手动触发时运行单元测试、JS 语法检查，并重新构建页面。如果生成结果与提交的 `index.html` 不一致，检查会失败；请本地运行 `python3 -B build.py` 后一并提交生成文件。CI 使用 Python 3.12 和 Node.js 24，不安装项目依赖或部署页面。设计见 [CI 说明](docs/ci.md)。

## 项目结构

| 文件 | 作用 |
| --- | --- |
| `index.html` | 可直接打开的完整离线页面，包含样式、脚本和数据 |
| `shell.html` / `styles.css` / `app.js` | 页面结构、样式和交互源文件 |
| `data/modeling-catalog.json` / `catalog_data.py` | 内置目录快照、示例配置、无结果模板 |
| `configuration.js` / `catalog-ui.js` | 表单验证、配置隔离、目录及张量编辑窗口 |
| `tools/snapshot_catalog.py` | 按需从 modeling 的受跟踪文件刷新目录，仅标准库 |
| `test_catalog.py` / `test_configuration.cjs` | 目录完整性、未知值、配置隔离及恢复检查 |
| `fixtures.py` | 固定硬件/方法、合成数值和校准元数据 |
| `execution_data.py` | 合成执行记录、局部事件、资源活动 |
| `build.py` | Python 预处理、详情生成、单文件打包 |
| `task_details.py` | 任务来源、输入输出、硬件快照及新增详情内容 |
| `matrix_data.py` | 统一图表尺度、详情字段分组、双结果可比性及差值预处理 |
| `test_matrix_data.py` | 图表坐标、零值/缺失、比较口径及未知字段测试 |
| `test_task_details.py` | 任务上下文、字节数和缺失语义测试 |
| `test_build.py` | 数据口径与缺失语义测试 |
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

26 项 Python 测试（其中一项运行 7 个 Node 表单状态测试）、三份 JS 语法检查通过。目录/形状与dtype/取消和恢复/硬件搜索/矩阵/浮层/双比较/JSON 已在浏览器验证，桌面1366×768及小屏375×812无页面横向溢出。设计与当前验收边界见 [矩阵设计](docs/result-matrix-design.md)；原独立打包记录见 [docs/PACKAGING.md](docs/PACKAGING.md)。JSON 预览及下载链接内容已核对，文件下载落盘未验收。用户明确仅PC桌面使用，不投入移动端支持；没有真实硬件性能或仿真精度验证。

本包不包含 modeling 后端、数据库、原 Git 历史、个人 Skill 或外部服务凭据。源码仓库已同步到 GitHub 的 Youngscc/opscope；未部署网站，未新增开源许可证授权。
