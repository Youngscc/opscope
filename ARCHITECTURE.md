# 架构

## 统一展示目录

`catalog_data.operator_groups()`按名称忽略大小写/下划线归并100个内部模板为94个可见算子。MatMul、Linear、RMSNorm、SwiGLU、Embedding只有一个列表入口，不同张量契约以中性的“输入形式”保留。内部id/domain/source不变，校验与硬件档案选择继续按原契约；界面移除来源筛选、徽标及源码详情。

`Configuration.public_export()`为JSON预览和下载生成中性operator_id/template_id及hardware标识，去掉仓库路径、来源域、目录revision和档案溯源；不修改内部数据，不丢失synthetic、性能数值、执行方法和校准来源。当前结构仍是展示私有契约，未增加导入能力。

## 当前形态

主要入口已改为 Vue 3 / TypeScript / Vite / Pinia / Vue Router + FastAPI / Uvicorn。`start.sh` 构建前端并在单端口提供页面/API；开发模式由 Vite 代理API。无任务数据库依赖。Web环境与外部计算解释器隔离，原单文件离线生成链路保留。

```text
Vue页面/组件 → Pinia状态 → /api/opscope APIRouter
                              ↓
                 EvaluationRuntime → 隔离worker
                              ↓
                 结构化结果 + Python预处理图表
                              ↓
                    Vue展示 / 离线HTML快照
```

`frontend/src/pages/OpScopePage.vue` 是接入宿主的页面入口，`backend/web/routes/opscope.py` 是可挂载路由，`app.state.opscope_runtime` 注入计算运行时。生命周期由独立宿主或未来modeling宿主管理。API基址和前端部署base可配置；当前独立服务使用根base。具体迁移边界见 [框架对齐设计](docs/framework-alignment.md)。

以下为保留的离线生成链路：

```text
opscope/offline/fixtures.py → execution_data.py
              ↓                    ↓
              task_details.py → build.py → matrix_data.py
       + shell.html + styles.css + app.js
                    ↓
               index.html
                    ↓
    浏览器筛选 / 比较 / 详情 / JSON 导出
```

`build.py` 的 `build_payload()` 生成私有 `operator-ui-demo-v1` 结果包。`make_result()` 生成单组合结果、格式化值、图宽和详情 HTML。`execution_record()` 生成解析或详细执行示例。浏览器读取内嵌 `result-data` JSON，用内存 state 保存当前选择，不持久化用户操作。

## 文件职责

- frontend/src：Vue组件、API客户端与Pinia状态；取消请求/配置切换使旧批次响应失效。
- backend/web：FastAPI宿主、命名空间API、静态产物托管、生命周期和本地来源校验。
- setup.sh：环境配置入口，创建/同步独立环境（uv sync 或 venv+pip 回退）并安装前端依赖；命令见 [环境配置](docs/environment.md)。
- start.sh：校验环境就绪后构建/启动，开发模式负责子进程清理。

- opscope/offline：合成任务上下文、目录、矩阵、示例执行数据和单文件生成；根 `build.py` 只是稳定入口。
- opscope/evaluation：输入契约、结果转换、任务运行时、Roofline/TileSim worker 和流水消费。
- tests：Python 单元测试和离线 JavaScript 契约测试。
- shell.html：结构和内嵌替换占位符；styles.css：PC 布局；app.js：展示与交互。
- tests/test_build.py：数值、同源性、事件边界、缺失、校准合并等不变量。

## 数据边界

默认示例结果 synthetic=true；可选运行时预测 synthetic=false、measurement=false。方法名不等于所有来源已接通。`details` 为可信内置 fixture 生成的展示 HTML，导出时移除；它不是正式 API 契约。当前 JS 使用 innerHTML 渲染可信内置数据，未来导入外部数据前必须增加校验与安全渲染，不能直接插入外部 HTML。

当前预生成95条组合记录（6个示例硬件+11个目录型号+2个TileSim硬件，各5方法），25条有合成结果；默认显示示例的30条。方法3与方法4各有5条虚拟总耗时，目录型号仍缺失。逻辑工作量、单kernel耗时与活动时间分开表达，计算/访存/等待允许重叠。精确字段语义见 [.agent/data-semantics.md](.agent/data-semantics.md)。

## 后续边界

开发验证由 [.github/workflows/ci.yml](.github/workflows/ci.yml) 执行：单元测试、JS 语法检查、重新构建并检查 index.html 无差异。它不参与页面运行或部署，具体约定见 [CI 说明](docs/ci.md)。

不把现有内嵌 HTML 结构直接固化成公共 API。接入应先设计独立结构化结果契约及来源/版本/单位，再由后端适配器产生可展示数据；参见 [.agent/integration.md](.agent/integration.md)。

## 单算子任务详情

结果附带 task、workload、hardware_snapshot；全部由构建期生成，不代表真实任务服务。原八类详情内容保留在 details，matrix_data 将其分成五个UI页签，并预提取用于双结果逐行对齐的标量。单条和双条都进入原生dialog，共用滚动区、焦点与关闭行为。

主界面固定硬件行×方法列；JS只负责筛选、主指标选择、图表行/列聚焦、详情和导出。图表采用HTML/CSS标记，其刻度和百分比坐标由Python根据全部结果统一生成，筛选不会悄悄重定标。matrix.pairs 保存有方向的 A/B 比较说明；跨硬件又跨方法、输出/计时边界不一致或真实来源未校验时不生成比值。默认使用合成fixture契约；新增运行时以规范配置、硬件和引擎身份校验预测对比，尚不是通用实测数据校验服务。

全局 JSON 导出筛选范围，详情 JSON 导出当前一或两条结果；两者移除 details/sections/matrix 等新旧展示字段，保留原始上下文、执行记录和 synthetic。字段背景见 [详情设计](docs/task-detail.md)，当前UI见 [矩阵设计](docs/result-matrix-design.md)。

## 算子目录与配置

`tools/snapshot_catalog.py`按需读取modeling受跟踪源码中的训练OP_CATALOG、推理资产及公共硬件顶层字段，写入`data/modeling-catalog.json`。日常构建由`opscope/offline/catalog_data.py`读取本地快照；没有原仓库或YAML依赖。硬件按系统名列出，但`profiles`分别保留train/infer路径与内容摘要，不合并两域规格。旧示例硬件拥有独立id和分组。

`configuration.js`仅负责表单语法、部分维度约束及配置匹配，`catalog-ui.js`负责搜索/编辑/应用。三个JS文件由build.py内嵌；Node只用于验证。Python安全求值已知模板维度，未知项为null。用户编辑配置不做FLOPs或输出形状推导；输出、工作量、耗时保持空缺。已有真实接口不支持的额外属性不擅自添加。

应用配置时，同时更换标题、结果上下文与导出内容，清空比较和图表聚焦。只有完整匹配合成默认配置才恢复25条fixture结果；其余组合用Python预生成的空模板并绑定当前输入。配置在内存中保存，关闭/取消浮窗不提交草稿。详情和全局JSON增加configuration与catalog_revision，仍保留synthetic=true。实现计划与目录范围见 [算子目录设计](docs/operator-catalog-plan.md)。

## 可选的本地评估运行时（2026-09-22）

静态构建与示例仍不依赖外部仓库。`serve.py` 是服务兼容入口，可选连接通过启动参数指定的建模源码和Python环境。`opscope/evaluation/evaluation_contract.py`根据内置模板规范化请求并校验基础算子形状/精度；客户端不能指定代码、硬件文件路径或公式。同目录`evaluation_runtime.py`维护有界内存任务，以独立子进程调用`engine_worker.py`，避免Web系统、任务数据库及共享Hub缓存。

worker为每个组合创建独立OpNode/Roofline实例，读取单设备硬件规格，返回原始数值、规格摘要、源码/校准身份；该worker仅处理Roofline，测量/方法3/4明确不支持，不做回退。`evaluation_results.py`生成`opscope-evaluation-v1`的工作负载、任务、来源和安全转义详情，由已有matrix_data生成全批图表尺度及比较数据。预测结果synthetic=false且measurement=false；空缺为null，不沿用fixture计数器或参考误差。

TileSim worker由`tilesim_contract.py`维护显式算子/硬件支持矩阵，`tilesim_adapters.py`按算子生成输入输出、dtype、工作量和模型假设。MatMul/FA使用有流水的DSL工程路径，已验证的归一化、激活、逐元素、BMM、固定轴Gather等使用成本模型工程或理论路径；模型存在但缺少axis、perm、group_list等运行值时保持不支持。所有路径都返回actual_backend=tilesim，不回退Roofline。

`evaluation-ui.js`处理服务探测、任务提交/轮询、运行状态和整批切换；配置改变递增请求代号，旧任务不覆盖新配置。`configuration.js`仍只做表单校验，实际数值计算在worker，格式化/比较在服务。`build.render_page`同时用于构建示例和生成完整离线结果快照；快照内嵌initial_configuration并单独保存恢复示例所需的fixture和matrix，不将示例混入评估结果。

部署入口、限制见[README](README.md)，接口与方案见[本地评估设计](docs/live-evaluation-plan.md)。这是可选运行模式，不代表已将建模引擎打包到本项目；训练/推理来源仍不出现在界面中。

## 可选 TileSim 流水（2026-09-22）

`opscope/evaluation/tilesim_contract.py`固定硬件、算子、精度、形状与事件预算范围；同目录`tilesim_worker.py`在显式独立解释器中运行已审计1.0.9的EngMatmulL0。`evaluation_runtime.py`为每批创建临时目录隔离上游trace文件，单独处理TileSim失败并保留Roofline结果。服务仍仅依赖标准库，不安装第三方包。

`evaluation_results.py`保存同次结果的模型原字段和规范化事件；`tilesim_details.py`计算每核/通道区间并集、统一全程时间轴和SVG路径。`trace-ui.js`只做选核、分页及显示；由build.py内嵌。JSON剔除trace_view几何但保留全部事件的name/ts/dur/pid/tid/ph，省略上游冗长cat对象字符串。HTML快照保留展示几何。活动百分比并非算力利用率。具体能力与验证见[TileSim接入](docs/tilesim-integration-plan.md)。

## 逐组合更新（2026-09-22）

worker通过逐行JSON/flush报告组合状态，worker_stream.py在进程仍运行时消费事件；stderr隔离并保留超时终止。EvaluationRuntime预建queued组合，按稳定ID发布不可变payload与revision。查询携带since_revision，未变时不重复发送流水；前端700ms轮询更新已完成卡片/图表/详情，后续失败保留成功组合。总数按请求组合固定，finished_count包含成功/失败/不支持。HTML快照只在整批完成后开放，部分JSON保留evaluation.status。范围与验证见[逐结果更新](docs/incremental-results.md)。

## 模型覆盖补齐（2026-09-22）

`tilesim_adapters.py`区分 DSL 工程、DSL 理论和工程 API，适配 BNSD FA 的输入与逻辑工作量；保留各自实际 mode，不自动回退。GPU 映射复用已审计源映射，借用配置随结果导出并进入矩阵标记和比较限制。无事件的模型允许 trace_view=null，默认占位字段不作为采集数据展示。R200 对应已有 R200_Server Roofline 规格；源头仍缺的 910B Roofline、GPU BF16、GB200/R200 带宽/存储参数明确显示原因。见[覆盖计划及验证](docs/modeling-coverage-plan.md)。
