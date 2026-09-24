# 项目记忆

## GitHub 到 GitCode 分支同步（2026-09-24）

本项目 GitHub Youngscc/opscope 的 main 为主，GitCode YYoung_G/opscope main 为副本；单向快进同步保留 SHA，不强推，不同步额外分支/标签。工作流需 GITCODE_TOKEN，自动运行需 GITCODE_SYNC_ENABLED=true；可手动 dry-run。5项隔离 Git 测试通过，三个仓库 Actions 演练和首次正式同步成功，目标 SHA 一致，自动同步已启用；用户选择保留全部原有工作流。本地工作区与远程配置未调整。详见[配置说明](../docs/github-gitcode-sync.md)。

## 字体层级与排版细化（2026-09-23，已验证）

共享 `styles.css` 细化在线/离线桌面层级：辅助文字12px、正文14px、分节标题18px、主标题24–26px、矩阵关键数值28–30px；标题700、标签/数值600，继续用系统字体与等宽数字，不引入在线字体依赖。硬件/方法轴加粗，单位次级化，工作负载说明与状态同排；详情头部/标签区压缩，摘要主卡与次卡宽比由2:1调整为1.6:1，双结果指标名列22%，数值两列等宽。修改已有规则并保留现有交互与数据语义。

Vue类型检查与构建、离线生成、14项构建/矩阵定向测试和差异检查通过。桌面浏览器检查矩阵、单项/双项详情、差异筛选、JSON、筛选取消选择、长算子目录名称及离线双结果布局；页面无横向溢出，在线控制台未见错误。原8768服务直接读取新静态产物，未重启服务。未做移动端或实际设备精度验证。


## 矩阵内直接比较（2026-09-23，已实现并验证）

用户要求直接在二维表格选择两个结果，已移除在线页面的评估时间选择区，保留历史后端接口兼容。在线/离线每张有结果卡片常驻“加入对比”，标记 A/B；矩阵上方展示选择、取消/清空与“对比所选”，筛选隐藏项自动取消，换选详情与矩阵同步。原卡片主体仍打开单项详情。浮窗新增 Python 预处理的同尺度总耗时图，沿用分类指标、差异筛选、不可比原因与 JSON。在线浮窗可下载所选两项的独立 HTML 报告，支持示例以及同批运行中已完成的结果；未知任务不回退示例。详见[设计](../docs/matrix-comparison.md)。

验证：80 项 Python 测试、3 项前端测试、类型检查与构建、离线生成、三份 JS 语法与差异格式检查通过；1280px 桌面验收直接选卡、A/B、第三项禁选、取消换选、筛选清理、单项/双项浮窗、分类/差异和 JSON；离线直接选择与图表、独立报告视觉检查通过，控制台未见错误。临时服务实际运行 128×128 FP16 MatMul，H100/H200 Roofline 分别为 0.07336119402985075/0.0512 μs，按结果 ID 获取报告成功。用户明确授权后已重启 8768，新版页面已加载；旧内存历史随重启清空，正在查看的旧任务另备份于临时目录。离线报告下载入口未新增，仍通过在线服务生成。


## FP8 Roofline 硬件字段修复（2026-09-23，已实现并复验）

`bundled_roofline.peak()` 的 FP8/FP4 读取改用现有 `_tops` 字段，其他浮点精度继续使用 `_tflops`，未改硬件数值。独立 worker 对 `infer:QuantBatchMatmulV3` 默认输入的 17 个非 TileSim 入口复验：16 成功、`Adevice03_POD` 1 项仍因 `fp8_tops=0` 不支持、0 运行失败；910B1/B4 整卡 Roofline 规格仍缺。回归测试锁定 H200 的 `fp8_tops=1979` 与 POD 零值语义；详见[缺口地图](../docs/evaluation-gap-map.md)。旧全量审计 CSV 是修复前快照，未重新生成。

## 按任务变更记录（2026-09-23，已建立）

新增 [变更记录 Skill](../agent_skills/opscope-change-record/SKILL.md) 和 [变更记录](../docs/CHANGES.md)。今后每个完成的仓库文件修改任务写一条实际结果、主要文件、验证和限制；只读工作与中间保存不记。重大变更的设计/计划、长期事实项目记忆、Git 提交说明仍分别维护。首次只记录新流程自身，未回填无法核实的早期任务，也不自动提交/推送。

## 当前评估缺口索引（2026-09-23，静态审计核对）

将同日 9,500 默认组合审计按缺输入、Roofline 规格/公式/单元、TileSim 硬件参数/适配、未接方法拆开，列出项目持久化位置、wheel 安装副本和同类可比数据，见[缺口地图](../docs/evaluation-gap-map.md)。该轮未修改模拟算法；当时发现 `infer:QuantBatchMatmulV3` 的 17 个 Roofline FP8 拒绝里，16 个是字段不匹配，后来已修复并增量复验，结果见本页首节。TileSim 配置随已打包 wheel 保存，`.venv` 是安装副本，不应作为长期改动位置。

## 独立 HTML 对比与事件报告（2026-09-23，已实现并验证）

参考 modeling 的独立 HTML 报告组织方式，在本项目新增两次评估对比报告和单项结果详细报告。对比报告复用在线历史对比的配对、可比性、变化率及统一图宽，逐组合并排呈现全部结构化指标和补充说明；单项报告包含任务身份、预测细项、核/通道活动时间轴、完整模拟事件（含类型、开始、时长）与原始预测字段。只有上游真实输出 `execution.events` 才显示事件；无流水明确说明缺失。两类报告都无外部资源，可下载后离线阅读，文本转义；接口仅对运行时保留的终态任务开放。设计与口径见[独立 HTML 报告](../docs/html-reports.md)。

78 项 Python 测试、3 项前端测试、Vue 类型检查与生产构建、离线构建、JS 语法和差异格式检查通过。实际 TileSim 910B1 MatMul 128×128 FP16 生成 2.996023742971288 μs 和 15 个事件，独立报告包含这 15 条事件。浏览器工具策略禁止打开本地 `file://` 报告，故报告的桌面视觉效果未完成浏览器验收；其 HTML 内容、下载接口及内联 JS 语法已检查。报告仍受内存历史限制，服务重启或任务淘汰后不能重新下载。

## 两次评估时间对比（2026-09-23，已实现）

在线界面新增两次评估时间选择、相同硬件×方法的总耗时同尺度成对条形图、方向计数和逐项并排详情；原始结果可展开。后端仅列出内存中最近12个终态任务，并按配置、硬件规格与引擎身份决定能否计算变化率；缺失和零值保持原语义。离线HTML继续保留单批比较。架构和边界见[设计](../docs/time-comparison.md)。

已通过74项Python测试、3项前端测试、Vue类型检查与生产构建、离线构建、JS语法和差异检查。在临时8795本地服务用两次H100 Roofline实跑验证时间选择、刷新后保留、同尺度图表、逐项详情与JSON展开；浏览器控制台无错误。未做持久化，服务重启后记录消失。


## 项目管理 Skill 补充（2026-09-23，已实现）

在三个领域 Skill 之外，按用户追问补充 [改动规划](../agent_skills/opscope-change-planning/SKILL.md) 与 [Git 交付](../agent_skills/opscope-git-delivery/SKILL.md)。前者只在跨模块、公共契约或性能口径变化时使用，单点低风险改动继续简化；后者只在用户要求 commit/push/PR 时使用，按实际差异包含相关未跟踪文件、排除临时和个人文件，遵循本仓库 GitHub 工作流，不套用 modeling 的 GitCode 发布模板。两者不会因写入计划而自行授权远程写入，也不要求重复确认已获授权的动作。[Skill 设计与分工](../docs/agent-workflows.md)和 `AGENTS.md` 已更新。

新增两个 Skill 已通过 `quick_validate.py`；本轮仅更新文档和工作指引，未更改计算代码或执行 Git 发布。

## 项目级 Skill 适配（2026-09-23，已实现）

按用户要求，将原 modeling 流程中适合独立 OpScope 的部分改写为仓库内三个 Skill：[算子接入](../agent_skills/opscope-operator-onboarding/SKILL.md)、[评估结果核验](../agent_skills/opscope-evaluation-review/SKILL.md)、[硬件配置](../agent_skills/opscope-hardware-profile/SKILL.md)。`AGENTS.md` 按任务触发选择，并补充性能公式/硬件身份/结果口径变动时维护当前能力说明与不变量测试。Skill 不要求原 modeling、真机、数据库或个人环境；不引入其模型图、offload、校准桶及 GitCode 发布流程。设计与适用边界见[项目级 Skill 设计](../docs/agent-workflows.md)。

三个 Skill 已用 skill-creator 的 `quick_validate.py` 校验通过，仓库内相对链接及差异格式已检查。本轮只更新工作流与文档，没有修改计算代码或运行性能测试；先前未提交功能改动保持原样。

## 旧外部引擎配置清理（2026-09-23，已实现并验证）

当前独立服务只用仓库 `.venv` 和内置 Roofline/TileSim。删除仅含旧外部路径与默认端口的本机 `.env`、过时 `.env.example`，移除启动脚本的 `.env` 加载、服务设置与 CLI 的三个外部引擎覆盖项；Vite 不再主动读取根目录 `.env`。保留端口参数、`setup.sh` 无 uv 回退所需的 `PYTHON_BIN` 与宿主集成用 `VITE_OPSCOPE_API_BASE`/`VITE_OPSCOPE_BASE` 命令环境变量。底层 `EvaluationRuntime` 构造参数仍供宿主注入和隔离测试。使用说明、架构和[清理记录](../docs/environment-cleanup.md)已同步。

68 项 Python 测试、3 项前端测试、类型检查与生产构建、shell 语法及差异检查通过。正常 `./start.sh --port=8794` 启动后 HTTP 能力报告 Roofline/TileSim 均可用；128×128 MatMul 的 H200 Roofline 0.0512μs、910B1 TileSim 2.996023742971288μs，临时服务已关闭。自定义 Vite base/API 地址构建产物验证后恢复默认构建。没有改动原 modeling 仓库、依赖锁或已有未提交的其他功能修改。

## 算子/方法缺口适配（2026-09-23，已实现并复验）

在首次全目录审计后，新增本地82个推理算子资产及符号默认值快照、受限目录公式Roofline（`catalog-analytic`，明确区别于完整Kepler）、算子axis/perm属性及在线/离线编辑、7个默认TileSim模板和2个需手填axis的模板、GB200/R200缺带宽项的前置拦截。macOS Apple Silicon的`setup.sh`选Python3.11；SciPy加载失败时从`uv.lock`按SHA256装同版本macOS12 ARM64 wheel。本项目`.venv`实际可运行TileSim成本模型，无需原modeling运行环境。

最终用本项目`.venv`遍历100模板×19硬件入口×5方法=9,500组合，实际执行1,118次、执行失败0：Roofline833成功（49模板，比基线多629组合/37模板），TileSim285成功（34默认模板；比首次本机多222，比工作环境对照多76/7模板）。Cumsum/GatherV2默认缺axis保持blocked_input；显式填axis=2/0后910B1各实跑成功，分别8.620018/134.468667μs。页面端实测Cumsum在910B1/910B4逐卡显示8.620/13.221μs、详情显示工程模型假设。新适配器对错误rank/轴张量形状前置拒绝；67项Python测试、3项前端状态测试、Vue构建、离线生成、JS语法和差异格式检查通过；桌面浏览器验证配置、筛选（25/40→20/35）、逐卡显示、详情、双结果比较（+12.1%）、JSON预览2条/synthetic=true，控制台无错误；临时服务已关闭。

当时本机`.env`仍包含旧外部引擎路径，因此这轮适配复验显式清除环境覆盖，以本项目`.venv`直接启动FastAPI并通过HTTP提交Cumsum：能力报告Roofline/TileSim就绪，H200 Roofline目录公式0.1365375μs、910B1 TileSim工程模型8.620018μs，910B1 Roofline正确保持不支持。临时端口已关闭。旧`.env`随后按用户要求删除，见上方清理记录。

仍缺910B1/B4整卡Roofline峰值/HBM、GPU BF16和GB200/R200部分TileSim参数、18个模板的默认维度及Cumsum/GatherV2轴值、通信模型、Profiling与方法3/4执行器。目录公式与原Kepler纯单算子路径在37模板×2硬件的74组中，输出shape/dtype一致72组、FLOPs一致60组；不能宣称两种模式数值完全等价。详见[适配实施与证据](../docs/operator-adaptation-plan.md)及[原始审计结果](../docs/audits/2026-09-23-adapted/summary.json)。下方首次审计的环境故障与未适配结论为历史基线，已由本节更新。

## 全目录实跑审计（2026-09-23，已验证）

用户要求逐算子×方法实跑并区分来源缺失和适配问题。新增 tools/audit_evaluations.py、audit_supplemental.py、audit_upstream_roofline.py；结果在 [审计报告](../docs/operator-method-audit.md) 与 docs/audits/2026-09-23-operator-method/。100 输入模板（94组）×19 硬件入口×5方法共9,500组合；默认门槛允许413次执行：Roofline204全成功；TileSim209中63成功、146因项目Python3.12.14的SciPy1.15.3 _spropack Mach-O动态库加载失败。已有Python3.11.16/SciPy1.15.3对照209全成功；TileSim源码hash一致、63个共有成功时延完全相等。当前环境未修复，不能把对照成功当作当前已可用。能力探测未覆盖成本模型工程API是待修项。

已登记28个TileSim模板，27个默认输入完整且至少一个硬件可执行；FlashAttentionScore补head_dim=128后仍超事件上限，缩至[1,8,512,128]后两910B均成功。显式FP16等70个补充检查47成功、10引擎失败、13前置阻塞：新发现GB200/R200的BMM/TransposeBatchMatMul缺GM→L1带宽，Cast/Sigmoid/SwiGlu缺L0C→L2带宽，前置检查漏拦截。其他GPU BF16、910B Roofline规格仍缺。默认目录18个非通信输入模板缺维度；通信6个排除。大量已有TileSim模型仍缺axis/perm/group_list/量化/布局契约适配，不能笼统归为无模型。

只读原modeling纯计算对照：64个可提交infer模板×2硬件，61个各返回结果、3个各失败；QuantLightningIndexer缺输出sparse_count、SparseIndexSelect缺index_topk，MoeGatingTopK二维输入在layers/moe.py:104按三维解包异常。61个返回结果中含START/END和零FLOPs简化结果，不等于完整性能模型。原仓库不是OpScope运行依赖。24项定向测试、产物唯一性/数值/缺失语义/来源hash检查、脚本语法与离线生成通过。本轮未改生产逻辑/锁文件/原仓库源码，未提交推送；保留之前未提交的算子选择UI修改。

## 算子选择入口强调（2026-09-23，已验证）

用户要求算子选择更显眼。在线页和离线模板把选择入口合入左侧当前算子标题：整个名称区域可点击，浅蓝底、主题色边框、28px 算子名、60px 高度，并显示“选择算子”与下拉箭头；形状摘要紧邻，右侧保留评估操作。复用原配置弹窗，离线 workload-name 标识移至按钮内 span，避免配置更新覆盖按钮结构。

已通过 12 项目录/矩阵定向测试、3 项前端测试、Vue 类型检查与构建、JS 语法、离线生成和差异格式检查。1280px 桌面浏览器验证 MatMul 与 ColumnParallelLinearQuant 名称、无横向溢出、鼠标/Enter 打开配置、应用及恢复示例、硬件筛选、单条详情、双结果比较与 JSON（2 条结果、synthetic=true）；控制台无错误。8768 预览服务已启动。未新增依赖，未提交或推送。

## 内置评估引擎（2026-09-22，已实现）

项目已把运行所需的轻量 Roofline 后端和 TileSim 发行包收进自身目录。执行 `./setup.sh` 后，`./start.sh` 只使用本仓库、仓库 `.venv` 和内置数据，不再要求存在外部 modeling 仓库、其 Python 环境或 `.env` 路径。早期外部路径覆盖入口已在2026-09-23删除。

Roofline 内置实现覆盖当前 11 个基础算子，并带 11 套由原运行时解析后固化的硬件规格；其默认配置在 Adevice03 Server 与 H200 Server 上逐字段对照上游参考，共 22 个结果、176 个数值/状态字段完全一致。TileSim 以 `vendor/msopmodeling/msopmodeling-1.0.9-py3-none-any.whl` 和 Mulan PSL v2 许可证随仓库保存，首次配置仍需从包索引安装 NumPy、SciPy、Pandas 等依赖。默认运行时已实测同时探测 Roofline 与 TileSim 成功，128×128 FP16 MatMul 在 910B1 上得到 2.996023742971288µs。

最终验证通过 60 项 Python 测试、3 项前端测试、Vue 类型检查/生产构建、JS 语法、锁文件只读同步、离线页面构建和差异格式检查。另在显式清空全部外部引擎环境变量后，从本仓库启动 8783 服务：健康接口正常，能力接口同时报告 Roofline/TileSim 可用，小型 Roofline 与 TileSim 请求均成功完成；验证服务已关闭。

当前只内置 OpScope 实际使用的最小 Roofline 逻辑和数据，不复制 modeling 的任务数据库、Profiling 服务或其他应用代码。910B1/B4 仍没有可验证的完整 Roofline 峰值/带宽规格，因此只用于 TileSim；未知型号和不支持组合继续明确返回缺失原因。设计、来源、校验和更新步骤见[内置评估引擎](../docs/bundled-engines.md)。

## 环境配置与启动分离（2026-09-22，已验证）

本节记录早期拆分过程；当前环境入口与依赖口径以“当前状态”的最新条目和 `docs/environment.md` 为准。

用户要求把环境配置从 start.sh 拆出做独立命令文档。新增 setup.sh 作为环境配置唯一入口（uv sync / venv+pip 回退 + npm ci + 无参数守卫），start.sh 精简为只校验环境就绪后启动——缺 .venv 或 node_modules 时提示"请先运行 ./setup.sh"并退出 1，不再内联安装逻辑。新增 docs/environment.md 集中记录 uv / venv+pip 两条路径、前端依赖、验证命令（含 vue-tsc 正确调用方式）与常见问题。随后应要求新增 docs/setup-steps.md 单独记录 setup.sh 内部子操作（加载 .env、参数解析、Python 二选一分支、前端依赖、就绪提示）、失败处理与扩展注意，供维护者排查参考；docs/README.md 索引同步登记。README 快速使用改为两步（setup → start）并引用文档，ARCHITECTURE.md 文件职责同步更新。实测：setup.sh 幂等成功，start.sh 拆分后 /api/health 200（8782），环境缺失提示正确，index.html 构建一致。分类提交：脚本拆分 189913f、文档随下一条提交，推送后远程与本地一致。

## uv 环境配置（2026-09-22，已验证）

本节记录最初接入 uv 时的历史实现；后续已改为提交 `uv.lock`、锁定同步并由锁文件导出 requirements。

用户要求加入 uv 配置运行环境的命令和依赖。新增根目录 pyproject.toml：virtual 项目（无 build-system，uv 不安装 opscope 自身），dependencies 为 fastapi==0.141.1、uvicorn==0.52.4，dev 组 httpx==0.28.1，与 backend/requirements*.txt 精确一致；uv.lock 由本地生成并加入 .gitignore 不入库，CI 与 pip 路径仍以 requirements 为准。start.sh 检测到 uv 时优先 `uv sync`，否则回退 venv+pip；并新增守护：uv 创建的 .venv 无 pip 时给出明确提示而非报错崩溃。README 快速使用、验证命令、项目结构表同步更新。uv 0.12.15 实测：uv sync 幂等复用现有 .venv 且保留 pip，59 项测试通过，start.sh 冒烟 /api/health 200（8779/8780 端口），index.html 构建一致。分类提交：工具链 d48de61、文档随下一条提交，推送后远程与本地一致。

## 分类提交（2026-09-22，第二批）

用户要求将未提交修改分类提交。本轮分四类：功能代码主体（逐结果增量+覆盖扩展+包重组，79dc0be）、CI与测试路径配套（cd44636）、文档与项目记忆（c6ab705）、补交三篇功能设计文档（eca77c4，逐结果/覆盖计划/TileSim算子覆盖，后经amend并入MEMORY修正为e4fe710）。提交前重新通过59项Python测试、3项前端测试、5份JS语法、Vue构建、离线构建确定性与产物一致性检查。opscope/ 新包与根目录删除在同一提交中由git识别为重命名。.arts/、.vscode/、trace.json 保持untracked不提交。用户随后授权push，71b8938..e4fe710已推送，远程main与本地HEAD一致。

## 最新：TileSim算子覆盖扩展（2026-09-22）

TileSim不再只开放MatMul/FlashAttention。按当前目录契约登记26个模板，覆盖MatMul/Linear/BMM、稠密FA、LayerNorm/RMSNorm/AddRmsNorm、SiLU/GELU/Softmax、Mul/Add/Sigmoid/SwiGLU激活、固定axis=0 Embedding、Cast、DynamicQuant、MoeGatingTopK和TransposeBatchMatMul；DSL工程、成本模型工程和成本模型理论路径分别标记，不回退Roofline。融合SwiGLU MLP、未知axis/perm/group_list、量化缺完整输入和复合边界仍明确不支持。

默认可解析的25个模板已在910B1与910B4逐项实跑成功；FlashAttentionScore默认head_dim为空且规模超过流水上限，缩小到[1,8,512,128]后两卡分别13.977425/18.839385μs并各输出1328事件。LayerNorm默认分别54.266292/72.481067μs，RMSNorm20.136326/24.294752μs。LayerNorm补零beta、LayerNormV4补单位gamma/零beta、GemmaRmsNorm借普通RMSNorm模型等假设进入详情。59项Python测试、3项前端状态测试、JS语法、Vue构建、离线构建和diff检查通过；尚未真机精度认证。详见[TileSim算子覆盖](../docs/tilesim-operator-coverage.md)。

## 最新：按现有模型补齐覆盖（2026-09-22）

已增加 R200_Server Roofline、910B1/B4 的 FA DSL 工程适配及现有 TileSim 硬件映射。9382→910B4、H100/B300→H200 明确标记借用；H200配置FP16 MatMul理论/FA工程API也已跑通。三种模式分别保留mode，流水可为空，占位与缺失不冒充实测。当前页面BF16 FA [2,32,512,128]已有9个预测：新增R200 Roofline3.935μs和910B1/910B4/借用910B4的TileSim71.165/109.768/109.768μs。8768服务已更新，页面配置保留并重新评估。

仍不能从现有来源补齐：910B1/B4完整Roofline规格、GPU TileSim BF16参数、GB200/R200的L0C→L2带宽与FA工程存储参数。已改为明确原因。56项Python测试及前端检查通过，实跑batch/head对照、MatMul回归、浏览器FA详情/流水/JSON预览。无真机精度验证、未提交/推送，外部仓库未改。详见[覆盖计划与实跑记录](../docs/modeling-coverage-plan.md)。下文较早的仅MatMul/不允许借用说明为历史范围。

## 最新：按组合逐卡展示（2026-09-22）

按用户要求取消整批结束后统一显示。Roofline/TileSim worker通过逐行JSON输出组合状态；运行时增量发布带revision的部分payload，Vue和离线客户端700ms轮询更新。等待/运行/不支持/失败分别显示，已完成预测即时可查看、比较、导出；后续失败保留前面成功结果，修改配置继续隔离旧响应。HTML快照等整批完成；中途JSON保留批次状态与进度。细节见[逐结果方案](../docs/incremental-results.md)。

本机8768服务已重启。浏览器确认16/40时4个Roofline预测可见、TileSim仍等待；32/40时部分JSON状态running且H100为277.935μs；最终7个预测且TileSim数值未变。52项Python测试（含4项离线交互检查）、2项前端状态测试、类型检查、Vue/离线构建及差异格式通过；新增屏障/子进程输出/超时/版本轮询覆盖。未提交或推送本轮修改。

## 分类提交（2026-09-22）

用户要求将累计改动分类提交。本轮按“组件分析与输出审计”“实际评估与流水展示”“Vue/FastAPI框架与启动CI”“使用说明与项目记忆”四类整理本地提交。前三类提交为36d942a、00fb20a、1b38a92；本条记录随第四类文档提交。提交前重新通过47项Python测试、2项前端测试、Vue类型检查/构建、离线产物一致性与diff格式检查；未修改业务行为，未重复浏览器验收，沿用上一轮结果。本轮仅本地提交，未推送。

## 最新：框架对齐与端口启动（2026-09-22，已实现）

按用户要求，在线入口改为Vue 3 + TypeScript + Vite + Pinia + Vue Router，后端FastAPI/Uvicorn，与本地modeling及其配套zrt-sim-ui一致。`./start.sh`一条命令构建并在127.0.0.1:8768提供页面/API；`--dev`使用Vite5173代理后端，端口可改。独立Web虚拟环境，不混入模拟器依赖；无外部引擎时可浏览演示。实际本机.env已配置原先两个解释器，忽略不入库。

Vue页面位于frontend/src，FastAPI可挂载路由位于backend/web/routes/opscope.py，前缀/api/opscope；宿主注入app.state.opscope_runtime。保留原生离线生成和serve.py兼容启动入口。Python仍负责性能数值/聚合/图表，前端管理状态与展示；取消或改配置会丢弃旧响应。未改modeling/zrt-sim-ui业务代码，尚未真正合入宿主。

47项Python测试、2项前端状态测试、Vue类型检查/构建与离线构建通过。浏览器验证实际7/40组合、4096² FP16 TileSim 390.891/627.736μs、双比较+60.6%、各53,888事件JSON、选核分页、K校验及128² BF16重新运行；控制台无错误。开发代理与退出端口清理、宿主APIRouter注入、真实HTML快照200/attachment已验证。未推送、未部署、未做真机精度认证。详见[框架设计与验收](../docs/framework-alignment.md)。下文“默认纯静态/无框架”的记录是历史状态。


## 最新：TileSim结果与流水接入（2026-09-22，已实现）

此前“尚未接UI”为历史。新增可选--tilesim-python，连接外部1.0.9独立环境的DSL EngMatmulL0；仅MatMul二维FP16/BF16、128倍数维度、80,000事件上限，固定分块128/256/512/128。硬件新增独立910B1/910B4，不借用9382/GPU。每批临时目录隔离上游输出，失败保留Roofline。服务8768已带两解释器启动。

总耗时、最慢核通道分项、预测L2字节命中率、路径搬运字节、周期、输入/硬件/分块证据和可选核流水接入浮窗。Python预处理区间并集与SVG，前端只选择/分页。JSON完整保留6键规范化事件，剔除冗长cat和展示几何；大型流水使用紧凑JSON+Blob。无等待原因、整体compute/memory分类、bound或实测偏差，不虚构。

43项测试、五份JS语法与构建通过；实跑4096平方FP16两个硬件分别390.8914486042133/627.7357897236953µs，各53,888事件，末端与时延一致；128平方BF16分别2.996023742971288/4.441526814082755µs。桌面默认7/40结果、详情、切核/40条分页、双流水和+60.6%比较、单条及双条完整JSON核对；最终筛选6/35→7/40、切核焦点、控制台无错误。下载落盘未单独验收。HTML快照17MB接口成功，离线浏览器与真机精度未验收。未推送。详见[接入设计与验证](../docs/tilesim-integration-plan.md)。

## TileSim 输出严格审计（2026-09-22）

按安装的1.0.9源码及三路径MatMul实际返回核对：公开结果14顶层字段（5固定/默认零占位），底层OperatorResult17字段，trace每事件7键。理论5.904144µs、工程API10.936681µs、DSL8.559026µs/1736事件不能混拼。发现工程compute_workload.CUBE实际操作数/µs；mem_volume的L1_cache累计元素、其他cache项字节，不能统一Bytes；规则DSL时间分项属最慢核不是全芯片累计；tiling零/空和AIV标签需校验，append_result未正确写回trace。详见[字段审计](../docs/tilesim-output-inventory.md)及随附实际JSON/源码摘要。未改业务代码或接UI，非真机精度认证。

## TileSim 流水能力核查（2026-09-22，已实跑）

更正此前只有汇总的表述：CLI eng路径仅返回汇总，但安装包另有DSL EngineeringOperator规则流水路径。直接EngMatmulL0在910B1/24AIC生成1736个事件、4通道、8.559025912870776µs；ts/dur/pid/tid齐全，原始trace与脚本保存在外部tilesim-runtime。是Tile级模拟，不是真机指令trace；与CLI 10.936681µs不同实现，禁止混用。多候选时内部trace.json会被最后候选覆盖，应取最优OperatorResult.trace。详见[安装记录](../docs/tilesim-installation.md)。尚未接网页，其他算子未验证。

## TileSim 独立安装（2026-09-22，已验证）

用户授权安装。官方 msopmodeling 1.0.9 已安装在外部 modeling/tilesim-runtime/.venv（Python3.11）；原 modeling .venv 与8768服务未改。源码Git匿名克隆需认证，使用官方文档指定PyPI包。SciPy1.15.3改用同版本macOS12 ARM64 wheel解决本机Mach-O加载问题；pip check、CLI及理论/工程API导入通过，910B1 MatMul工程模式成功预测10.936681071217901µs，输入与原始结果/依赖锁/wheel摘要均保存。未做真机精度验证。旧适配器固定theo且按字典读取，新API返回tuple，工程接口独立；不能直接接通或沿用旧硬件映射。OpScope仍未连接该独立环境，详见[安装记录](../docs/tilesim-installation.md)。

## 可选 Roofline 运行时（2026-09-22，已实现）

用户授权按分析实施。新增标准库serve.py，显式--engine-root/--engine-python指定外部环境；前端运行按钮→任务轮询→矩阵/图表/详情/JSON，支持保存含结果的离线HTML。当前本机服务在127.0.0.1:8768，原8767静态服务未改；重启命令见README。任务内存存储、2并发/12条保留、60秒超时，不创建modeling任务或访问测量DB。每组合独立节点与RooflineSimulator，不使用Hub缓存/回退。

默认MatMul及11基础模板支持保守形状和FP16/BF16/FP32（Embedding整数索引）；非默认执行选项拒绝，其他输入形式暂未适配。TileSim本体缺失，状态明确unsupported；即使装好仍须完成硬件/算子认证才能启用。Profiling、方法3/4运行时均空，示例模式保留虚拟数据。新契约synthetic=false、measurement=false，无参考偏差/计数器/trace；同规范配置和引擎身份才允许预测比较。

38项Python测试（含7项Node配置、3项异步/快照初始化检查）、四份JS语法、构建一致性及差异格式通过。新worker在11模板×3硬件上33次Roofline成功，对应TileSim33项均不支持。浏览器默认MatMul5/30有预测，H200277.935194μs；改A为[1024,4096]先清空再重新计算，H200约57.903/B200约25.452μs，双比较-56.0%。单详情JSON核对数值/来源/无参考，双条导出范围正确，控制台无错误。快照HTTP200及attachment和内嵌配置/5条结果核对；浏览器URL策略拒绝file://，未绕过，该项离线浏览器验收未完成。未做真机精度或TileSim执行验证，未推送。见 [实施方案与验收](../docs/live-evaluation-plan.md)。

## 建模组件复用分析（2026-09-22，只读核查）

用户要求先分析能否复用modeling Roofline/TileSim。已核查当前已跟踪源码并用其现有Python3.11.16环境执行11基础模板×3硬件共33次纯Roofline调用，全部成功；另验证4096² FP16 MatMul H200总耗时277.935194μs，均为预测、不是实测精度验证。默认校准库缺失，TileSim本体/目录缺失且import不可用。未提交任务、访问用户任务数据库、安装依赖或修改两项目业务代码。分析见 [复用可行性](../docs/modeling-reuse-analysis.md)。建议OpScope可选轻量服务及方法隔离适配器，先Roofline、后补TileSim；禁止自动回退冒充独立方法、沿用错误硬件映射/跨方法缓存、将旧示例细项或profiling_hit当作真实证据。仅新增分析与记忆，未实施、未推送。

## 本轮同步检查（2026-09-21）

用户明确授权 push。本轮重新通过26项Python测试（含Node配置测试）、三份JavaScript语法检查、页面构建和差异格式检查；远程main与提交前本地HEAD一致。提交范围包含结果矩阵、算子配置目录、方法3/4虚拟数据、CI及相关文档。推送是否成功以远程main与提交后HEAD一致性验证为准，GitHub托管CI结果尚未验证。

## 最新：方法3、方法4虚拟结果

用户授权方法3与方法4加入虚拟数据。方法3不再空占位，新增方法4；连同Profiling、Roofline、Tilesim共五列，默认6硬件30组合、25有示例数据。两新方法分别为琥珀菱形、青色三角图表标记。在5个已有示例硬件上各增加总耗时，R200仍缺失，11个目录型号不继承示例值。真实后端、任务ID、计算/访存分项、瓶颈和执行流水不虚构，execution.kind=virtual。修改配置仍清空，精确恢复示例才恢复25条。

26项Python测试（含7项Node配置测试）、JS语法、构建通过。桌面1366×900五列布局、方法4筛选、H100行图表聚焦、虚拟详情、方法3/4双比较及JSON检查正常；170/158微秒对应B较A -7.1%，JSON保留synthetic/virtual及backend=null。修改A形状后0/30，恢复25/30，控制台无错误；临时视口已恢复。方案见 [虚拟方法](../docs/virtual-methods.md)。

- 最新展示偏好：用户不需要硬件菜单的“独立合成示例”提示。已去掉分组标题，硬件统一列表，打开页面默认勾选原6个演示硬件；顶部示例数据标记及导出synthetic保留。定向验证17个选项、默认6个勾选、15/24结果、H100搜索、JS语法和构建通过；此次仅菜单展示调整。

## 最新：统一算子展示（2026-09-21，已实现）

用户明确界面不要体现来源项目、算子不要训练/推理标签，并去除重复项。现在100个内部模板归并为94个可见算子，MatMul（含示例）、Linear、RMSNorm、SwiGLU、Embedding各只一行。不同张量契约通过“输入形式”保留，标签为矩阵相乘/权重投影/融合投影等；内部适配身份继续存在，不混算性能。不同版本/融合算子未凭名字相似合并。

来源筛选、徽标、源码路径/提交号说明移除；硬件分组改“硬件配置”。JSON预览/下载也用中性算子/模板/硬件标识并移除来源域/仓库溯源，保留synthetic和性能来源；内部原数据不变。只验收桌面。24项Python测试（含7项Node）及3份JS语法通过；浏览器验证94个不重名列表、SwiGLU两种输入切换、硬件/详情无来源词、单条/双条JSON无原域与路径、MatMul示例恢复15条和双比较157/176微秒，控制台无错误。未推送或修改后端。

最后更新：2026-09-22。当前项目名 OpScope，目录名 opscope，中文名“算子性能观察台”。

## 当前状态（已实现）

- 环境说明已收敛为单一入口 `docs/environment.md`：逐条记录 uv 安装 Python、创建 `.venv`、锁定同步、requirements 兼容安装、依赖更新/导出、启动与验证命令。`.python-version` 固定开发 Python 3.12，`uv.lock` 纳入版本控制；`setup.sh` 使用 `uv sync --locked --all-groups`，防止安装时静默改锁。`backend/requirements.txt` 与 `backend/requirements-dev.txt` 由 `uv export` 生成，分别供运行和开发/CI。原重复的 `docs/setup-steps.md` 已合并删除。已在 `/tmp` 分别按 uv 锁文件和 `requirements-dev.txt` 从空环境安装，`uv pip check` 通过，Python 3.12 下 59 项测试全部通过。

- 按用户要求移除 `SHA256SUMS`，日常开发不维护文件哈希清单；打包文档中的校验结果仅为历史记录。
- 已添加 [CI 工作流](../.github/workflows/ci.yml)：push、PR、手动触发，检查单测、JS 语法和生成页面一致性；Python 3.12 / Node.js 24，不部署。GitHub 实际运行待推送后验证，设计见 [CI 说明](../docs/ci.md)。
- 从 modeling 的 HTML 原型提取为独立项目；构建、测试、离线运行不依赖 modeling。
- 原生 HTML/CSS/JS，Python 标准库生成内嵌页面。从原版保留实现与测试；命名时仅修改页面标题与品牌文案，重新生成 index.html。
- 可配置算子与输入，默认 MatMul 4096³；六个示例硬件/五方法/30个默认可见组合、25有数据。另有11组内置硬件可选，所有性能结果仍为合成 UI 示例。
- 硬件×方法矩阵、硬件/方法筛选、总耗时/偏差切换、联动偏差/耗时图、五页签浮层、双结果字段对齐、JSON 预览/选择/下载链接。
- Roofline 已合并成一个方法；已校准/通用估算为状态，bucket/aggregate/regression/heuristic 为示例来源。H200 回归仅总耗时，计算/访存/bound 为 null。
- 用户要求暂不使用GPU独立模拟器；方法3、方法4按后续授权提供虚拟总耗时，不代表实际模拟器执行。

## 用户确认的 UI 偏好

仅考虑 PC 桌面，用户明确移动端用不上，不再投入小屏适配。减少无关文字。外层应该看得到关键差异，深入细节后仍要让标签与数值靠近。取消多次实验的分布与 p50/p95；保留单次执行流水/核活动示意。顶部示例标记持续可见。不要把临时手机视口当成交付视图。

## 已验证与未验证

- 提取前最新版本八项单测、JS 语法检查、PC 筛选/比较/详情/JSON 检查通过。
- 独立包的本次验证见 [打包记录](../docs/PACKAGING.md)。
- CI 添加后，本地八项单测、JS 语法、构建一致性和差异格式检查通过；未安装 actionlint，GitHub 托管运行尚未验证。
- JSON 文件下载落盘、修正后的手机布局未完成验收。
- 可选Roofline后端已接入并验证调用；TileSim已按文首范围接入；无真实profiling、Accel-Sim执行或精度认证。
- 示例时钟、tiling、kernel 名称、校准系数和计数器均虚构，不可作为硬件事实。

## 专题与后续入口

- [数据口径和不可混淆的语义](data-semantics.md)
- [接入后端的建议、历史发现与待办](integration.md)
- [架构](../ARCHITECTURE.md)、[提取前原型迭代记录](../docs/HISTORY.md)

后续先依据用户目标决定导入数据或接 API，不默认升级框架。新 Agent 从 AGENTS.md 开始，不能把未来计划写成已完成能力。

## 项目命名与解压（2026-09-21）

用户要求命名并解压。已从原 ZIP 校验后提取为 opscope 独立目录；名称为 OpScope（算子性能观察台）。README、AGENTS、页面标题/品牌与本记忆同步更新。原压缩包与原独立目录保留为提取时快照，后续开发以 opscope 为准。功能和数据未变；重新构建、八项测试、JS 语法及校验清单验证通过。本轮未重复浏览器交互验收。

## GitHub 同步准备（2026-09-21）

用户指定远程仓库为 `git@github.com:Youngscc/opscope.git`。本目录初始化 Git，main 接续远程初始提交 `3e9061e`（原仅含 README），保留远程历史。同步前重新构建成功、八项单测和 JS 语法检查通过；未修改 UI，未重复浏览器验收。推送结果以远程 main 与本地 HEAD 的一致性为准。

## 界面选择（2026-09-21）

用户认为新版没有明显风格区别，决定继续使用原版。已删除新版生成页、模板、样式和对比方案；构建和 CI 恢复仅处理 index.html。原版页面保持不变。后续不要自动恢复该视觉实验。

## 单算子任务详情完善（2026-09-21）

参考 modeling 前端单算子、任务历史和算子依据源码，在原版新增任务概览/输入输出/硬件配置页签；保留已有五页签和外层微图快捷入口。新增 task_details.py，所有结果含结构化 task/workload/hardware_snapshot；真实任务与硬件规格未知字段保持 null。详情 JSON 导出当前一或两条结果，全局 JSON 仍导出筛选范围。

已验证：12 项单测、JS 语法、构建和差异格式；浏览器单条概览、张量表、硬件缺失、双结果布局、硬件筛选、H200 回归 bound 缺失、键盘页签；JSON 单条1/双条2/全局8条且无 details HTML、保留 synthetic。未验证下载落盘，未接入后端。1440px 临时视口已恢复。方案见 [详情设计](../docs/task-detail.md)。

- 2026-09-21 核查 modeling 的 FlashAttention 跨入口差异，已复现推理单算子8头输入仍按默认32头计算公式/输出的问题；前端还会重算耗时和 Bound。未修复，未取得用户具体任务，详见 [接入记录](integration.md)。不能将训练/推理同名方法视为同一工作负载契约。

- 2026-09-21 已只读核对用户指定 modeling 任务127/128：相同bf16 [1,32,2048,1]输入，后端均compute；FLOPs统计相差2倍、总字节相差9倍，Kepler另计softmax及10µs固定成本。页面重算可能反转bound；本例不是8头绑定bug。具体数值见 [接入记录](integration.md)，未修复业务代码。

## 结果矩阵设计（2026-09-21，仅提案）

用户要求硬件×方法二维网格、综合图表、悬浮详情，强调直观、简洁、美观且实用；明确先设计，不重构前端。详细提案见 [结果矩阵设计](../docs/result-matrix-design.md)。建议连续矩阵、每格总耗时/参考偏差/瓶颈三层，默认偏差点图、可切耗时条形图，点击行列聚焦，详情和双结果对比进入模态窗口。雷达图/无序类别折线暂缓；计时边界和可比性校验优先。以上具体取舍尚未由用户逐项确认。

会话中制作了独立交互设计示意，使用现有合成数值；检查了矩阵、指标切换、行聚焦、图表切换、单条浮层、Esc和双结果对齐，未见浏览器脚本错误。示意不是正式功能，未覆盖完整筛选/导出/全部详情；正式桌面断点与完整可访问性仍待实施验收。本轮仅新增设计文档与记忆，未修改页面源文件或生成index.html。

## 结果矩阵重构交付（2026-09-21，已实现）

用户随后授权按设计文档完整重构，允许跳出旧布局，指定interface-design与UI UX Pro Max两个skill。采用紧凑纸白/浅灰矩阵、蓝色交互、克制的方法系列色，配置收至顶部；原六硬件四方法默认全选。单元格三层信息，行列点击聚焦下方偏差点图/耗时条形图，图表标记可开详情。

原生dialog承载五页签；八类旧详情信息保留并重新分组。任务/来源/运行记录默认折叠；双结果共享字段逐行对齐，只有明确已提供且显示相同的字段才被差异过滤隐藏。matrix_data.py负责全数据统一图尺度（当前0–300µs/±25%）、详情字段预提取、有方向A/B差值和可比性。跨硬件又跨方法或真实契约未校验不给比值，不能将其视为已完成真实接入。

18项数据测试与JS语法通过；浏览器检查1440×900、1366×768、375×812，无页面横向溢出（矩阵自带横向滚动）；筛选、空组合、主指标、图表聚焦/切换、单条/双条、仅看差异、未知硬件、H200回归缺失、Esc焦点与键盘页签、JSON单条1/双条2/H100筛选4条。导出剔除details/sections/matrix而保留synthetic/null。下载落盘、200%缩放、完整屏幕阅读器验收未完成。临时视口交付前恢复。未引入依赖，未接后端或修改modeling，未推送/部署。详见 [矩阵设计](../docs/result-matrix-design.md) 和 [实施计划](../docs/result-matrix-plan.md)。

## 算子及硬件目录（2026-09-21，已实现）

用户要求完整modeling算子、shape/dtype配置、完整硬件列表和方法3候补。新增100条可搜索列表（99内置+1原合成示例）：train 11、infer 88，其中6通信资产标“单算子入口未提供”、不可应用；Flow注明流程标记。算子来源独立，vision旧资产保留实际seeder key。未知维度不补1；Python解析表达式后保留null，界面显示?并校验。9种dtype逐张量配置；矩阵/Attention/Embedding有基础契约校验，不等于完整内核支持认证。

公共硬件11个系统、22个train/infer档案，支持搜索/全选当前搜索/清空，Server/POD分开。旧6个示例独立分组，不能把示例耗时映射到新型号。默认仍展示原6个示例；首次切换目录算子默认选择Adevice03/H100/H200 Server以控制页面长度，其余型号均在列表。方法3仅候补，无原GPU模拟器数值。

新配置窗口左右分栏、独立滚动、固定底部应用按钮；主界面仅配置摘要。取消不提交；应用清空比较/聚焦，精确恢复原示例时才恢复15条数据。其余配置的矩阵/图表/详情/JSON都无性能结果，导出当前输入与来源、synthetic标记。内存配置不跨刷新保存。

快照工具只读modeling受跟踪源码，保留路径/提交号/内容摘要，日常构建不依赖原仓库。未导入用户数据库或私有生产覆盖；未运行后端评估或修改modeling。23项Python测试（含6项Node配置测试）、三份JS语法通过。浏览器覆盖1366×768、375×812、算子搜索/类别筛选、未知维度阻止应用、配置取消/应用/示例恢复、通信禁用、硬件POD搜索选择、方法3详情、双比较及1/2条JSON内容。文件下载落盘、完整屏幕阅读器与真实后端仍未验收。临时小屏视口完成后恢复。见 [目录方案](../docs/operator-catalog-plan.md)。

- 用户最新明确：不用考虑小屏，移动端用不上。后续设计与验收聚焦PC桌面；本轮此前进行过的小屏检查仅为历史记录，临时视口已恢复。

## Python 目录整理（2026-09-22，已实现）

根目录只保留 `build.py`、`serve.py` 两个 Python 兼容入口。离线构建和示例数据移入 `opscope/offline/`，请求契约、结果转换、运行时与 worker 移入 `opscope/evaluation/`，所有测试移入 `tests/`。后端直接从包导入；Roofline/TileSim worker 继续支持外部解释器按脚本启动。当前测试命令使用 `unittest discover -s tests`，详细边界见 [目录设计](../docs/python-layout.md)。

已验证 56 项 Python 测试、两组离线 Node 契约测试、2 项前端状态测试、JS 语法、Vue 类型检查/构建和离线生成。两个 worker 的独立解释器 probe 均成功；TileSim 输出一个不影响执行的 Fontconfig 缓存警告。目录迁移不改变数据语义或页面交互。

目录迁移后修复在线页启动选择：能力接口的 `tilesim_hardware` 是后端模型名称，不是目录 ID；前端现从 bootstrap 硬件目录选择 `tilesim:*` ID，不再提交 `910B1/H200` 等名称。后端非法选择提示区分硬件与方法。回归覆盖 TileSim 可用/不可用的初始选择，最小 Roofline 提交返回 202。

## 算子语义去重审计（2026-09-22，仅分析）

用户要求按算子内部逻辑而非名称去重。审计确认当前名称规则既漏合并异名同义项，也误合并同名异义项：MatMul/BMM/Linear/MatMulV3/TorchMm 可通过 batch、rank、weight transpose 形成同一规范算子的输入变体；训练 SwiGLU 是含三组权重投影的完整 MLP，推理 SwiGlu 只是末维二分激活，必须拆开。Embedding 推理资产缺显式权重，合并前需修正契约。量化、稀疏、分布式和融合算子只归同族，不直接去重。详细清单见 [语义去重审计](../docs/operator-semantic-dedup-audit.md)。本轮未修改目录或界面。

## 结果详情视觉层级优化（2026-09-22，已实现）

结果详情改为结构化事实列表，概览在桌面端保持总时延、有效算力、参考偏差、主要瓶颈同一行；总时延作为主视觉，其余指标和说明降权。任务、来源与运行记录移入默认折叠的三列元数据区，避免与性能结论竞争。双结果入口增加 A/B 标识，保留逐项表格、差异摘要与“仅看差异”。离线合成结果的说明文字继续显示，空的旧指标容器不再输出。

已验证 59 项 Python 测试、3 项前端测试、Vue 类型检查/构建、JS 语法、离线生成与差异格式。浏览器以桌面视口检查 H200 Roofline 概览、展开元数据、计算与访存页，以及 H200 Roofline/TileSim 双结果对照；关键指标未换行，折叠层级和 A/B 选择清晰。未进行移动端适配或验收，符合用户的 PC-only 要求。
