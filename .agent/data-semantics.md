# 数据口径

## 矩阵双结果比较（2026-09-23，当前入口）

直接选择当前矩阵两张有结果的卡片；Python 按二者原始总耗时生成从零开始的同尺度条形图，包括零值。口径不满足既有比较条件时仍显示绝对值与原因，但不计算变化率；不能从图中推断准确性、归因或实测加速。在线所选结果报告复用同一判定，示例保留 synthetic 标记。下方时间比较为保留接口的历史说明，页面入口已经移除。


## 两次评估时间对比（2026-09-23）

在线历史仅为服务内存中最近12个终态任务；时间来自任务提交/完成记录，不是设备测量时间。按硬件×方法配对两批结果，只有两侧成功且配置摘要、硬件规格摘要、引擎/校准身份一致、均非合成时才绘制同尺度总耗时条和计算(B−A)/A。A 为零时比率未定义但零值仍保留；缺失或身份变化保留 A/B 原值及原因，不能当成零。汇总计数只描述可比组合的预测时延方向，不平均不同硬件/方法，也不代表实测加速或模型准确度。[详细设计](../docs/time-comparison.md)。

独立 HTML 报告复用同一数值和判定，不重新执行模型。单项报告中的事件来自 `execution.events`，时间戳/时长均为 μs，核/通道活动可重叠；未提供事件时明确显示缺失，不从成本分项补造流水。报告不新增实测、归因或准确性结论。[报告设计](../docs/html-reports.md)。

## 最新展示约定

UI不展示来源项目或训练/推理域；100个内部模板按名称忽略大小写/下划线归并为94个列表入口。同名不同契约保留为“输入形式”，不因去重把SwiGLU的4输入融合投影与1输入门控混成同一工作负载。版本/融合算子不凭名字相似合并。内部domain/id/source继续用于准确校验与档案匹配，但对用户的JSON转换为中性operator_id/template_id，移除仓库路径、来源域和catalog_profiles等溯源字段；保留synthetic/null/执行与校准来源。不影响示例精确匹配和性能计算。

## 工作负载与外层

- MatMul M=N=K=4096，FP16 输入/输出、FP32 累加；逻辑 FLOPs=2MNK=137438953472。
- 逻辑字节=(MN+MK+KN)×2=100663296 bytes=96 MiB；不是实际 HBM 流量。
- latency_us 为设备侧单 kernel 总耗时，单位 μs。有效算力=逻辑 FLOPs/总时延，单位 TFLOP/s，不是峰值利用率。
- 偏差=(方法耗时−同硬件 Profiling 参考)/参考×100%；短于参考并不代表更准确。当前参考本身也是合成数据。
- 旧详情分项图共用 320 μs 尺度，有效算力示例元数据共用 2400 TFLOP/s 尺度。新矩阵分析图由Python根据全数据生成统一刻度，当前耗时0–300 μs、偏差−25%–25%；筛选不改变刻度。真实数据接入时不能直接套用示例上限。
- 外层与详情/导出共享同一数据源；实际流量、带宽、缓存命中、资源活动仅在相应示例记录中存在。

## 不同方法能展示什么

| 方法 | 当前示例 | 必须保留的边界 |
| --- | --- | --- |
| Profiling | 耗时、计数器、活动与流水 | 全部合成；并未采集真机 |
| Roofline | 总耗时、可用的计算/访存成本、校准元数据 | 不生成实际计数器、kernel 或 trace |
| Tilesim | 总耗时与详细执行示例 | 细项标“扩展字段示例”，不是原适配器真实输出 |
| 方法3 / 方法4 | 各5条手工虚拟总耗时 | 尚未指定模拟器；分项、瓶颈、kernel与流水为空；不继承旧Accel-Sim记录 |

Roofline 校准 status=calibrated/generic；source=bucket/aggregate/regression/heuristic。H200 演示 regression，compute_us、memory_us、bound 为 null，不从总时延虚构分项；其他解析示例的成本也不是真实模型计算。

## 单次执行与缺失

计算活动、访存活动、等待可以重叠，不能强制相加成总时延。局部流水仅 12 个事件，核活动仅 24 个示意实例，均不是完整 trace 或实际硬件核数。Cube/Vector 与 Tensor/SIMT 使用各自原生口径，不能直接当同定义计数器横比。

available=false 表示组合缺失，reason 保留原因；零耗时/零比例与 null 不等价。R200 正式型号仍待确认。synthetic 标记在整个 payload 与各结果保留。

当前 schema 为 operator-ui-demo-v1，是展示私有结构，不保证兼容实际 modeling 的 SimResult。导出仅当前筛选结果，剔除 details HTML，保留 execution、校准来源与缺失值。

矩阵新增 sections/matrix 展示预处理字段，导出一并剔除。双比较差值按(B−A)/A计算；A为零不计算比值，仍展示零值。合成同工作负载可同硬件比方法或同方法比硬件，硬件与方法同时变化时不作直接比值。真实来源尚未接入，缺契约不能套用此示例可比性。仅看差异过滤明确已提供且显示值相同的标量，未知字段仍保留。

## 任务上下文

每条结果包含 task/workload/hardware_snapshot。同一 MatMul 配置共享 workload_id，result_id 按硬件和方法区分。task.status=demo/unavailable，不代表真实任务完成；actual_backend、task_id/run_id、运行时间、回退原因与报告地址无来源时为 null。硬件快照未采集，峰值/容量等规格为 null。张量 A/B/C 各 33554432 bytes，输入 64 MiB、输出 32 MiB，合计 96 MiB，不是峰值显存。详情 JSON 仅当前一或两条结果，全局 JSON 仍为全部筛选结果。

## 可配置目录（2026-09-21）

以上MatMul数值只适用于精确的默认合成配置。现已允许选择modeling内置目录与逐张量shape/dtype：训练11条、推理88资产，保留来源身份而不把同名算子合并。通信6条仅目录不可应用，Flow条目注明流程标记。未知默认维度为null/“?”，必须人工填写，不自动取1。原始输出模板仅作来源说明，未执行时不推导输出。

硬件目录11个系统、22份train/infer来源，Server与POD分开。目录不等于仿真适配认证，R200_Server的存在不证明原R200别名已核实。原6个示例硬件独立于目录型号；目录硬件不复用示例性能。所有新增组合available=false、latency_us=null、task.status=not_run；修改配置不携带旧执行记录、FLOPs或逻辑字节。configuration保留应用的输入与来源；导出全局和逐条上下文一致。

## 实际模型调用（2026-09-22）

本地评估服务新增opscope-evaluation-v1。只有实际调用Roofline成功的组合available=true、task.status=succeeded，synthetic=false、measurement=false、execution.kind=analytic，不等于设备实测。缺失/不支持/失败字段为null，原SimResult缺省0不能冒充计数器。regression校准不展示计算/访存/瓶颈分项。工作量与分项来自本次结果；kernel/tiling/trace为空；无真机参考时deviation_percent=null。

规范配置与硬件规格分别有摘要，实际engine版本/源码摘要/校准库摘要保留。首次接入仅基础模板的默认语义；页面默认累加FP32、row-major不意味着模型比较不同kernel精度/布局。所有非默认执行选项拒绝，Attention限定QKV同形BNSD。边界为单算子解析预测，不指定实际kernel，不包括Host或传输；复合SwiGLU不宣称设备单kernel。

双预测对比要求相同配置摘要、相同引擎/校准身份，并固定硬件或方法至少一轴；比较文案明确非实测加速。切换运行整批清空示例参考与虚拟结果；恢复示例必须显式应用原配置。离线快照保留独立demo_results仅用于恢复，不参与当前results、JSON导出或图表。

## TileSim 工程结果（2026-09-22，已接入）

独立msopmodeling1.0.9按算子选择DSL工程、成本模型工程或成本模型理论路径。910B1/910B4的MatMul和FA可提供DSL流水；LayerNorm/RMSNorm/BMM/激活等成本模型通常只提供汇总。synthetic=false、measurement=false，execution.kind=tile_simulation，不冒充设备实测。通道分项可重叠；L2字段为预测字节命中率；data_transfer为模型路径累计量，不能当作真机HBM计数器。逻辑FLOPs、张量字节和有效算力由本系统按算子语义推导，并与TileSim内部工作周期区分。

固定输入分块128/256/512/128明确记录，非自动最优。输出与输入同FP16/BF16，累加精度未单独建模。整体compute_us/memory_us/bound、等待原因、实测参考与偏差均空。trace保留全部事件及6个规范字段（name/ts/dur/pid/tid/ph），省略冗长cat；原始模型占位值不提升为UI事实。按核通道活动用区间并集/全程时延，既非峰值利用率，也不用于推断同步等待。

## 部分结果与进度（2026-09-22）

任务运行中也可有payload与available=true结果。组合状态queued/running/succeeded/failed/unsupported/not_run分别表示等待/计算/成功/失败/不支持/本批未选；只有succeeded有预测数值，空缺为null。evaluation.total固定为本次请求硬件×方法数，finished_count统计所有终态组合，success_count只统计成功；status与completed_at表示整批状态。发布新组合保持已有结果ID与finished_at。中途JSON含evaluation元数据，不把部分结果当整批已完成；整批HTML快照仍需completed。

## 预测模式与借用模型（2026-09-22）

TileSim engine.mode区分dsl-eng/dsl-theo/cost-eng；只有真实events生成trace_view，其他路径为空且说明无流水。理论路径未赋值的周期/L2命中率/MTE1默认零改为null；工程API CUBE工作量为速率不能当周期，L1_cache元素按输入2B换算，API原值保留并标注固定占位字段。FA逻辑工作量采用B×N×S²×(4D+4)，不是引擎通道周期。借用硬件配置显示在卡片、硬件详情、JSON；涉及借用的跨硬件比较不计算真实型号加速比。

## 目录公式预测与算子属性（2026-09-23）

`infer:*` 的新 Roofline 路径以本地快照的输入/输出和 `compute_flops` 公式计算，`engine.mode=catalog-analytic`；它不是原 Kepler 图模型的完整移植。逻辑输入/输出字节与硬件 HBM 峰值给出访存下界，按公式的分精度 FLOPs 和对应峰值给出计算下界，取较大者；未计融合、静态开销、校准，也不产生设备事件。默认上下文中的并行度均为1，不能解释为真实并行策略。目录公式缺失、精度/峰值缺失、形状推导矛盾时拒绝预测；资产零FLOPs保留为零，绝不把缺项转成零。

硬件快照的 FP8/FP4 峰值键使用 `_tops`，FP16/BF16/FP32 等使用 `_tflops`；两者读取后都换算为每秒 10¹² 次运算。键名不匹配不得解释成缺规格。当前 `Adevice03_POD` 的 `fp8_tops=0` 仍按无可用峰值拒绝 FP8 目录公式预测，不能借用 Server 或 TileSim 的规格。

算子属性与张量shape/dtype分开存储在`configuration.attributes`，参与配置摘要与双结果可比性。TorchSum固定axis=1、TorchCumsum固定最后一轴、Transpose固定`[0,2,1]`。Cumsum和GatherV2的axis默认未知，须由用户明确填写，分别只接受最后一轴和0；仅axis张量的形状不能代表其数值。TileSim三维Linear请求会展平前导维度，结果的逻辑输出仍保留原维度；分布式/通信成本未包括在内。
