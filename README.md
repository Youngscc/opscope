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

- 硬件与方法筛选；同硬件比方法、同方法比硬件。
- 外层展示总时延、相对参考偏差、计算/访存、有效算力、HBM/L2、资源活动、瓶颈。
- 点击查看耗时、计算、访存、各核流水、执行依据；支持两条结果并排比较。
- 导出当前筛选的 JSON，提供预览、文本选择和下载链接。
- 一个 Roofline 方法，用“已校准 / 通用估算”标注状态，来源与参数在详情中。

固定工作负载为 MatMul，M/N/K=4096，FP16 输入、FP32 累加、FP16 输出，设备侧单 kernel 边界。界面列出六个硬件选项和四个方法，共 24 个组合，其中 17 个有示例数据。R200 型号待确认；方法选项及示例不代表工具实际兼容性认证。

## 开发与验证

Python 3.9+，仅标准库。本次使用 Python 3.9.6 验证。Node.js 只用于可选的 JS 语法检查，不是运行或构建依赖。无需 npm install 或 pip install。

```bash
python3 -B build.py
python3 -B -m unittest discover -s . -p 'test_*.py' -v
node --check app.js
```

修改 `shell.html`、`styles.css`、`app.js` 或 Python 数据文件后，运行 `build.py` 并刷新页面。不要直接修改生成的 `index.html`。生成器相对自身定位源文件，不依赖原仓库路径。

## 项目结构

| 文件 | 作用 |
| --- | --- |
| `index.html` | 可直接打开的完整离线页面，包含样式、脚本和数据 |
| `shell.html` / `styles.css` / `app.js` | 页面结构、样式和交互源文件 |
| `fixtures.py` | 固定硬件/方法、合成数值和校准元数据 |
| `execution_data.py` | 合成执行记录、局部事件、资源活动 |
| `build.py` | Python 预处理、详情生成、单文件打包 |
| `test_build.py` | 数据口径与缺失语义的八项测试 |
| `AGENTS.md` | Agent 首先读取的工作规则 |
| `.agent/MEMORY.md` | 已确认决策、验证边界和接入任务索引 |
| `ARCHITECTURE.md` | 当前数据流及实现边界 |
| `docs/HISTORY.md` | 提取前的原型迭代记录，早期数量以最新记忆为准 |
| `SHA256SUMS` | 本次交付文件校验清单，修改后将不再匹配 |

## 交给 Agent 继续开发

将本目录作为工作区打开，让 Agent 首先读取 `AGENTS.md` 和 `.agent/MEMORY.md`。它们均使用相对路径，不依赖原机器上的 Skill 或 modeling 目录。可直接使用以下提示：

> 请先阅读 AGENTS.md、.agent/MEMORY.md 和 ARCHITECTURE.md，确认当前数据是合成示例，然后根据我的需求继续开发。修改后同步更新记忆中的实现状态与验证记录。

数据口径见 [.agent/data-semantics.md](.agent/data-semantics.md)，后端接入边界和待办见 [.agent/integration.md](.agent/integration.md)。

## 已验证与限制

八项定向测试、JS 语法、原页面 PC 交互已验证；本次独立打包验证记录见 [docs/PACKAGING.md](docs/PACKAGING.md)。JSON 预览有效，原内嵌浏览器的文件下载落盘没有验收。手机不是当前设计目标。没有真实硬件性能或仿真精度验证。

本包不包含 modeling 后端、数据库、原 Git 历史、个人 Skill 或外部服务凭据。未配置 Git 远程或发布到网络；未新增开源许可证授权。可在独立目录自行初始化版本管理。
