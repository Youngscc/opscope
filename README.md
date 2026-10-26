# OpScope · 算子性能观察台

OpScope 是面向 PC 的**纯前端性能展示与交互项目**，使用 Vue 3、TypeScript、Vite、Pinia 和 Vue Router。页面读取仓库内的预设 JSON，在浏览器内完成配置、筛选、对比和导出，无需启动后端服务。

目前所有性能结果均为合成示例，页面及导出保留 `synthetic` 标记。修改输入后，只展示精确匹配的预设结果；未预设的组合显示暂无数据。

## 三个工作台

| 页面 | 主要功能 |
| --- | --- |
| 性能评估 | 选择算子、形状和精度；按平台与方法筛选矩阵；查看总耗时或参考偏差；双向柱状图、单项详情和双结果比较 |
| 性能分析 | 选择算子、平台与输入规模；展示瓶颈结论、资源指标、执行流水和优化方向 |
| MegaKernel 优化 | 按算子族比较实现；选择硬件、维度与基线；展示排名、时间/空间开销和规模趋势；支持 JSON 导入族定义 |

默认评估数据为 MatMul 4096 × 4096 × 4096，FP16 输入、FP32 累加，五种平台 × 五种方法共25组结果。方法顺序为真机数据、MSKPP、CAModel、TileSim、Roofline；“真机数据”也是示例列名，并非已连接设备实测。

## 直接查看或交付

| 文件 | 用途 |
| --- | --- |
| [opscope-demo.html](opscope-demo.html) | 三页完整展示版，脚本、样式与数据全部内嵌，可单文件发送 |
| [opscope-ui-design.html](opscope-ui-design.html) | UI 设计交接版，可直接编辑其中的模板、CSS 和 JSON |
| [算子族 JSON 模板](data/opscope-families.example.json) | 在 MegaKernel 左侧导入，配置族名称、成员归属及类型 |

两个 HTML 均可直接用浏览器打开，不需要另外发送资源文件。设计师修改交接版后，应按模板的 `data-source` 标注迁回 Vue 源码，再重新生成文件。详见[交接说明](docs/ui-design-handoff.md)和[族导入说明](docs/family-json-import.md)。

## 本地开发

需要 **Node.js 22.12+**，推荐 Node.js 24。所有命令从仓库根目录执行：

```bash
./setup.sh                 # npm ci，安装锁定的前端依赖
./start.sh                 # 纯前端开发服务，支持热更新
```

访问终端输出的地址，默认为 <http://127.0.0.1:5173/>。可用 `./start.sh --port=5176` 指定空闲端口，Ctrl+C 停止服务。

也可直接执行：

```bash
npm --prefix frontend ci
npm --prefix frontend run dev
```

页面使用 hash 路由：`/#/`、`/#/optimization`、`/#/megakernel`。开发和默认构建均使用本地数据，不需要 Python、FastAPI、数据库、引擎安装或 API 代理。

## 构建与预览

```bash
npm --prefix frontend run build          # 静态站点 → frontend/dist/
npm --prefix frontend run preview        # 预览构建产物
npm --prefix frontend run build:demo     # 更新根目录 opscope-demo.html
npm --prefix frontend run build:design   # 更新根目录 opscope-ui-design.html
```

也可以执行 `./start.sh --preview --port=5176`，一次完成构建与预览。`frontend/dist/` 可交给静态文件服务器托管；hash 路由无需服务端路由回退规则。Vite preview 用于本地检查。

单文件构建直接消费已提交的 JSON。只有修改 Python 示例生成规则时才需要额外运行：

```bash
python3 -B build.py
npm --prefix frontend run build:demo
npm --prefix frontend run build:design
```

Python 在此承担离线数据与图表预处理，不参与页面运行。`build.py` 也会更新历史单页产物 `index.html` / `demo.html`，它们不是当前三页应用入口。

## 代码在哪里

```text
frontend/
  src/
    pages/                  三个工作台页面
    components/             配置、详情、图表、导出等组件
    stores/                 页面状态及配置选择
    data/                   预设 JSON、数据选择、算子族文件导入
    archive-theme.css       本轮设计稿样式
    reference-theme.css     共用参考主题
    optimization.css        分析与 MegaKernel 基础样式
    main.ts                 应用入口及路由
  tests/                    前端状态与数据合同测试
  build-demo.mjs            完整展示版单文件构建
  build-design.mjs          可编辑交接版单文件构建
  vite.config.ts            前端开发和构建配置
data/                       算子族模板、目录和硬件快照
opscope/offline/             可选的 Python 示例数据生成器
styles.css                  被 Vue 复用的基础样式
configuration.js            被 Vue 复用的输入配置校验
opscope-demo.html            当前三页展示产物
opscope-ui-design.html       当前 UI 设计交接产物
docs/                       使用、设计与变更文档
```

日常 UI 修改集中在 `frontend/src/`，优先修改源码再生成 HTML，避免单文件产物与源码不一致。页面数据分别位于 `workspace-demo.json`（性能评估）和 `optimization-demo.json`（性能分析与 MegaKernel）。计算量、比例和图宽由预处理层准备，前端负责选择与展示。

算子族 JSON 只改变目录和成员组织，导入在当前会话中生效，刷新恢复默认。已有成员按 ID 绑定结果，新成员显示待接入；不按名称猜测计算语义或生成性能值。

## 验证与协作

```bash
npm --prefix frontend test
npm --prefix frontend run build
npm --prefix frontend run build:demo
npm --prefix frontend run build:design
```

UI 修改还需检查桌面布局、配置应用/取消、筛选、单项详情、双结果比较和 JSON。默认 [CI](.github/workflows/ci.yml) 只安装 Node 依赖并验证前端与两种单文件构建。Python 生成规则的测试另见[历史代码与工具边界](docs/repository-layout.md)。

- [文档导航](docs/README.md)
- [当前架构与历史记录](ARCHITECTURE.md)
- [18 张设计图映射](docs/archive-design-implementation.md)
- [变更记录](docs/CHANGES.md)
- Agent 开发入口：[AGENTS.md](AGENTS.md) 与[项目记忆](.agent/MEMORY.md)

## 历史代码与可选工具

仓库保留 `backend/`、`opscope/evaluation/`、`vendor/` 和旧原生单页实现，供历史参考及示例生成链路使用；它们不属于当前默认运行路径。旧后端安装/启动脚本集中在 `tools/legacy/`，相关文档归入[历史索引](docs/legacy-index.md)。本轮未批量删除仍有引用关系的模块，详见[仓库分层说明](docs/repository-layout.md)。
