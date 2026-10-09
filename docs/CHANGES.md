# OpScope 变更记录

## 2026-10-09 · 优化工作台分类交付

将本轮改动按预设数据与结果匹配（`3b39505`）、前端界面与路由（`d15978f`）、设计文档与维护记录分类提交，推送目标为既有origin/main。[优化工作台设计](optimization-workspaces.md)、[架构](../ARCHITECTURE.md)、[数据口径](../.agent/data-semantics.md)与使用说明覆盖最终实现。此前宿主记录、Profiling调研、个人设置和临时trace不纳入此次交付，原文件保留。

验证：35项Python检查、9项前端测试、Vue类型检查/生产构建通过，生成的两份离线HTML与基线一致，暂存差异格式检查通过。沿用实现阶段的浏览器验证，本轮未重复运行实际评估或部署宿主。

## 2026-10-09 · 性能优化支持 Size 选择与输入配置

[诊断页](../frontend/src/pages/OptimizationPage.vue)增加 Size 快捷选择，强化算子/硬件/尺寸选择框和蓝色主按钮；[输入弹窗](../frontend/src/components/optimization/DiagnosisSizeConfig.vue)支持逐维编辑、校验与应用/取消。[预设生成器](../opscope/offline/optimization_demo.py)扩展为12组结果并升级v5，完整维度参与精确匹配；自定义尺寸无结果时显示空状态，导出包含尺寸和输入张量。同步[设计](optimization-workspaces.md)、架构、数据口径与项目记忆，保持synthetic标记和最终结论展示。

验证：10项预设、9项前端测试、Vue类型检查/生产构建、离线生成与差异格式检查通过。浏览器检查Size/硬件/算子联动、草稿取消、Escape焦点回归、非法维度提示、自定义尺寸空状态、桌面与390px弹窗布局；实际导出Attention/910B4/S512核对63.2μs、完整维度、Q/K/V与synthetic，控制台无错误。原矩阵筛选/详情/双结果比较未重复实测。预览已更新并恢复默认桌面视口，未执行实际评估、部署宿主或提交推送。

## 2026-10-09 · 性能优化支持算子与硬件选择

[诊断页](../frontend/src/pages/OptimizationPage.vue)将算子与硬件选择并列，切换时保留另一项并精确匹配完整结果。[预设生成器](../opscope/offline/optimization_demo.py)提供MatMul/Attention与910B1/910B4四组独立示例；[流水组件](../frontend/src/components/optimization/PipelineChart.vue)按对应结果绘制重点区间。未知组合返回null、显示空状态并禁用导出；JSON升级v4，包含两项选择身份与synthetic。同步设计、架构和数据口径，不修改真实硬件规格、模型映射或后端计算。

验证：9项预设不变量、7项前端测试、Vue类型检查/生产构建、离线生成通过。浏览器检查四组切换、键盘选择、1440px/390px无溢出、MegaKernel往返及导出状态重置；实际下载Attention/910B4 JSON并核对238.8μs、重点区间、身份与synthetic。刷新后控制台无错误。缺失组合null经过单元测试，空状态未通过浏览器构造缺失数据实测；原矩阵筛选/详情/双结果比较未重复实测。预览已更新，未提交推送或部署宿主。

## 2026-10-08 · MegaKernel 按人工定义的族组织成员

[MegaKernel页](../frontend/src/pages/MegaKernelPage.vue)增加算子族选择、族内成员数量和算子/融合算子/算子组合标签；以MatMul、Attention两个预设族展示人工归属，同族不同计算用对比范围隔离。族切换同步重置结果选择，输入形状和趋势轴随族更新。[预设生成器](../opscope/offline/optimization_demo.py)与JSON导出升级v3，显式携带族和成员身份，保留synthetic与最终结果展示约定。同步[设计](optimization-workspaces.md)、架构和数据口径；不接入族编辑持久化或后端计算。

验证：7项预设不变量、5项前端测试、Vue类型检查/生产构建、离线生成通过；浏览器检查桌面及390px无溢出、键盘族切换、范围/规模/基线联动、自比1.00×和不同规模排名，实际导出核对Attention族、成员上下文、synthetic和2.17×。刷新后控制台无错误。原矩阵筛选/详情/双结果比较未重复实测；5173预览已更新，未提交推送或部署宿主。

## 2026-10-08 · 移除流水重播

移除[关键流水](../frontend/src/components/optimization/PipelineChart.vue)的重播按钮、状态和扫描动画，保留静态等待区间与片段时间提示；清理对应图标和样式，同步[交互说明](optimization-workspaces.md)。

验证：Vue类型检查/生产构建、离线生成通过；浏览器确认1440px桌面布局、MatMul/Attention切换及区间标记正常，重播按钮已移除，控制台无错误。此次为定向展示调整，未重复运行原矩阵筛选、双结果比较和JSON检查；5173预览已更新，未部署宿主或提交推送。

## 2026-10-08 · 优化界面聚焦最终结论

按用户要求，[性能优化页](../frontend/src/pages/OptimizationPage.vue)删除多方法证据卡、数量和来源选择，资源压力与[关键流水](../frontend/src/components/optimization/PipelineChart.vue)不再标注方法；页面直接显示任务耗时、瓶颈位置和优化方向。MegaKernel维持实现级比较，确认无评估方法信息。同步清理[预设生成器](../opscope/offline/optimization_demo.py)中的方法记录与失效样式，展示/导出资产升级到v2，仅包含结果层字段，保留synthetic；原性能矩阵不受影响。

验证：5项预设测试、Vue类型检查/生产构建、离线生成及差异格式检查通过。浏览器检查两页无方法信息、诊断切换、键盘流水重播、融合排名及390px窄屏无溢出；控制台无错误。实际下载Attention诊断JSON，确认只有工作负载选择与最终结果，无source/evidence字段，示例标记保留。预览已更新，宿主未部署。当前产品约定见[优化工作台](optimization-workspaces.md)。

## 2026-10-08 · 性能优化与 MegaKernel 界面预览

在 Vue 前端加入两个与性能矩阵并列的页面：[性能优化](../frontend/src/pages/OptimizationPage.vue)展示统一瓶颈、资源压力、多方法证据、局部流水和优化方向；[MegaKernel](../frontend/src/pages/MegaKernelPage.vue)展示同一功能族内的实现排名、可选基线、规模趋势与融合边界。使用简洁的图表和展开交互，预设数据和导出始终标记 synthetic；不实现后端性能计算。共享导航、独立样式与图表组件位于 frontend/src；[预设生成器](../opscope/offline/optimization_demo.py)由 build.py 调用，图宽和比值在Python生成。静态路由增加两个页面的刷新入口，原矩阵配置在导航返回后保留。

验证：5项新预设、14项构建/矩阵、1项HTTP静态路由及5项前端测试通过；Vue类型检查、生产构建、离线生成和差异格式检查通过。浏览器检查桌面与390px窄屏、筛选、缺失流水、重播、键盘、基线自比、规模排名变化和融合边界；两页JSON下载检查synthetic与上下文正确，控制台无错误。原矩阵可读取宿主目录，未运行评估。当前只更新本仓Vue源码；原单文件demo仍为矩阵，宿主zrt-sim未同步。减少动态效果仅静态样式核对。设计边界见[优化工作台](optimization-workspaces.md)。

## 静态展示页（2026-09-29）

新增单文件 [demo.html](../demo.html)，内置现有 MatMul 预设结果，无需安装或启动服务即可演示。复用[离线生成器](../opscope/offline/build.py)、共享样式与交互，固定输入并隐藏执行入口，[初始化](../evaluation-ui.js)跳过服务探测；支持筛选、详情、双结果比较和 JSON，保留合成标记与缺项原因。[使用说明](../README.md)和[架构](../ARCHITECTURE.md)同步更新。

验证：重新生成两份 HTML，14项数据/矩阵测试、4项既有评估UI测试、JS语法与静态模式无网络/不可提交定向检查通过。按用户要求未启动服务或运行评估；浏览器布局、筛选、详情、双结果和JSON交互未实测。交付仅包含本次静态展示相关改动，已有未提交调研及其他工作保留本地。

此处按**完成的修改任务**记录结果与验证，不按文件保存次数记流水。历史原型迭代见 [HISTORY.md](HISTORY.md)；长期项目事实见 [项目记忆](../.agent/MEMORY.md)。记录不等于已提交或已发布。

## 2026-09-28

### 同步 GitHub main 到集成开发分支

- 合并 OpScope main `f04aab8` 的 GitCode 同步工作流及记录；同时将 modeling fork main `635e5558` 的主线更新合入其集成分支。文档冲突保留双方独立记录，接入实现保留，个人文件和原有未提交修改不纳入。
- 验证：OpScope 97 项 Python、5 项前端、5 项同步脚本测试通过，离线重建一致；modeling 严格26项、E2E4/4、同步脚本5项通过。推理扩大回归受未启动的本机 PostgreSQL 阻断（289项 fixture 错误），全量仍有2项 MCP 导入收集错误；未把环境阻塞视为测试通过。
- 更新仅发布至 `codex/opscope-modeling-integration`；远端 main 和 GitCode 镜像目标不变，运行服务未重启。

### 分类提交共享后端与算子覆盖改动

按环境、功能、设计文档和覆盖审计组织 OpScope 提交，并将 modeling 的共享后端实现与说明分别提交。明确纳入原忽略规则漏掉的 TileSim 适配模块；用户 trace、个人设置及 modeling 原有无关修改不纳入。GitHub 集成分支为交付目标，未合入 main，不触发仅跟随 main 的 GitCode 镜像。验证沿用本轮已完成测试，并检查暂存差异及生成文件一致性；实际推送结果以 Git 远端核对为准。

### 补齐共享目录配置及算子方法适配

- modeling 新增严格符号绑定、资产工作量与共享 SFU 策略复用，补齐合法 dtype、输出、固定轴以及 TileSim 原生理论/工程适配；宿主前端未改。OpScope 的 [provider](../opscope/evaluation/modeling_provider.py)、配置表单和[来源详情](../opscope/evaluation/modeling_details.py)只传递有界参数并展示实际模式，不复制计算公式。
- [覆盖说明](shared-operator-coverage.md)记录 100 模板的 300 项 H200 审计及资产/硬件快照：Roofline 默认 93/100 成功；TileSim 默认 11/100，显式 BF16→FP16 实验 24/100。两项审计超时延长后成功，没有计为不支持；精度不会自动转换。余项按原生模型、张量合同、硬件/精度或执行错误列出原因和路径。
- 验证：97项 Python、5项前端、类型/生产构建、离线生成、JS语法通过；modeling严格26通过，扩大回归187通过/3原始基线同样失败，全量5个原有收集错误，E2E4/4。真实 HTTP RmsNorm 双方法、桌面配置/矩阵/详情/双结果/JSON预览，以及单项/对比报告接口通过。
- 边界：不代表全硬件或任意输入已支持；未补造 TileSim 缺失算法/输入，不提供虚假流水或方法回退。原8768未改，隔离8803展示更新结果；未提交/推送。

## 2026-09-24

### GitHub 主仓到 GitCode 指定分支同步

- 新增 [同步工作流](../.github/workflows/sync-to-gitcode.yml)、分支推送脚本、隔离 Git 测试与[配置说明](github-gitcode-sync.md)。OpScope 的 main 对应 YYoung_G/opscope main；同批为 modeling、UI 的 fork 准备了 main 到原 GitCode 接入分支的映射。
- 同步保留提交身份，只允许快进；不复制其他分支/标签，不覆盖独立提交。令牌仅从 Actions Secret 读取，自动触发需显式启用变量。
- 验证：5 项本地真实 Git 测试通过，覆盖创建、快进、重复运行、分叉拒绝、演练无写入及其他分支/标签保留。三个仓库的 Actions 演练和首次正式同步成功，日志核对目标 SHA 一致，自动同步变量已启用；按用户选择保留全部已有工作流。本地未提交功能改动未发布。

### 实现共享建模后端接入与轻量环境

- 新增 [HTTP provider](../opscope/evaluation/modeling_provider.py) 与来源详情适配；复用 modeling 资产目录、硬件解析、Roofline/TileSim、既有单算子任务和 worker，保留逐格结果、比较和报告。在线提交按资产 ID/hash 固定配置，严格方法不回退、不使用本地规格补缺；同名硬件按配置 ID 区分。宿主前端无本轮源码变更。
- 增加 [轻量 requirements](../backend/requirements-modeling.txt)、`setup.sh --modeling`、启动服务 URL/身份文件配置，本地引擎变为可选 extra。OpScope 取消接口将切换配置传到上游并停止后续组合。当前能力、安装与限制见[共享模式](modeling-runtime.md)，覆盖初查见[CSV](audits/2026-09-24-shared-roofline-h200.csv)。
- 验证：OpScope 90 项 Python、4 项前端、类型/生产构建、离线生成、JS/bash 语法及差异检查通过。全新无 NumPy/SciPy/Torch/TileSim 的环境真实调用 H200_Server 128² FP16 MatMul，Roofline 0.0512μs、TileSim 0.14128508391203703μs；页面配置/筛选/逐卡/详情/双结果、JSON及两个报告接口核验。真实取消上游任务终态为 cancelled。modeling 严格与包兼容14项通过，E2E4/4；联合硬件专项34/36，全量5个收集错误阻断，未宣称全部通过。
- 边界：100模板×H200 Roofline初查55成功45不支持，不是全硬件/全方法覆盖。工程流水、完整语义去重、生产登录透传和旧副本物理清理仍未完成；独立模式显式保留。未提交/推送，未重启原8768；临时8802/8803使用隔离任务库供本轮验证。

### 收紧接入计划以优先复用并保持轻量

- 更新[设计](modeling-backend-integration-design.md)、[计划](modeling-backend-integration-plan.md)、接入边界及记忆：明确直接复用、兼容扩展、必要新增的顺序；候选新接口不再作为必建项，复用现有资产、任务、权限、存储和展示实现，增加重复模块/依赖清理验收。
- 验证：核对 modeling 现有 assets 和基础单算子路由，文档链接及差异格式检查通过。仅修改计划文档，未改变接口或运行行为，未运行功能测试，未提交或推送。

### 将硬件与算子数据复用纳入接入计划

- 补充[接入设计](modeling-backend-integration-design.md)与[实施计划](modeling-backend-integration-plan.md)：明确复用 modeling 硬件加载器、算子/硬件资产及版本权限，列出数据源、只读目录接口、同名配置边界、本地快照迁移和数据更新验收；同步接入边界与项目记忆。
- 验证：静态核对现有硬件加载、算子模板、资产查询/版本及 TileSim 配置映射路径；文档相对链接与差异格式检查通过。仅扩展计划，未修改数据或执行代码，未运行功能测试，未提交或推送。

### 制定 OpScope 复用 Modeling 后端的接入计划

- 新增[接入设计](modeling-backend-integration-design.md)与[实施计划](modeling-backend-integration-plan.md)，明确宿主前端不动、两种模型在 modeling 统一执行、OpScope 通过远程 provider 接入；列出方法回退、字段来源、近似映射、依赖及缓存问题，给出分阶段文件清单和验收标准。同步边界文档、导航与项目记忆。
- 验证：对照本地源码与依赖元数据核查调用链，检查本次文档相对链接及差异格式。本轮仅形成计划，未安装依赖、修改运行代码、执行性能预测或测试套件；新接入能力尚未实现，未提交或推送。既有未提交功能修改保持原样。

### 准备 Modeling 接入试验分支与约束

- modeling 与 zrt-sim-ui 从各自当前 HEAD 创建并切换至 `codex/opscope-modeling-integration`；在[接入边界](modeling-integration-scope.md)记录基线、保持宿主前端不动、直接复用 Roofline/TileSim 后端的原则，更新文档导航与项目记忆。
- 验证：两仓库分支、HEAD、工作区状态及已跟踪差异摘要核对，既有改动保留。本次未修改运行代码，未执行运行测试；尚未实现接入，未提交或推送，OpScope 分支保持不变。

## 2026-09-23

### 统一方法顺序并预设 lookup

- [方法目录](../opscope/offline/fixtures.py) 按真机数据、MSKPP、ESL、Roofline、TileSim排序；前三项配置为lookup，保留旧内部ID。示例、在线结果、筛选、详情/报告和JSON同步命名与预设元数据；运行时未接查表数据明确返回缺源原因，不回退计算。见[方案](method-lookup-presets.md)。
- 验证：81项Python测试、3项前端测试、类型检查/构建、离线生成、JS语法及差异检查通过。HTTP实跑H200小型MatMul，前三项unsupported且耗时为空，Roofline/TileSim分别0.0512/0.14128508391203703 μs成功；桌面顺序、lookup标签、MSKPP/ESL对比、筛选及JSON检查通过。尚未实现lookup数据导入与匹配，不将示例当真实命中；未提交或推送。

### 优化字体层级与结果区域比例

- 在共享 [styles.css](../styles.css) 中强化耗时、硬件/方法名和分节标题的字号/字重层级，提升标签可读性；收紧详情顶部，将更多空间留给内容，调整单项摘要卡比例及双结果表格列宽。重新生成 [index.html](../index.html)，在线/离线共用样式；不修改计算或交互逻辑。
- 验证：Vue类型检查/生产构建、离线构建、14项构建与矩阵定向测试、差异格式检查通过；桌面检查矩阵、单项/双项详情、筛选、差异、JSON、长算子名称及离线双结果展示，无横向溢出，在线控制台无错误。8768已加载新静态产物，无需重启；未执行移动端检查，未提交或推送。

### 改为直接选择两张矩阵卡片比较

- 在线/离线常驻“加入对比”，标记 A/B、最多两项，取消/筛选/换选保持同步；页面移除评估时间选择区。浮窗新增同尺度总耗时图及按所选结果下载 HTML 报告，保留原始指标、不可比说明、零值与 synthetic 语义。主要修改 [ResultMatrix.vue](../frontend/src/components/ResultMatrix.vue)、[ResultDetails.vue](../frontend/src/components/ResultDetails.vue)、[矩阵预处理](../opscope/offline/matrix_data.py)、[报告路由](../backend/web/routes/opscope.py)与离线模板；见[设计](matrix-comparison.md)。
- 验证：80 项 Python 与 3 项前端测试、类型检查/构建、离线生成、JS 语法和差异检查通过；桌面选择/取消/第三项限制/筛选、单项/双项详情、差异筛选、JSON、离线页面和报告视觉验收通过。实跑 H100/H200 小型 MatMul Roofline 并下载所选结果报告成功。
- 经用户明确授权重启 8768 服务；历史接口保留但不再显示时间选择 UI。报告仍依赖服务内存快照，示例报告独立标明 synthetic。没有提交或推送。

### 修复 FP8/FP4 Roofline 峰值字段映射

- [`bundled_roofline.py`](../opscope/evaluation/bundled_roofline.py) 从已有 `_tops` 字段读取 FP8/FP4 峰值，其他浮点精度继续读取 `_tflops`；未修改硬件数值。增加目录公式回归测试，并更新[缺口地图](evaluation-gap-map.md)、[数据口径](../.agent/data-semantics.md)和[项目记忆](../.agent/MEMORY.md)。
- 验证：独立 worker 实跑 `infer:QuantBatchMatmulV3` 默认输入的 17 个非 TileSim 硬件入口，16 成功、`Adevice03_POD` 1 项因 `fp8_tops=0` 不支持、0 运行失败；Python 全量 79 项测试通过，差异格式检查通过。未重跑 9,500 格全量审计；910B1/B4 的整卡 Roofline 规格仍缺。

### 建立按任务记录的变更流程

- 增加 [变更记录 Skill](../agent_skills/opscope-change-record/SKILL.md)，并在 [AGENTS.md](../AGENTS.md) 与[项目级 Skill 分工](agent-workflows.md)中规定：每个完成的仓库文件修改任务留一条实际变更、验证和限制记录。既有设计文档与项目记忆继续承担各自职责。
- 验证：Skill 结构校验、文档链接和差异格式检查。此轮只改工作流文档，未更改评估计算或页面行为；未回填此前任务的流水，也未提交或推送。
