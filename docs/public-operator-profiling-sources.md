# 公开算子性能与 Profiling 数据来源调研

核查日期：2026-09-28。面向 OpScope 的真机查表、结果比较和任务详情。本文是来源调查，不代表数据已经接入或经过本地真机复测。

## 结论与选用顺序

有公开数据，但“已测好的延迟记录”“测量工具”“模型运行时间线”和“算子定义”提供的信息不同。当前优先候选是 FlashInfer-Trace 的 B200/GB200 延迟记录、KernelBench 的 H100 基线 JSON；希望研究流水与计数器时，Meta HTA 的公开 trace 样例更有针对性。需要任意形状、指定软件栈或其他硬件时，通常仍须用对应工具重新采集。

| 来源 | 实际公开内容 | 主要信息 | 对 OpScope 的用途 |
| --- | --- | --- | --- |
| FlashInfer-Trace | 可下载定义、输入描述、实现与逐条评测 JSONL | shape、dtype、硬件名称、软件版本、耗时、正确性、参考耗时、加速比 | 真机 lookup 第一候选 |
| KernelBench | H100 两种环境的 PyTorch 基线 JSON 与题目代码 | 模块耗时统计、硬件名称、执行模式；形状需关联代码 | 补充 H100 参考实现基线 |
| NVIDIA SOL-ExecBench | 235 个问题定义、3,957 个 workload 条目、执行工具与榜单 | 输入输出、参考实现、容差；本地执行后才有评测结果 | 复用测试配置和验证方法 |
| Hugging Face Kernels | Kernel Hub、benchmark CLI、部分仓库的性能说明 | 运行后产生耗时统计、环境、版本、可选正确性检查 | 采集与版本溯源参考 |
| NVIDIA CUTLASS Profiler | 可运行的矩阵/卷积评测工具 | M/N/K、布局、tile、核函数、延迟、计算与访存吞吐 | 系统采集 GEMM/Conv 数据 |
| NVIDIA NVBench | 通用 CUDA benchmark 工具，可选 CUPTI | 参数轴、CPU/GPU 时间、设备信息、吞吐；可选缓存/DRAM 指标 | 自建采集器参考 |
| DeepSeek DeepGEMM / DeepEP | 性能表、图和可复现 benchmark | GEMM/MoE、通信耗时、吞吐、并行与网络配置 | 专项对照，逐条核对边界 |
| FlashAttention | A100/H100 等平台的性能图与测试代码 | Attention 配置、速度/显存比较 | Attention 专项参考 |
| FlagGems | 多平台汇总表、benchmark 框架 | 算子精度测试状态、dtype 加速比；自行运行可得逐形状延迟 | 广泛算子覆盖与 Ascend 采集线索 |
| Meta HolisticTraceAnalysis（HTA） | 公开 PyTorch trace 样例与分析工具 | 事件时间线、CPU/GPU 关联、kernel 启动配置，部分样例带计数器 | 流水/详情展示与解析验证 |

以上条目都有下文对应的一手来源。Hugging Face 是托管平台；`flashinfer-ai`、`nvidia`、`kernels-community` 分别是不同发布者，不能统一视为 Hugging Face 官方测量。

## 1. FlashInfer-Trace：已核验的逐条测量记录

入口：[数据集](https://huggingface.co/datasets/flashinfer-ai/flashinfer-trace)、[结果格式](https://huggingface.co/datasets/flashinfer-ai/flashinfer-trace/blob/main/trace.md)、[执行工具](https://github.com/flashinfer-ai/flashinfer-bench)。数据集标注 Apache-2.0。

本轮固定版本 `da915083d4c7c5e61aa3005e3d17ae488e0fc71c`。共下载并解析全部 190 个 definition JSON 和 196 个 trace JSONL，无下载失败；没有下载大型张量集合，也没有执行任何候选实现。

| 审计项 | 实际数量 / 内容 |
| --- | --- |
| 定义文件 | 190；同一家族的不同固定参数会分别定义，不是 190 类基础算子 |
| 评测记录 | 7,735；包含多种实现与重复 workload |
| 发布方标为 PASSED 且有延迟 | 5,474，涉及 92 个定义 |
| 其中 baseline PASSED | 1,978，涉及 89 个定义 |
| PASSED 按硬件名称 | NVIDIA B200：5,301；NVIDIA GB200：173 |
| 全部记录按硬件名称 | NVIDIA B200：7,562；NVIDIA GB200：173 |
| 其他状态 | 编译错误 1,262；运行错误 533；数值错误 418；超时 48 |
| PASSED 的 definition + workload UUID + hardware 去重组合 | 1,692；仍不能直接当成 1,692 个唯一 shape |

按实际成功记录划分，覆盖如下。定义目录另含 DSA、GDN、Mamba、RoPE 等，不能因存在定义便声称已有实测结果。

| 家族 | 有 PASSED 的定义数 | PASSED 记录数 | 结果中的硬件 |
| --- | ---: | ---: | --- |
| GEMM | 37 | 2,529 | B200 |
| Paged GQA | 30 | 1,438 | B200、GB200 |
| Ragged GQA | 8 | 286 | B200、GB200 |
| Paged MLA | 2 | 376 | B200 |
| Ragged MLA | 1 | 20 | B200 |
| MoE | 1 | 76 | B200 |
| RMSNorm / Fused Add RMSNorm | 10 | 669 | B200 |
| Sampling | 3 | 80 | GB200 |

字段分散在几类文件中，需要关联：

| 文件 / 对象 | 可取得的信息 |
| --- | --- |
| `definitions/<family>/*.json` | 算子名称、家族、描述、标签、常量/变量轴、输入输出 shape/dtype、参考实现代码 |
| workload | UUID、具体轴值、输入生成描述；部分输入用 safetensors 路径与 tensor key 引用 |
| solution | 实现标识及关联实现资料，区分 baseline 和不同候选实现 |
| evaluation | 状态、日志、时间戳、硬件字符串、Torch/Triton/CUDA 等版本、正确性误差 |
| performance | `latency_ms`、`reference_latency_ms`、`speedup_factor`；失败项不能当成有效测量 |

**实际样例**：`fused_add_rmsnorm_h2048`，B200，hidden_states/residual `[6, 2048]`、weight `[2048]`，BF16，epsilon `1e-6`，baseline 实现。记录的延迟 `0.007666674151122668 ms`，即约 **7.667 μs**；参考延迟约 **55.198 μs**，加速比约 **7.200**。环境为 Torch `2.8.0+cu128`、Triton `3.4.0`、CUDA `12.8`。这是残差加法融合 RMSNorm，不能冒充单独 RMSNorm 或 RMSNormQuant。来源：[定义](https://huggingface.co/datasets/flashinfer-ai/flashinfer-trace/blob/da915083d4c7c5e61aa3005e3d17ae488e0fc71c/definitions/rmsnorm/fused_add_rmsnorm_h2048.json)、[结果](https://huggingface.co/datasets/flashinfer-ai/flashinfer-trace/blob/da915083d4c7c5e61aa3005e3d17ae488e0fc71c/traces/baseline/rmsnorm/fused_add_rmsnorm_h2048.jsonl)。

边界：这些 trace 是评测记录，不是 GPU 活动时间线。没有从已审计记录中得到 L2 命中率、SM 流水、实测 HBM 流量或完整时钟/功耗配置。当前数据不能填到 H100/H200/Ascend 卡片中；文档中的 H100 示例也不构成该版本含 H100 实测的证据。PASSED 是发布方的正确性结论，本轮未复测。

## 2. NVIDIA SOL-ExecBench：定义完整，但公开 HF 数据不是耗时表

入口：[数据集](https://huggingface.co/datasets/nvidia/SOL-ExecBench)、[执行框架](https://github.com/NVIDIA/SOL-ExecBench)、[榜单](https://research.nvidia.com/benchmarks/sol-execbench)。数据集使用 NVIDIA Evaluation Dataset License，不能沿用其他数据集的许可标记。

通过官方 Dataset Viewer API 读取了四个子集的全部 235 行，无单元格截断，并解析其中的 workload JSON：

| 子集 | 问题定义数 | workload 条目数 |
| --- | ---: | ---: |
| FlashInfer-Bench | 26 | 660 |
| L1 | 94 | 1,480 |
| L2 | 82 | 1,299 |
| Quant | 33 | 518 |
| 合计 | 235 | 3,957 |

每行字段：`name`、`description`、`hf_id`、`axes`、`inputs`、`outputs`、`reference`、`custom_inputs_entrypoint`、`workloads`。workload 的实际键仅见 `uuid/axes/inputs/tolerance`，**没有逐条实测 latency 或硬件字段**。因此不能把 3,957 个配置当成 3,957 条真机结果。

范围包括矩阵、卷积、Attention、归一化、融合计算、量化等；一个问题可以是子图，不必是一个基础算子。执行框架能生成含状态、错误、环境、正确性、延迟的 JSONL；参考计时是可选配置。官方运行说明给出 B200 与锁频设置等条件。[结果数据结构](https://github.com/NVIDIA/SOL-ExecBench/blob/main/src/sol_execbench/core/data/trace.py)支持这些字段，但结构存在不代表 HF 数据已填好。

SOL 是分析模型估计的速度上限口径，必须与实际计时区分。本轮未确认榜单完整原始逐 workload 结果的批量下载入口。可以复用其测试定义，不能据此自动补齐 lookup。

## 3. KernelBench：H100 基线结果可下载，需补齐配置关联

来源：[计时结果目录与说明](https://github.com/ScalingIntelligence/KernelBench/tree/main/results/timing)、[计时实现](https://github.com/ScalingIntelligence/KernelBench/blob/main/src/kernelbench/timing.py)。

在版本 `423217d9fda91e0c2d67e4a43bf62f96f6d104f1` 的目录中确认四个结果 JSON：H100_Modal 与 H100_PCIe_LambdaLabs 各有 PyTorch eager、`torch.compile/inductor/default`。全部解析后，每个文件包含 level1 100、level2 100、level3 50，共 **1,000 条有数值 mean 的记录**；对应 250 个问题在四种环境/执行模式组合下的基线，不是 1,000 类算子。

结果键为题目 Python 文件名；内容包括 `mean/std/min/max/num_trials/hardware/device`。单位由计时实现确认为 **ms**。实际 hardware 字符串分别是 `NVIDIA H100 80GB HBM3` 和 `NVIDIA H100 PCIe`。README 声明该批基线使用 Torch `2.5.0+cu124`、CUDA `12.4`、3 次 warmup、100 次试验。

形状、dtype、算法需关联题目及生成配置；结果自身不充分。README 将已发布基线描述为 wall-clock，而当前工具支持 CUDA event 等多种计时方式，导入时应记录来源声明，不能用当前默认参数反推旧结果。level2/3 包含融合片段和完整模块，不能统一当成单 kernel 延迟。README 列出的其他 GPU 不等于当前目录已经提供它们的 JSON。

## 4. Hugging Face Kernels：适合建立可追溯采集流程

来源：[benchmark CLI 文档](https://huggingface.co/docs/kernels/cli-benchmark)、[实际 JSON 序列化实现](https://github.com/huggingface/kernels/blob/5782e1a09d88300d0131aa963e53b4b18d768dcb/kernels/src/kernels/cli/benchmark.py)。本轮查看的是 main 文档，可能领先稳定发布版本。

CLI 运行指定版本的 kernel 仓库和 `benchmarks/benchmark*.py`，可以输出 JSON。已核对的 JSON 字段包含 workload 名称、均值/标准差/最小最大值/四分位数/异常值数/次数、可选 `verified`、GPU、后端、PyTorch、OS、CPU，以及 kernel SHA、benchmark 脚本路径和 SHA。

**终端输出与 JSON 不完全相同**：终端可显示参考耗时和加速比，但本轮核对的 `to_payload()` 没有序列化 `ref_mean_ms` 或 speedup 字段。不能因为截图里有，就承诺 JSON 可以直接导入。shape/dtype 往往在 benchmark 的 setup 中，也不保证平铺在结果里。

平台可以找到具体算子的公开性能说明，但本轮未确认一个由 Hugging Face 统一提供、覆盖所有 kernel 与硬件的完整结果数据库。适合作为未来采集协议参考；统计字段可以保留在来源元数据，不代表要恢复本项目已移除的分布类 UI。

## 5. NVIDIA CUTLASS Profiler / NVBench：工具能产出数据，仍需硬件运行

### CUTLASS Profiler

来源：[官方 Profiler 文档](https://docs.nvidia.com/cutlass/latest/media/docs/cpp/profiler.html)。

针对 GEMM/卷积扫描参数并导出 CSV，可包含：provider、operation、kernel、验证状态，M/N/K/batch、alpha/beta、输入输出/累加精度与布局，CTA/warp/instruction tile、pipeline stages、split-K，以及运行时间、FLOPs、Bytes、GFLOP/s、GiB/s。

其中吞吐通常由工作量和运行时间推导；`Bytes / time` 不是 DRAM 性能计数器。kernel 支持的架构范围也不等于实际 GPU 型号；采集时需额外保存完整设备与软件环境。文档示例 CSV 是格式参考，不能直接当成覆盖本项目硬件的真机库。

### NVBench

来源：[官方仓库](https://github.com/NVIDIA/nvbench)、[输出选项](https://github.com/NVIDIA/nvbench/blob/main/docs/cli_help.md)、[CUPTI 指标实现](https://github.com/NVIDIA/nvbench/blob/410dcdd21c9b48191ecb3d3d77060b1bf4ac6244/nvbench/detail/measure_cupti.cu)。

通用 CUDA benchmark 支持参数轴、冷缓存/批量计时、CPU/GPU 时间、采样次数与噪声、吞吐和设备属性，可输出 JSON/CSV/Markdown。启用相应能力后，CUPTI 还能采集 DRAM 吞吐占持续峰值比例、global load/store efficiency、L1/L2 命中率。

必须区分普通吞吐计算与启用 CUPTI 后的计数器字段。工具能力不代表默认输出完整硬件指标，更不代表已有覆盖所有算子的公共测量表。

## 6. DeepSeek：GEMM 与 MoE/通信专项资料

来源：[DeepGEMM](https://github.com/deepseek-ai/DeepGEMM)、[FP8/FP4 benchmark](https://github.com/deepseek-ai/DeepGEMM/blob/78b69000794d0937b47ae3387eff7663410264d1/tests/test_fp8_fp4.py)、[Mega MoE 性能表](https://github.com/deepseek-ai/DeepGEMM/pull/316)、[DeepEP](https://github.com/deepseek-ai/DeepEP)、[DeepEP 旧版详细性能](https://github.com/deepseek-ai/DeepEP/blob/main/docs/legacy.md)。

| 项目 | 配置与结果 | 必须保留的边界 |
| --- | --- | --- |
| DeepGEMM | GEMM/分组 GEMM 的 M/N/K、group、布局、量化模式、输出精度、耗时 μs、TFLOPS、GB/s、部分 cuBLAS 比较 | 与具体实现及测量范围绑定；量化/布局准备是否计入须查 benchmark，不能全视作端到端 |
| Mega MoE 表 | 模型维度、experts/top-k、每 rank tokens、EP8、时间、计算/访存/互连吞吐和相对旧实现加速比 | 表中结果跨 8 ranks 平均；不是普通单卡矩阵乘，具体硬件身份仍须另行确认 |
| DeepEP | dispatch/combine、token/hidden/top-k、精度、SM 架构、网卡、并行拓扑、使用 SM 数、带宽；旧版还列延迟 | 多卡通信结果，依赖 NIC、互连与分组；README 特别说明逻辑带宽包含本地 rank 数据 |

DeepGEMM 测试中的 TFLOPS、GB/s 使用计算量/字节数除以耗时得到，不应标成硬件计数器。性能图、表适合特定点对照；没有据此认定存在任意 shape 的完整规范化 JSON 数据库。

## 7. FlashAttention：先区分 forward、backward 和总计

来源：[官方仓库与性能说明](https://github.com/Dao-AILab/flash-attention)。

公开说明含 A100/H100 性能比较、序列长度、head dimension、batch 等条件、相对速度和显存节省，并提供 benchmark 代码。部分图比较的是 forward + backward 合计。它不能直接与单独 forward 或 decode kernel 的延迟混用；图上的加速比也不能在缺少基准耗时时转成绝对 μs。

导入前必须明确 FlashAttention 版本、causal、head 数/dim、Q/KV 长度、batch、dtype 和计时阶段；只凭名称“FlashAttention”无法匹配。官方图表不等于已发布完整 Nsight 报告或每个 shape 的原始测量记录。

## 8. FlagGems：多平台公开汇总，Ascend 的重要线索

来源：[公开结果页](https://docs.flagos.io/projects/FlagGems/en/latest/performance/results.html)、[benchmark 源码](https://github.com/flagos-ai/FlagGems/blob/master/benchmark/base.py)、[汇总口径](https://github.com/flagos-ai/FlagGems/blob/master/docs/content/en/performance/overview.md)、[表格字段](https://github.com/flagos-ai/FlagGems/blob/7f3d009175a626183d0dec0228ac26f229db19f6/docs/static/js/benchmark.js)。

公开页面可切换 ASCEND、HOPPER、HYGON、ILUVATAR、METAX、MTHREADS、THEAD。表格含 compiler、timestamp、operator、accuracy、通过/失败/跳过数量、性能测试状态、FP16/FP32/BF16、备注。已由表格 JS 确认精度列是 **speedup 加速比**，不是毫秒；概览图说明是对各 shape 的加速比进行平均。

自行运行 benchmark 可以获得输入配置、基线延迟、当前实现延迟、加速比，部分算子还计算 GB/s/TFLOPS。其数据库后端说明描述用户自建结果存储能力，不能据此假定有可公开查询的全量数据库。

本轮直接抓取结果 HTML 遇到 403，已改为官方索引和仓库源码核对结构；未获取全平台底层逐 shape 记录。尚未从这些汇总材料确认 Ascend910B1/910B4 的完整型号身份和逐形状绝对延迟，因此暂不能填入这两个型号的 lookup。

## 9. Meta HTA：真正的时间线与部分计数器样例

来源：[官方仓库](https://github.com/facebookresearch/HolisticTraceAnalysis)、[公开样例目录](https://github.com/facebookresearch/HolisticTraceAnalysis/tree/0502deb4ab98b5d30f747b27847b232ce873a8e3/tests/data)、[CUPTI 采集示例](https://github.com/facebookresearch/HolisticTraceAnalysis/blob/main/examples/cupti_profiler_demo.py)。这是 Meta 的分析工具与测试样例，不能称为 Llama 全算子的标准性能库。

本轮实际下载并解压两个公开文件：

| 文件 | 实际包含 |
| --- | --- |
| `tests/data/execution_trace/benchmark_simple_add_trace.json.gz` | `deviceProperties`、CPU op、CUDA API、关联事件、4 个 GPU kernel；事件名称、开始时间、持续时间、线程/进程等 |
| `tests/data/cupti_profiler/benchmark_result_924719_1679055439_trace.json.gz` | 77 个 `cuda_profiler_range`；九种 FP16/FP32/FP64 add/mul/fma SASS 线程指令计数 |

两份样例的设备名称均为 `NVIDIA A100-PG509-200`。普通 kernel 事件还包含 device/context/stream、grid/block、寄存器/线程、shared memory、blocks/warps per SM、correlation 与 **estimated achieved occupancy**。这个 estimated 字段不能冒充另行测出的 occupancy 指标。

这些样例可用于开发时间线、调用关联和计数器展示，但不是全面计数器集合：上述 CUPTI 文件未包含 DRAM 字节计数；当前采集示例代码能请求它，也不能反推历史样例已有它。shape/dtype 也并非每个事件都有，可能需要关联 execution trace/源程序。profiling 的采集开销和 replay 会影响耗时，不能直接把样例的所有 duration 当作稳态 benchmark 结果。

## 10. 如果需要完整 profiling：对应工具与公开数据要分开

| 需求 | 对应一手工具 | 可以采集 / 分析的信息 |
| --- | --- | --- |
| NVIDIA 单 kernel 性能原因 | [Nsight Compute](https://docs.nvidia.com/nsight-compute/ProfilingGuide/index.html) | 计算/访存吞吐、缓存、occupancy、warp stalls、launch 资源、源码/指令分析；实际字段依 GPU 和选用 sections |
| CPU/GPU 调度与重叠 | [Nsight Systems](https://docs.nvidia.com/nsight-systems/UserGuide/index.html) | CUDA API、kernel、memcpy、NVTX、stream 和时间关联，可导出供分析 |
| Ascend 算子 profiling | [Ascend 官方说明](https://github.com/Ascend/triton-ascend/blob/main/docs/zh/debug_guide/profiling.md) | 提供 msprof 等操作示例；真机采样与 simulator 输出必须按命令和产物区分 |
| 计算/通信依赖图 | [MLCommons Chakra](https://github.com/mlcommons/chakra/blob/main/USER_GUIDE.md) | 连接 host/device execution trace，编码依赖，转换为图/模拟器输入；不是硬件实测结果库 |

本轮没有确认这些厂商发布了能覆盖本项目全部算子、全部硬件、全部形状的完整 profiling 数据。也没有找到可直接替代 Ascend910B1/B4 规格和 TileSim 全部校准表的公开集合；这是本轮调查范围内的结论，不代表其他渠道绝无资料。

## 对 OpScope 的接入建议（尚未实施）

1. **先做 FlashInfer-Trace 的 baseline lookup。** 只导入发布方 PASS 且有有效延迟的记录，关联 definition/workload/solution，保留出处与版本。B200/GB200 必须分别映射；不能借给其他型号。
2. **再补 KernelBench H100 基线。** 先匹配题目算法、输入和精度；区分 eager/compile、基础算子/融合模块，以及计时范围。不能仅按 MatMul/RMSNorm 名称匹配。
3. **流水展示用 HTA 的真实 trace 验证解析。** benchmark 标量结果与 timeline 分开存储；缺事件/计数器时保留缺失，不从耗时造流水。
4. **其余来源作为专项参考或采集工具。** SOL/HF Kernels/CUTLASS/NVBench 提供配置与采集能力；DeepSeek、FlashAttention、FlagGems 的图表先保留原始比较范围，不能自动转成任意输入的真机结果。

最少匹配与溯源信息：算子语义/融合边界，所有输入输出 shape/dtype，layout/stride/转置，算子专有参数（如 epsilon、causal、量化 scale、KV page、分组），硬件精确身份，实现/库版本，计时范围与缓存/预热约定，来源 URL/版本/记录 ID，状态和单位。未提供的属性记为未知；不知道是否可比时不直接排序或计算误差。

公开数据最容易补的是**特定配置的总耗时、参考耗时、加速比**。吞吐可以在确认操作数/字节口径后推导并注明来源；硬件计数器和流水须有真实原始数据。它们可以作为建模校验目标，**不会自动补全 TileSim 的算法、带宽表或指令周期表**。

## 核查证据与限制

本轮统计见 [机器可读审计摘要](research/public-profiling-audit-2026-09-28.json)，保留版本、路径、数量、状态与字段列表。FlashInfer 全部定义和 trace 使用固定版本；SOL 的 235 行来自调查当日公开 Viewer API，该 API 未固定 revision，摘要中另列目录盘点时的版本。KernelBench 的四个结果文件全部解析；Meta 两份样例实际解压核查。

未运行 GPU/NPU benchmark，未验证外部发布数据的实际测量过程，未导入应用；没有为调研安装新依赖或修改运行代码。工具文档、样例文件、发布时间不同，不把当前代码支持能力倒推为历史记录已有字段。
