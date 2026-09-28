# Modeling 后端接入实施计划

日期：2026-09-24。状态：第一阶段核心链路已实施；完整迁移仍在进行。以下原检查项按完整验收口径保留，部分已实现但尚未全项验证。当前事实以[共享模式](modeling-runtime.md)为准。方案依据见[接入设计](modeling-backend-integration-design.md)。

## 执行顺序

先对齐基线和依赖，再实现 modeling 的严格执行入口，随后接 OpScope，最后扩展目录及验收。不要同时改页面、计算模型和目录来追求一次完成，否则难以定位数值差异。

轻量化顺序：直接复用 → 兼容扩展 → 必要新增。下文目录、接口和模块均是职责划分，不要求各新建一套；能在现有服务中满足契约就不另起模块。OpScope 最终只保留界面、必要的矩阵编排及适配，计算、数据、任务执行和权限尽量沿用 modeling。

### P0：确认版本与可执行环境

- [ ] 核对三个仓库工作区、分支和远端提交；保留既有未提交修改及用户 trace 文件。
- [ ] 按已经确定的 GitHub 主、GitCode 副关系对齐实施基线。此前 GitHub main 已新增同步工作流，本地 integration 分支不能假设与它完全一致。先比较差异再合并，不盲目 pull 或强推。
- [ ] modeling 与 UI 使用已有 `codex/opscope-modeling-integration` 工作分支；OpScope 实施时从确认后的基线建立同名分支。UI 本阶段不新增功能提交。远端发布仍走既定 GitHub main → GitCode 开发分支流程，发布前遵循用户当次授权。
- [x] 使用 modeling 指定 Python 检查 Roofline、TileSim 的包版本、导入路径和一项小型预测；复核 wheel/API 兼容性与平台依赖，形成可重复安装说明。
- [ ] 保存现有 OpScope 及 modeling 代表结果，包括有效配置、校准、硬件身份与输出来源。选取一个双方真实支持的 MatMul 组合，不预设缺规格型号必然可跑。
- [x] 在 modeling 侧按其项目规则补充设计、实施文档及必要的依赖边界记录，链接本次契约；不修改宿主前端。
- [ ] 核对硬件统一加载器、部署覆盖、TileSim 包内配置、算子模板及资产版本/可见性；列出 OpScope 本地目录、规格、默认参数和映射的替换清单。
- [ ] 建立“已有能力→复用位置→真实缺口→最小改动”清单，逐项检查 assets、单算子、jobs、权限和存储；记录接入前依赖/进程基线，不先新建同类基础设施。

交付：可复现的 modeling 运行环境、锁定的两边 revision、真实调用样例。若 TileSim 依赖未满足，先修复依赖，不能用 mock 声称已接通。

### P1：Modeling 共享严格执行服务

- [x] 建立版本化输入/输出契约和明确错误分类；先支持一个 MatMul 配置。
- [ ] 复用并按需补充 modeling 已有资产查询与硬件加载器；返回算子 schema、语义分组、硬件档案和具体版本。必要时提取少量共享归一化函数，不维护第二套目录服务或数据。语义关系在 modeling 定义，OpScope 仅呈现。
- [ ] 从既有构造逻辑中提取可共享的 OpNode/TensorMeta 构造、输出推导与硬件解析；无 Web 到核心的反向依赖。
- [x] 分别直接调用 `RooflineSimulator` 和 `TilesimSimulator`；每次新节点及隔离的执行状态，不走允许方法回退的 policy。
- [x] TileSim 能力探测与实际预测分开；现有 `can_simulate` 会执行预测，不能把它当目录枚举函数或在独立实例中重复调用。
- [x] 保存 TileSim 原生总时延并给 Roofline 补充分项加来源；将可选补充失败与主预测失败分开。以兼容扩展保留旧调用行为，不修改计算公式来迎合旧 OpScope 数值。
- [x] 输出请求/实际硬件和 dtype 等转换记录；严格模式拒绝未经确认的非等价映射。
- [x] 明确校准政策及版本；新增服务不复用未包含方法等信息的旧缓存。

交付：通过 Python 服务入口调用两种真实模型的结果，包含来源、单位、缺失原因。原 modeling 调用回归通过。

### P2：Modeling API 与异步任务

- [x] 优先兼容扩展既有单算子提交入口，无法安全兼容时才新增严格入口；能力探测不启动模拟。
- [ ] 优先直接使用现有资产和算子目录接口，按需补充规范化字段；执行时固定所选版本，保存有效配置快照，验证目录过期和资产不可见的错误行为。
- [x] 复用现有任务操作、worker 分发、状态与结果机制，仅在语义需要时注册新操作，不另造队列。
- [ ] 验证任务身份、资源可见性、请求幂等、取消和超时；处理部署前缀。
- [ ] 明确批量并发上限及模型进程隔离。CPU 密集预测不占用 API 事件循环；超时/取消能否真正终止计算必须实测。
- [x] 把任务结果保存为契约化数据，必要大体积详情使用已有 artifact 机制；没有原生进度只上报阶段。

交付：HTTP 可提交并查询单项 Roofline/TileSim；现有用户和任务路径不受影响。先用脚本验证，不依赖 OpScope 页面。

### P3：接入 OpScope 当前界面

- [x] `EvaluationRuntime` 引入明确的 provider 边界及远程实现；保留现有批次、单格状态和 revision 协议。
- [x] 在线从 modeling 加载能力/目录，解除对内置目录的硬性绑定；离线示例沿用原目录和 synthetic 标记。
- [ ] 算子表单从后端 schema 生成默认值与约束，硬件信息从后端有效档案获取；停止读取本地规格、算子定义及 TileSim 映射作为在线计算依据。目录缓存按用户/版本隔离，失联不切换本地数据。
- [x] 用户选择转换为统一请求；远程 provider 不再执行本地 Roofline/TileSim，也不自己补建模数值。
- [ ] 一个硬件×方法对应一个远程任务；有结果立即更新对应卡片；其他项继续执行。处理丢失连接、部分提交失败及取消传播。
- [x] 结果转换、详情、比较、JSON 和报告保留原来源及新增字段来源；旧任务不改写来源。
- [x] 对 modeling provider 明确错误，不做本地兜底；前三种 lookup 仍按未接数据源处理。
- [x] 如现有 OpScope 客户端需携带宿主身份，仅修改 OpScope 的必要通信层，不修改 `zrt-sim-ui`。

交付：现有 OpScope 页面实际调用 modeling，在无本地计算依赖的 OpScope 环境跑通两个方法；单项与双项报告一致。

### P4：目录覆盖、语义与可选详情

- [ ] 为当前所有算子生成映射表：原 ID、统一语义、等价条件、modeling 入口、每方法/硬件/dtype 支持与阻塞原因。
- [ ] 先扩展基础 MatMul/batch、逐元素、Softmax、LayerNorm/RMSNorm、FlashAttention 等代表类别，再覆盖其余资产；实际优先级依据真实可用模型调整。
- [ ] train 模板之外的资产，核对符号维度、输入角色、输出、融合、量化与通信边界；不把 Kepler 结果直接改标为 Roofline/TileSim。
- [ ] modeling 已有模型但缺桥接时，在 modeling 共享服务补桥接与测试；底层缺模型/规格时留下准确原因和数据文件位置。
- [x] 按实际 TileSim 包能力评估工程模式、原始指标和事件暴露；当前只有理论模式的路径不伪装有工程流水。此项不得阻塞基础时延接通。
- [ ] 生成全目录覆盖差异，标明相对原 OpScope 新增、保留、暂不支持的组合及原因；未跑不算支持。

交付：可以逐项解释的覆盖表和真实输出样本。不得以“全部卡片都有数字”代替支持正确性。

### P5：验收与清理

- [ ] 通过下方验收矩阵和设计中的全部标准；原 modeling 后端回归通过，确认宿主前端本次无源码差异。
- [ ] 验证 modeling 更新一项硬件/算子后 OpScope 刷新可见、旧任务保持原配置；明确本地快照只用于离线/显式独立模式，线上无双份规格维护。
- [x] 更新两个后端各自的当前能力说明、架构、启动文档、环境依赖及变更记录，注明已完成与缺口。
- [ ] 只有接入验收后才清理 OpScope 在线重复模型及不再需要的本地运行依赖。保留离线展示、报告与明确需要的兼容边界。
- [ ] 评估保留独立模式还是完成迁移；不得在删除前把未迁移能力默默隐藏。切换/回退必须显式，结果来源不混用。
- [ ] 审计最终新增接口、模块、依赖及进程数，说明每项无法直接复用的原因；删除不再需要的过渡适配，避免保留两套长期维护路径。

交付：可复现启动方式、测试证据、覆盖清单和来源一致的界面。提交/推送按后续用户指令执行，不因本计划自动发布。

## 文件级改动地图

表中“新增”是必要时的候选位置；能扩展现有模块就不新增，实施时依真实缺口定稿，不意味着本次已创建代码。

| 仓库/位置 | 计划改动 |
| --- | --- |
| modeling `backend/operator_evaluation/`（新增） | 规范化请求、能力描述、严格执行服务、结果与字段来源；不复制 simulator 算法 |
| modeling `backend/simulator/backends/roofline.py`、`tilesim.py`、`utils.py` | 优先复用；仅补必要的兼容扩展、详细结果暴露或映射元数据；保持原默认行为 |
| modeling `backend/web/services/train/op_sim.py` 及 IR/硬件 registry | 提取共享构造能力，避免新接口复制另一份模板公式 |
| modeling `backend/hardware/builtin_hardware.py`、`spec.py` 与 train/infer 规格目录 | 复用统一加载、配置覆盖和单位边界，不新增 OpScope 专用规格副本 |
| modeling 既有 assets 服务/存储、算子 JSON 及目录辅助逻辑 | 共享用户可见资产、版本、输入 schema 和语义分组；必要规范化在 modeling 内完成 |
| modeling `backend/web/routes/`、schemas、`backend/web/app.py` | 新严格单项 API/响应 schema 和路由注册，保留原路由 |
| modeling `backend/web/services/job_store.py`、worker 注册和作业模块 | 新任务类型、状态、结果、取消与权限衔接 |
| modeling 依赖声明、锁文件和安装文档 | 明确 TileSim 包版本、安装来源、平台与导入方式 |
| OpScope `opscope/evaluation/evaluation_runtime.py` | provider 注入、矩阵到远程任务映射和增量状态 |
| OpScope `opscope/evaluation/modeling_provider.py`（新增） | HTTP 调用、幂等重试、错误映射和取消，无建模算法 |
| OpScope `opscope/evaluation/evaluation_contract.py` | 在线目录、输入结构和方法选项的合法性校验 |
| OpScope 本地目录/规格快照、`operator_parameters.py` 与 `tilesim_contract.py` | 退出集成模式的数据权威路径；迁移期保留明确的离线/独立用途 |
| OpScope `opscope/evaluation/evaluation_results.py` 及比较/报告模块 | 后端无关的结果转换、可比性、字段来源与空值语义 |
| OpScope `backend/web/settings.py`、app/routes | provider 配置、服务地址、身份上下文及启动能力检查 |
| OpScope `frontend/src/` | 必要的状态和来源展示兼容；保留现有页面布局和操作 |
| 两仓库 tests 与 docs、OpScope `.agent/` | 契约、回归、真实样例、当前能力和迁移说明 |
| `zrt-sim-ui` | 本阶段无代码改动 |

## 验收矩阵

| 用例 | 观测点 |
| --- | --- |
| 小型 FP16 MatMul × 两种方法 | modeling 原生调用、共享入口、OpScope 调用有效配置一致，时延及来源一致；容差按模型确定，不预设允许任意误差 |
| LayerNorm/RMSNorm/FA/BatchMatMul 代表输入 | 维度、属性、输出与数学边界一致；不存在同名误映射 |
| TileSim 缺依赖、异常或不支持 | 实际后端不变成 Roofline；无本地兜底、零值成功或示例替代 |
| 910B1/B4 等缺 Roofline 规格组合 | 返回具体缺项；TileSim 本身成功时不因可选 Roofline 分项丢失主结果 |
| FP8→INT8、GPU→其他型号映射 | 记录原始/实际配置；严格模式拒绝非等价替代，不能以成功掩盖变化 |
| 同输入不同方法/硬件/校准，交替并发执行 | 无旧缓存或节点结果串用；原任务结果不可被新请求覆盖 |
| 多格有快有慢、有成功有失败 | 第一格完成即可见，其他格继续；重复轮询不重复提交 |
| 超时、断网重试、取消 | 状态可信，幂等请求不重复运行；远程仍运行时不谎报已终止 |
| 不同用户任务/资产 | 既有授权边界生效，无跨用户读取、取消或缓存泄露 |
| 详情、A/B 比较、JSON 和 HTML 报告 | 数值、单位、来源、空值、零值和近似说明一致；无原生事件时不生成流水 |
| OpScope 环境无本地计算依赖 | 仍可执行远程评估，能证明没有调用内置建模实现 |
| modeling 更新算子或硬件，新旧版本同时存在 | OpScope 刷新可见新版本，无需更新本地 JSON；旧任务结果和配置不变 |
| 删除、失效、越权或同名不同配置资产 | 提交锁定 ID/版本，不按名字悄悄换配置、不混合 train/infer 字段，无私有资产泄露 |
| OpScope 集成环境无本地算子/硬件执行快照 | 目录、配置、评估继续可用；远程失联时明确报错，不偷偷使用旧数据 |

真实结果验证不能只比较 mock。mock 用于异常、幂等和状态转换测试；数值一致性须保存真实配置、依赖版本、原始结果和对照结果。宿主原有回退接口的输出不一定是严格 TileSim，不能不检查 actual backend 就拿它当基准。

## 本轮实际完成（2026-09-24）

- P0：本地工作区/分支及未提交内容已核对、保留；modeling 依赖实际安装并运行。未合并远端同步工作流，发布前仍需对齐远端。三个项目均使用 integration 分支，宿主 UI 未修改。
- P1/P2：已实现 strict-operator-v1、共享构造/执行、真实 TileSim 包兼容、资产冻结、只读规范化目录；复用 simulate_op/jobs/worker，无新队列数据库。拒绝方法回退和未认证替代。
- P3：HTTP provider、动态输入/硬件目录、逐项显示、来源详情、比较、JSON、HTML 报告、轻量安装已贯通。原界面保留；身份支持配置原有加密头；生产登录透传待集成。没有提交自动重试；超时/服务关闭请求取消，页面切换配置传播取消，停止后续组合；一次真实上游取消已验证为 cancelled。
- P4：目录100模板/22硬件档案；MatMul/BMM分组，其余完整去重未认证。H200 Roofline默认输入100模板审计55成功45unsupported；全硬件×方法、任意输入和工程TileSim未验收。
- P5：OpScope回归通过；modeling定向、HTTP和E2E已跑，全量存在收集错误、硬件专项两项失败，详见当前说明。原模型副本和离线快照保留给独立模式，不做提前删除。

### 接口与文件最终取舍

未新增候选 `backend/operator_evaluation/`、任务类型或专用数据库。modeling 使用现有 `train/opsim.py`、schemas、worker操作，增加 `train/strict_catalog.py`、`train/strict_op.py` 和包兼容 loader。OpScope 新增 `modeling_provider.py`、`modeling_details.py`，轻量requirements；计算库仅为可选extra。当前仅多部署一个既有OpScope Web进程，复用原modeling Web/worker，测试服务是隔离验证用途。

后续优先：生产身份与跨用户验收；取消与超时真实终止验证；共享资产符号/语义覆盖；完整去重与全硬件差异审计；覆盖达标后删除独立副本。不能通过删掉未迁移算子来宣称迁移完成。
