# 后续接入与已知边界

当前在线应用已采用Vue 3/TypeScript/Vite/Pinia/Router与FastAPI/Uvicorn，启动和宿主迁移入口见[框架对齐](../docs/framework-alignment.md)。`/api/opscope`路由可注入EvaluationRuntime；独立服务使用内置最小 Roofline 后端和固定 TileSim wheel，不再读取旧外部引擎路径。完整 modeling 任务系统仍未合入。

本文保留历史接入分析；文末记录已实现的可选 Roofline 本地服务。上传解析器与profiling数据库仍未接入；文末更新TileSim实际接入状态。

## 建议顺序（待实施）

1. 与用户确认先接入的算子、硬件和数据来源。建议从一个明确组合和设备侧单 kernel 边界开始。
2. 定义结构化结果契约：算子/shape/dtype/layout、硬件正式 SKU、方法、实际执行后端、版本、kernel/tiling 身份、耗时单位、来源、缺失原因。区分请求的方法和实际采用的方法。
3. 接入一份可追溯真机结果，再对齐 Roofline 和 TileSim 的输出，先建立总耗时与同口径偏差；分项只有真实提供才显示。
4. 性能计算、聚合、比值和图表数据预处理放后端。前端保留展示交互，不将当前 details HTML 作为外部可信输入。
5. 先做固定 fixture 契约测试，再做一条完整导入/查询→比较→详情→导出的端到端验证。不能把 API 返回成功称为精度验证。
6. 真正检验模型精度需要不同于校准集的真机留出样本；本项目尚未做此项工作。

## modeling 历史发现（2026-09-20/21，需在接入时重新核实）

这些发现来自原仓库当时的审计，原代码不随本包提供，不能据此假设当前环境也相同：

- 公共 Roofline 支持校准来源选择；查表与 TileSim 是其他成本来源。普通和校准 Roofline 没有必要在 UI 上重复列为方法。
- 训练/推理单算子入口并非同一套采用规则；推理可能发生查表→TileSim→Roofline 的选择/回退。必须记录实际采用来源，不能只信请求名。
- 原单算子接口的 profiling_hit 字段不能直接证明真机数据来源；按算子、shape、dtype、硬件、软件/内核版本核对查表匹配。
- 同一 Hub 缓存未按方法隔离是接入风险；每次新建 Hub 的路径当时未复现串用。
- Adevice03 配置 SoC 为 Ascend910_9382，而 TileSim 当时仍使用 910B4 配置；多个 GPU 名称共用 H200 路径。确认过配置差异，未量化误差或修复。
- 当时本机 TileSim 无法导入，未审计其内部模型；默认校准库缺失，部分本地配置关闭 Lookup。这些都是历史环境状态。
- CANN 算子 Host/kernel 与调度库可帮助恢复执行细节，但开源版本不等于真机安装包。需匹配正式 SKU、软件版本、tiling 和运行记录。
- 当时调研发现 Accel-Sim dev 有 H100/H200 配置，未编译/运行；Blackwell 支持未验证。此项可能随版本变化，需重新查官方资料。

上述问题没有因独立打包而修复。原后端业务测试的历史失败也不能视作本静态前端的测试结果。

## 后续 Agent 的第一步

先读 README 与数据语义，运行已有八项测试，向用户当前目标对齐。未获新的实现要求前不主动删除 Accel-Sim、引入框架、调用远程评估或更改任何硬件参数。

## FlashAttention 同配置差异核查（2026-09-21，已复现实例，未修复）

本地直接调用 modeling 训练单算子服务和推理 `_simulate`（使用仓库 FlashAttentionScore 资产，不查任务数据库）：H100、BF16、Q/K/V 均 [2,8,512,128]。训练 FLOPs=2164260864、输出 [2,8,512,128]；推理 FLOPs=8589934592、attention_out=[2,32,512,128]。推理维度绑定仅处理独立变量，未从 `num_attention_heads // tp_size` 绑定头数，默认32头继续进入公式和输出。另有 BNSD 第1维被写入 input_length 的静态映射问题，其对具体任务影响未单独验证。

32头对照时，两链路计算量和输出字节仍不同：训练包括 softmax 工作量，推理返回两份 FP32 softmax 统计辅助输出。前端 deriveOpReport 使用返回 FLOPs/Bytes 和页面有效算力/带宽重新计算耗时与 Bound。上述两个实测样例后端 Bound 均为 compute，没有复现用户所说的相反结果；用户具体配置/任务尚待提供，不能据此断定该任务根因。没有修改 modeling 业务代码。

### modeling 任务 127 / 128 定向核对（2026-09-21，只读）

读取用户指定的本地 task_store.sqlite3 中 task/config/run/result，127=train/simulate_op/zrt_roofline（run145），128=infer/infer_simulate_op/kepler_operator（run146）。两者 bf16 QKV 均 [1,32,2048,1]、硬件同名 Adevice03_POD，但保存的硬件资产分别为 train/infer，配置不完全相同。

- 127：FLOPs1073741824，读393216B/写131072B，AI2048，计算19.217337µs/访存0.8192µs/总19.217337µs，bound=compute。
- 128：FLOPs536870912，读393216B/写4325376B，AI113.777778，计算37.282702µs/访存3.515625µs/总47.282702µs，bound=compute。额外两个 fp32 [1,32,2048,8] softmax 输出各2MiB，令总字节从0.5MiB增至4.5MiB。
- 127 FLOPs含两次矩阵乘加4个softmax操作；128返回的FLOPs仅矩阵乘，softmax在Kepler内部独立计时。D=1时softmax成本突出：华为Vector/SFU按24TFLOPS×0.6计价，softmax共536870912操作，对应37.282702µs，再加固定10µs。
- 两者后端均计算受限，不能称为后端bound相反。PerformanceOpPage.vue deriveOpReport用返回FLOPs/总字节与当前UI硬件/利用率重新算时延和bound，忽略Kepler softmax成本和固定开销；同一阈值在113.78与2048之间时即可显示相反bound。具体当时滑条值没有保存在任务配置中，未声称复原当时屏幕值。
- 本例头数32与默认值相同，前次复现的8头绑定bug不是这两条差异的原因。无业务代码修改，无任务重跑；原始结果来自保存记录。

## 第一阶段已接入（2026-09-22）

上文完全静态及未接入状态为历史。现已实现可选本地服务与严格Roofline适配，详见[本地评估设计](../docs/live-evaluation-plan.md)。使用显式外部目录/解释器，通过子进程调用基础算子构造及RooflineSimulator，不使用Hub方法缓存、不提交原系统任务、不查测量数据库。33个基础模板×硬件组合经新适配器实际调用成功；这不构成精度或完整目录覆盖验证。

TileSim本体与硬件配置仍缺失，因此只提供可观察的不可用原因；即便安装，仍需单独认证转换和硬件映射后才能启用。测量参考也未接入。方法3/4继续只供离线演示。源码中的默认校准库本次探测缺失，预测为未校准Roofline。

## TileSim 安装状态更新（2026-09-22）

已独立安装并通过工程模式单算子冒烟验证，见[安装记录](../docs/tilesim-installation.md)。以上“本体缺失”为原解释器历史状态；当前OpScope尚未连接新的tilesim-runtime环境。新版本API返回格式、工程接口与硬件映射仍需单独适配。

## TileSim输出口径（2026-09-22）

接入前必读[字段审计](../docs/tilesim-output-inventory.md)：单位、占位、最慢核分项、tiling及trace合并均存在实现边界，不能按字段名直连UI。包含三路径实跑数据及关键源码摘要。

## TileSim 接入状态（2026-09-22，已实现）

初版曾通过 `--tilesim-python` 连接独立环境；该启动参数现已移除。MatMul+910B1/910B4使用DSL工程路径，和Roofline分别执行，不使用旧适配器。支持范围、固定分块及事件预算见[接入设计](../docs/tilesim-integration-plan.md)。真实来源字段、流水、JSON与详情已联通；其他算子/芯片仍未验证，无真机精度认证。默认4096²FP16和128²BF16均在两个硬件模型上实跑成功。

## 覆盖补齐更新（2026-09-22）

已接入 R200_Server Roofline、910B1/B4 的 DSL 工程 FA（保留 B/N/S/D）和现有硬件到 TileSim 的映射。Ascend 9382 使用 910B4，H100/B300 使用 H200 均明确标记借用；不能解释为对应 SKU 的独立预测。H200 配置 FP16 MatMul 理论、FA 工程 API 已跑通；GPU BF16 配置不存在，GB200/R200 理论路径缺 L0C→L2 带宽、FA 工程缺 UB/L0；原仓库没有 910B1/B4 完整 Roofline 规格。详细验证及限制见[覆盖记录](../docs/modeling-coverage-plan.md)。外部仓库没有修改。
