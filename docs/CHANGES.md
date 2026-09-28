# OpScope 变更记录

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
