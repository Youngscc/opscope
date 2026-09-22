# TileSim 1.0.9 输出字段审计

2026-09-22。范围为当前安装 wheel 的公开 API、CLI 文件输出及算子流水底层结果；不是所有内部临时变量、调试绘图或所有算子实现的完整审计。以源码赋值为准，不把字段名称当单位或把默认零当已计算。未改引擎代码，未接入网页。

证据：[三路径原始结果](tilesim-output-audit/matmul-output.json)、[复现脚本](tilesim-output-audit/reproduce.py)、[关键源码 SHA256](tilesim-output-audit/source-hashes.json)。依赖及路径见[安装记录](tilesim-installation.md)。复现时在 modeling/tilesim-runtime 目录使用其 .venv/bin/python 运行脚本，依赖该目录 matmul-eng.json；脚本会输出 output-audit.json 和 DSL 自动生成的 trace.json。

## 入口和统计范围

|入口|成功返回|流水|
|---|---|---|
|CLI `backend_type=theo`|每个算子一个14字段字典，包装为OP_0等|公开结果没有trace|
|CLI `backend_type=eng`|另一工程实现的14字段字典|公开结果没有trace|
|通用 `op_latency_predict`|tuple：(14字段结果, 优化建议列表)；按输入模式走注册表|底层可能生成，但格式化结果不保留|
|工程 `op_latency_predict_engineering`|14字段字典|本返回结构没有trace|
|直接 `EngineeringOperator.run()`，本次为EngMatmulL0|17字段OperatorResult|trace中有traceEvents|

CLI通过PredictionService将theo和eng路由到两个不同函数；不能把CLI eng等同于DSL EngineeringOperator。通用API也可以按注册表接入DSL eng，但本次DSL验证用直接类调用。定义字段数量并不等于有效指标数量，更不能将各层数量相加为独立指标总数。

## 公开算子结果：恰好14个顶层字段

|字段|实际意义/单位|边界|
|---|---|---|
|op_name|算子或实现名称，字符串|例：TheoMatMul与MatMul不相同|
|latency|预测总时延，µs|模型预测，不是真机执行耗时|
|component_latency|通道时间字典，µs|理论7项，工程9项；可重叠|
|l2_hit_rate|模型L2命中比例|理论MatMul本例0，DSL按命中字节比例计算；不是实测计数器|
|cube_utilization_rate|CUBE分项时间/latency|模型时间占比，不是硬件监控occupancy|
|vec_utilization_rate|VEC分项时间/latency|同上|
|mem_volume|访存统计字典|两API键和计算口径不同，见下|
|compute_workload|CUBE/VEC二项字典|两API单位不同，见下|
|gm_volume|当前格式化固定0|未提供有效全局内存总量|
|tiling_info|分块结果字典|可能空、零占位或名称推断错误|
|ideal_time_by_mem|默认或固定0|未输出有效理想访存耗时|
|ideal_time_by_cube|默认或固定0|未输出有效理想矩阵计算耗时|
|ideal_time_by_vec|默认或固定0|未输出有效理想向量计算耗时|
|ideal_ratio|默认或固定0|未输出有效理想性能差距|

最后五个占位字段是gm_volume和四个ideal_*，两条API都如此；不能显示为真实的0耗时、0访存或0效率。

### component_latency：7/9个子字段

共有7项：CUBE（矩阵计算）、MTE1（AIC片上L1→L0搬运）、MTE2（AIC侧外部数据搬入）、FIXPIPE（结果写回）、VEC（向量计算）、MTE2_AIV（AIV侧搬入）、MTE3（AIV侧搬出）。具体存储路线取决于算子，不应把每个MTE2事件都硬标成一次真实HBM读取。

工程API另加AIC_MEM_ACCESS和AIV_MEM_ACCESS，两者是派生汇总，不能再与组成项相加。AIC_MEM_ACCESS=max(MTE1,MTE2,FIXPIPE)；AIV_MEM_ACCESS对路径名含910B的配置取MTE2_AIV+MTE3，否则取max。该判定来自字符串，属于实现边界。

### mem_volume：两种不同结构

- 理论API直接暴露OperatorResult.data_transfer，键为模型实际产生的路径，不存在统一固定键集合。本例GM_2_L2、L2_2_L1、L0C_2_L2；DSL工程本例GM_2_L1、L1_2_L0A、L1_2_L0B、L0C_2_GM。DSL按张量元素数×dtype字节数累计，单位Bytes。
- 工程API固定6项：L1_cache、L0A_cache、L0B_cache、L0C_cache、L2_cache、UB_cache。它们不是芯片容量，也不是命中率。检查inter_core_pipeline._cache_stat：L1_cache累计tile.size（元素数），其余项使用tile.size×precision.size（字节）；并且AIC tile数据量同时累计到三个L0项。因此不能统一标成“各层真实搬运字节数”，需要逐项修正/适配，其他算子赋值分支未穷举。

### compute_workload：同名但单位不一致

- 通用/理论API的CUBE/VEC直接取aic_cycles/aiv_cycles；本次理论MatMul两者为0，不能解释成没有计算。
- 工程API的CUBE=2×AIC_TOTAL_MKN/CORE_TIME。时间单位µs，按矩阵乘加两次操作口径，这是操作数/µs，并非总FLOPs；除以10^6才是对应的TFLOP/s。本例196356063.9663837，即约196.356TFLOP/s。VEC取AIV_TOTAL_CYCLES。
- 不跨模式比较这两个字典的原始数值。

### tiling_info

工程API按name_0等动态阶段键输出；每阶段11个直接字段：item_name、tiling_type、l0_m、l0_n、l0_k、l1_m、l1_n、l1_k、ub_m、ub_n、param。param包含swizzle_dir、swizzle_offset两项。ub_m/ub_n直接复用m1/n1，core标签由k0>0推断。

本次CLI工程MatMul返回CATLASS、八个尺寸均0，并被描述为“AIV”；不能据此声称有效分块为0或MatMul在AIV执行。DSL本次tuning_result为空，候选tm128/tn256/tk1=256/tk0=64来自输入记录，并非结果返回。CLI工程使用tiling_config，DSL使用extra_param.tuning_candidates；相同JSON不保证参数被两条实现以相同方式采用。

## 底层OperatorResult：17个字段

|分组|全部字段|口径|
|---|---|---|
|时间10项|latency、aic_time、aic_cube_time、aic_mte2_time、aic_mte1_time、aic_fixpipe_time、aiv_time、aiv_vec_time、aiv_mte2_time、aiv_mte3_time|µs。规则流水实现latency取全局最晚结束；7个通道分项是max_latency_core上的工作累计，非全芯片总和。aic_time/aiv_time是该实现计算的span，不直接等于busy时间|
|搬运2项|data_transfer、small_pkt_transfer|按路径统计的数据量；小包统计可能空，键类型可能为枚举tuple，需要JSON规范化|
|事件1项|trace|默认None；规则流水结果实际是包含traceEvents的dict，虽类型标注写list|
|分块1项|tuning_result|动态字典，本例空|
|周期2项|aic_cycles、aiv_cycles|规则流水中为对应最慢核工作时间×clock_freq后取整，不是所有核周期总和|
|缓存1项|l2_access_rate|规则流水实现为hit_byte/(hit_byte+miss_byte)，无访问时0；实际代表命中比例，字段名容易误读|

DSL结果可有全部17个键，但默认0/空/None与真实零无法仅凭序列化值区分，应结合路径和实现标记状态。

## trace事件：每条7个键

|键|内容|
|---|---|
|name|Tile操作名称；copy包含源/目的存储层|
|cat|操作ID、事件计数及OpEntity文本；文本含张量形状、dtype、存储位置、offset等，但不是稳定的结构化子字段|
|ph|固定X，完整时长事件|
|ts|开始时间，µs|
|dur|持续时间，µs|
|pid|核类型及编号，如AIC_0|
|tid|执行通道，如CUBE或AIC_MTE2|

足以构造分核分通道时间线、重叠和空闲区间。没有独立的等待原因分类、依赖边列表、硬件指令PC或源码行映射；不能仅凭空白区自动断定等待原因。零时长事件被过滤，一个操作可能按多个执行单元生成多条事件，所以事件数不等于真实指令数。

本次MatMul实际1736事件、24个AIC核、4类通道，ts≥0、dur>0、max(ts+dur)=8.559025912870776µs，与本次DSL总耗时一致。这不是所有算子或多阶段融合的保证。

## 其他接口、文件与错误

- TileOp API成功仅输出latency（µs）和cycles（周期）2项；底层TileOpLatency还有unit_latency、data_transfer、small_pkt_transfer，共5字段，但不由该公开DTO返回。本次仅核对定义与转换代码，未实跑此接口。
- PTO ISA API当前包装只列TADD，成功返回pto_dispatch的整数周期。函数名含latency不能据此认作µs；并非通用完整指令集接口。本次未实跑。
- system_api.get_system_info定义engine/version两项，与性能结果独立；版本依赖内置version.json，本次仅核对源码，未验证调用。
- 通用算子API另返回优化建议列表。当前生成器仅实现“小包搬运”提示，单条含“算子性能影响表征”“根因”“瓶颈定位结果”3键；并非通用根因诊断系统。本次为空。
- CLI将结果包装OP_0、OP_1等，-o写JSON否则stdout；有建议时每算子写optimization_hints_OP_n.csv，另有日志。标准结果不附带请求配置、引擎版本、硬件完整快照、方法来源或真机标志，需要接入层补充。
- DSL Optim._eval_time会写当前目录trace.json，每个候选都会覆盖；应该取最终所选OperatorResult.trace，不能盲读最后候选文件。
- 常见失败结构为error/error_stack，不是成功14字段的补充；批处理捕获异常时可能只有error，CLI对失败返回非零。

## 实跑对照（同形状dtype和硬件，但不同模型实现）

910B1，A=[2048,512]、B=[512,1024]、输出=[2048,1024]，FP16输入/FP32输出，24个AIC。

|项目|理论API|CLI同路工程API|DSL工程流水|
|---|---:|---:|---:|
|总耗时µs|5.904144144144144|10.936681071217901|8.559025912870776|
|CUBE µs|5.904144144144144|6.642162162162163|6.64216216216216|
|MTE2 µs|0.55235435520362|6.832540105999664|6.3295717592592595|
|L2命中字段|0|0.75|0.32653061224489793|
|流水|公开返回无|公开返回无|1736事件|

仅验证本次成功返回和字段含义，不作精度认证。总耗时、缓存、搬运与trace必须同一路径同次运行，不能混拼。

## 接入风险

源码append_result构造局部trace列表却没有写回self.trace，且规则trace实际为dict；多阶段合并流水不能视为已验证。分核与通道时间、空/零值、mem_volume单位、compute_workload单位和tiling标签都要适配后才可直接展示。当前没有统一直接输出功耗、能耗、温度、真机计数器、张量计算结果或完整ISA执行轨迹；不要从现有字段虚构这些能力。
