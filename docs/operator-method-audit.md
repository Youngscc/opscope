# 全目录算子 × 方法 × 硬件实跑审计（2026-09-23）

本篇保留适配前的基线证据；其中“当前环境未修复”“未适配”的措辞均指首次审计时点。后续完成的适配和项目 `.venv` 复验见[算子适配扩展](operator-adaptation-plan.md)及[新版原始结果](audits/2026-09-23-adapted/summary.json)。

## 结论

**不能把不能运行都归因于 modeling 缺数据。** 本轮分出了：本机依赖加载故障、OpScope 只迁移了部分执行器、输入契约未表达、TileSim 自身硬件参数不全、上游资产/单算子路径缺项，以及没有同边界模型的复合算子。

- 当前界面 94 个算子组，保留 100 个输入模板；19 个硬件入口 × 5 个方法，共检查 **9,500 个组合**。硬件入口含示例别名和 Server/POD，不能理解为 19 种独立芯片。
- 使用目录默认 shape/dtype，未知维度不填 1，BF16 不偷换 FP16。原始运行环境是项目 `.venv`（Python 3.12.14、SciPy 1.15.3、msopmodeling 1.0.9）。
- 门槛允许的 **413 个组合实际执行**：Roofline 204/204 成功；TileSim 63/209 成功，146 个失败全部为同一个 SciPy 动态库加载错误。
- 用已有 Python 3.11.16 / SciPy 1.15.3 环境作独立对照，**TileSim 209/209 全成功**。两个环境 TileSim Python 源码 hash 相同，第一轮成功的 63 个时延逐个完全相等。**没有修改当前环境，也没有修改模型/放宽支持范围。**
- 另外执行上游单算子 Roofline 对照和明确改输入的 70 个补充检查。补充结果不混入默认覆盖率。

## 默认组合结果

| 方法 | 当前环境成功 | 当前环境执行失败 | 输入未填全 | 目录排除 | 前置不支持/未接入 | Python 3.11 对照成功 |
|---|---:|---:|---:|---:|---:|---:|
| Roofline | 204 | 0 | 342 | 114 | 1,240 | 204 |
| TileSim | 63 | 146 | 342 | 114 | 1,235 | 209 |
| Profiling | 0 | 0 | 342 | 114 | 1,444 | 0 |
| 方法3 | 0 | 0 | 342 | 114 | 1,444 | 0 |
| 方法4 | 0 | 0 | 342 | 114 | 1,444 | 0 |

每行 1,900 个组合；每个组合只记录最先遇到的阻塞，因此多重原因不会重复计数。Profiling、方法3/4 的所有组合都没有实际执行器，表中的输入/目录阻塞是更早的校验结果。方法3/4 的示例数据不属于执行结果。

Roofline 成功覆盖 12 个模板（含 demo MatMul，实际 11 个基础算子）×17 个硬件入口。TileSim 已登记 28 个模板，其中 FlashAttentionScore 默认维度缺失，其余 27 个至少能在一个硬件配置上执行。27×19=513 中，294 个因 GPU BF16 参数缺失被挡住，10 个 FP16 MatMul 因 GB200/R200 带宽缺失被挡住，剩下 209 个执行。其他 49 个输入完整、非通信模板未适配 TileSim。

## 缺什么、由谁补

### 1. 当前环境故障：不是缺算子数据

146 个失败全部经过 `tilesim_worker.run_model → op_latency_predict_engineering → scipy.interpolate → scipy.sparse.linalg._propack._spropack`，报：

```text
ImportError: dlopen(..._spropack.cpython-312-darwin.so...)
section '__DATA/__thread_bss' has a zero-fill section type, but offset field is not zero
```

只有成本模型工程路径触发该依赖；DSL 工程/理论和成本模型理论路径成功。对照环境中 146 个成本模型工程组合全部通过。例如 LayerNorm 在 910B1/B4 分别是 **54.266292 / 72.481067 μs**。因此这批 LayerNorm 等失败不能判断为 modeling 不支持。

责任：本机运行环境/二进制依赖兼容性。推荐先验证 Python 3.11 的独立环境，再决定修复主环境；不能凭此断言所有 Python 3.12 或 WSL 都失败。当前能力探测没有导入完整成本模型路径，会出现“TileSim 可用”但工程成本模型失败的情况，后续应补探测。依赖入口在 [pyproject.toml](../pyproject.toml)、[uv.lock](../uv.lock)，调用入口在 [tilesim_worker.py](../opscope/evaluation/tilesim_worker.py)。

### 2. Roofline：明显存在我们未迁入的能力，也有上游真实缺项

当前 [evaluation_contract.py](../opscope/evaluation/evaluation_contract.py) 的 `supported` 只开放 demo 与 11 个基础模板；[bundled_roofline.py](../opscope/evaluation/bundled_roofline.py) 也只迁移这些公式。`infer:*` 即使数学上接近基础算子，也没有进入这个后端。这是 **OpScope 适配缺口**。

只读调用原仓库 `backend/web/services/infer/op_sim.py` 的纯 `_build_model/_build_context` 与 Kepler `execute_model`，没有启动 Web/数据库、没有读取任务数据：

- 82 个非通信 infer 模板中，18 个默认输入不完整；64 个可以提交。
- 64 个各在 Adevice03_Server、H200_Server 执行：**61×2=122 个返回结果，3×2=6 个失败**。
- 3 个上游失败：`QuantLightningIndexer` 输出缺 `sparse_count`；`SparseIndexSelect` 输出缺 `index_topk`；`MoeGatingTopK` 返回 `bound_type=none`，按原 `_simulate` 判定失败。后者额外直接调用节点，确认继承的 `layers/moe.py:104` 把二维 gate score 解包为 `B, S, D`，抛出 `expected 3, got 2`；见[异常证据](audits/2026-09-23-operator-method/upstream-error-diagnostic.json)。这些不是我们的 Roofline 适配器造成。
- 61 个返回结果不等于 61 个完整、准确模型：其中 50 个报告正 FLOPs，11 个报告零 FLOPs，包括 START/END、搬运类以及待核对的 TorchCos/TorchSin/MoEGate。START/END 时延为 0，是流程节点；Compressor Epilog 默认 `compress_ratio=1` 使 factor=0。不要把合法零、控制节点与缺失公式混为一谈。

迁移工作需要表达输出/公式上下文、精度/计算单元、融合边界，并用上游数值做对照，不能简单放开白名单。原始结果见 [upstream-roofline.jsonl](audits/2026-09-23-operator-method/upstream-roofline.jsonl)。本轮验证的是单算子基准计算，不含原 UI 的多尺度 sweep 和数据库任务流程。

### 3. TileSim：有模型但我们尚未接入

当前映射在 [tilesim_contract.py](../opscope/evaluation/tilesim_contract.py) 的 `OPERATOR_KINDS`，请求转换在 [tilesim_adapters.py](../opscope/evaluation/tilesim_adapters.py)。以下不能笼统说“TileSim 没有”：

| 当前模板/算子族 | TileSim 1.0.9 中存在的候选 | 缺项/责任 |
|---|---|---|
| MatMul、Linear、Column/RowParallelLinear | MatMul / Linear 基础模型 | 我们未做 batch 展平、权重方向、分片契约转换 |
| TorchSum | 理论 ReduceSum | 我们未接 reduce_axis/keepdim 和输出映射 |
| Transpose、Cumsum、GatherV2 | 理论 Transpose、工程 Cumsum/Gather | axis/perm 实际值未进入配置；部分可由固定模板确定，但需显式约束 |
| ScatterNdUpdate | 同名理论模型 | FP8、索引布局与输出契约未适配/验证 |
| GroupedMatmul | 工程 GroupedMatmul | 缺 group_list 实际分组值与布局 |
| QuantBatchMatmulV3、DynamicQuantV2 | 量化工程模型/候选 | 量化 scale/offset、dtype 和完整输入输出契约 |
| FusedInferAttentionScore、SparseFlashAttention | 同名工程模型 | 缺默认维度、cache/layout/sparse 参数及请求转换 |
| SparseAttentionSharedKV | SparseAttnSharedkv | layout、tail_dim、KV窗口/稀疏索引与实际边界 |
| LightningIndexer、Compressor | 工程 LightningIndexer、理论 Compressor | 扩展参数、额外张量、布局与融合边界未接 |
| Rope、MHC、融合量化/MLA | 有若干部件或近似模型 | 不能仅按名字等同，需语义核对或组合模型 |

注册清单来自实际包源码，见 [tilesim-model-inventory.json](audits/2026-09-23-operator-method/tilesim-model-inventory.json)。**候选存在是源码证据，不是端到端运行/精度认证。** 当前通用提示“未提供与当前算子边界等价且已验证的模型”混合了未适配和无同边界模型，建议后续拆分。

已适配结果也保留简化假设：LayerNorm 补零 beta、LayerNormV4 补单位 gamma/零 beta，GemmaRmsNorm 借普通 RMSNorm 模型，Cast 固定转 FP32，Embedding 固定 axis=0，MoeGatingTopK 固定 top_k=8。相应说明已在执行结果的 `model_note` 中保留；本轮成功数不表示这些参数已可任意配置或融合边界已通过真机认证。

没有找到可直接等价调用的同边界模型的例子包括 ChunkGatedDeltaRule、CausalConv1d、DynamicMxQuant、FusedGdnGating、Engram/PLE/QSA、完整 vision block 和融合 SwiGLU MLP 等。不能仅补几个硬件数值就让它们跑通；需补模型/拆解并估算融合与中间访存。这里结论限定于当前 1.0.9 包，不能外推到其他版本。

### 4. 硬件：部分确实是现有来源缺规格

| 硬件/组合 | 缺项 | 来源及责任 |
|---|---|---|
| 910B1、910B4 的 Roofline | 分精度矩阵/向量峰值、整卡 HBM 带宽等完整规格 | 原 modeling 公共硬件和我们快照中都无可验证的同型号规格；TileSim 的分核/分层参数不能冒充整卡 Roofline |
| H200/GB200/R200 TileSim 的 BF16 | cube_throughput/cube_repeat_cycles、vector 指令吞吐等 BF16 参数 | 发行包 `core/config/arc_config/<型号>/<型号>.yaml` 缺失；H100/B300 借 H200，也继承该限制 |
| GB200/R200 的 MatMul 理论路径 | L0C→L2 带宽键 | 发行包相应 bandwidth CSV 缺失；当前有前置拦截 |
| GB200/R200 的 FA 工程路径 | UB、L0A/L0B/L0C 存储配置 | 发行包 YAML 不完整；当前有前置拦截 |
| GB200/R200 的 BMM、TransposeBatchMatMul（FP16 对照） | GM→L1、20核、normal 对应带宽键 | 实际 API 报缺 CSV 项；我们的前置检查漏拦截 |
| GB200/R200 的 Cast、Sigmoid、SwiGlu（FP16 对照） | L0C→L2、20核、normal 对应带宽键 | 理论后端加载硬件配置时报错；即使是向量算子也会触发，我们的检查漏拦截 |

补充实验明确把 22 个 BF16 模板改成 FP16，在 H200/GB200/R200 上检查 66 个组合：45 成功、10 实际失败、8 前置阻塞、3 输入仍缺维度。证明不能认为“改 FP16 就都能运行”。10 个失败的完整 key 和堆栈见 [supplemental.jsonl](audits/2026-09-23-operator-method/supplemental.jsonl)。

硬件路径：本项目 [roofline_hardware.json](../opscope/evaluation/data/roofline_hardware.json)；TileSim 在仓库随附 [msopmodeling wheel](../vendor/msopmodeling/msopmodeling-1.0.9-py3-none-any.whl) 内 `tilesim/core/config/arc_config/{910B1,910B4,H200,GB200,R200}/`，安装后位于 `.venv/lib/pythonX.Y/site-packages/tilesim/`。算子模型在 `ops/{engineering_model,theoretical_model}/`、`core/backend/engineering_costmodel/op_model/`，API 注册在 `api/operator_api/`。

Adevice03→910B4、H100/B300→H200 当前是明确标记的借用配置，成功返回不代表各型号得到独立校准或硬件认证；Server/POD 条目也不等于多卡算子仿真。

### 5. 输入默认值和范围限制

18 个非通信模板默认维度为 null；在 modeling 的 `_DIM_DEFAULTS` 中相应变量也没有值。**算子资产存在，不代表离开模型上下文就有完整运行配置。** 原目录遇到未知变量会回填 1，我们保留 null，不能因此说原系统支持任意真实形状。

FlashAttentionScore 补齐 head_dim=128 后，原形状 `[1,32,2048,128]` 仍超过我们 80,000 事件上限；这是本地保护限制，不是 TileSim 缺模型。明确缩到 `[1,8,512,128]` 后，910B1/B4 为 **13.977425 / 18.839385 μs**，各 1,328 个事件。4 个 FA 补充检查与上面的 66 个精度对照一起构成 70 个补充项（47 成功、10 失败、10 前置阻塞、3 输入不全）。

通信 6 个模板按原单算子入口排除；需要拓扑、rank/group、消息尺寸和通信模型，不能直接按计算算子评估。START/END 当前却仍可出现在算子目录，属于目录清理项。

## 逐模板清单

正常环境下的默认硬件覆盖如下；条目数包含别名，不是独立芯片数。

| 硬件入口组 | 条目数 | 每入口 Roofline 成功模板 | 每入口 TileSim 成功模板 |
|---|---:|---:|---:|
| Adevice03 / ascend | 3 | 12 | 27 |
| H100、H200、B300（H100/B300 借 H200） | 9 | 12 | 6 |
| B200、R200 | 5 | 12 | 4 |
| 910B1、910B4 | 2 | 0 | 27 |

下表 R/T 为成功硬件入口数，分母均为19；T 当前→对照表示 Python3.12→3.11，**对照不代表当前环境已修复**。上游列只查 infer 单算子；同一状态已在两种硬件上复现。具体失败硬件、完整输入和最先阻塞原因以 CSV/JSON 为准。

| 模板 ID | R 成功 | T 当前→对照 | modeling 单算子对照 | TileSim 缺项/说明 |
|---|---:|---:|---|---|
| `demo:matmul` | 17 | 14→14 | —（非 infer / 排除） | 已适配；默认成功范围见硬件表。GPU BF16 和模型假设仍受限制。 |
| `train:matmul` | 17 | 5→5 | —（非 infer / 排除） | 已适配；默认成功范围见硬件表。GPU BF16 和模型假设仍受限制。 |
| `train:linear` | 17 | 5→5 | —（非 infer / 排除） | 已适配；默认成功范围见硬件表。GPU BF16 和模型假设仍受限制。 |
| `train:bmm` | 17 | 0→5 | —（非 infer / 排除） | 已适配；默认成功范围见硬件表。GPU BF16 和模型假设仍受限制。 |
| `train:flash_attention` | 17 | 5→5 | —（非 infer / 排除） | 已适配；默认成功范围见硬件表。GPU BF16 和模型假设仍受限制。 |
| `train:layernorm` | 17 | 0→5 | —（非 infer / 排除） | 已适配；默认成功范围见硬件表。GPU BF16 和模型假设仍受限制。 |
| `train:rms_norm` | 17 | 0→5 | —（非 infer / 排除） | 已适配；默认成功范围见硬件表。GPU BF16 和模型假设仍受限制。 |
| `train:swiglu` | 17 | 0→0 | —（非 infer / 排除） | 融合三矩阵 MLP；仅有同名 SwiGLU 激活，需组合模型/融合成本，不能直接替代。 |
| `train:embedding` | 17 | 0→5 | —（非 infer / 排除） | 已适配；默认成功范围见硬件表。GPU BF16 和模型假设仍受限制。 |
| `train:silu` | 17 | 0→5 | —（非 infer / 排除） | 已适配；默认成功范围见硬件表。GPU BF16 和模型假设仍受限制。 |
| `train:gelu` | 17 | 0→5 | —（非 infer / 排除） | 已适配；默认成功范围见硬件表。GPU BF16 和模型假设仍受限制。 |
| `train:softmax` | 17 | 0→5 | —（非 infer / 排除） | 已适配；默认成功范围见硬件表。GPU BF16 和模型假设仍受限制。 |
| `infer:ChunkGatedDeltaRule` | 0 | 0→0 | 输入不全 | 未找到已验证的同边界可调用模型；需补模型/组合适配，不能只改名称。 输入还缺：key_head_dim, num_key_heads, num_value_heads, value_head_dim。 |
| `infer:FlashAttentionScore` | 0 | 0→0 | 输入不全 | 已接 DSL；缺 qk_head_dim/qk_nope_head_dim；补 128 后默认规模仍超 8 万事件限制。 输入还缺：qk_head_dim, qk_nope_head_dim。 |
| `infer:FusedInferAttentionScore` | 0 | 0→0 | 输入不全 | 同名工程模型已有；缺 head_dim/cache/block/prefix/rope 维度及对应参数适配。 输入还缺：max_num_blocks, qk_head_dim, qk_nope_head_dim, qk_rope_head_dim。 |
| `infer:KvQuantSparseFlashAttention` | 0 | 0→0 | 输入不全 | SparseFlashAttention 有 FP8 分支候选；补稀疏/量化上下文，尚未验证等价。 输入还缺：index_topk, kv_lora_rank, qk_rope_head_dim。 |
| `infer:SparseFlashAttention` | 0 | 0→0 | 输入不全 | 工程 SparseFlashAttention 已有；补 index_topk、索引/布局并适配。 输入还缺：index_topk。 |
| `infer:MatMulV3` | 0 | 5→5 | 返回结果 | 已适配；默认成功范围见硬件表。GPU BF16 和模型假设仍受限制。 |
| `infer:QuantBatchMatmulV3` | 0 | 0→0 | 返回结果 | 工程模型存在；补量化 scale/offset 等完整输入、精度与布局适配。 |
| `infer:TransposeBatchMatMul` | 0 | 0→5 | 返回结果 | 已适配；默认成功范围见硬件表。GPU BF16 和模型假设仍受限制。 |
| `infer:AddRmsNorm` | 0 | 0→5 | 返回结果 | 已适配；默认成功范围见硬件表。GPU BF16 和模型假设仍受限制。 |
| `infer:AddRmsNormBias` | 0 | 0→0 | 返回结果 | 有 RmsNorm/AddRmsNorm 部件；额外 bias/gate/quant 融合边界未建适配，未发现可直接替代的同边界注册模型。 |
| `infer:Cast` | 0 | 5→5 | 返回结果 | 已适配；默认成功范围见硬件表。GPU BF16 和模型假设仍受限制。 |
| `infer:CausalConv1d` | 0 | 0→0 | 输入不全 | 未找到已验证的同边界可调用模型；需补模型/组合适配，不能只改名称。 输入还缺：num_cache_lines, state_len。 |
| `infer:Cumsum` | 0 | 0→0 | 返回结果 | 已有 工程 Cumsum；当前配置无 axis 实际值，需要补语义和适配。 |
| `infer:DynamicMxQuant` | 0 | 0→0 | 返回结果 | 未找到已验证的同边界可调用模型；需补模型/组合适配，不能只改名称。 |
| `infer:DynamicQuantV2` | 0 | 0→0 | 返回结果 | 只有 DynamicQuant 候选；核对 V2 多输入/输出和量化选项，不能仅改名。 |
| `infer:FusedGdnGating` | 0 | 0→0 | 输入不全 | 未找到已验证的同边界可调用模型；需补模型/组合适配，不能只改名称。 输入还缺：num_heads。 |
| `infer:GatherV2` | 0 | 0→0 | 返回结果，FLOPs=0 | 已有 工程 Gather；当前配置无 axis 实际值，需要补语义和适配。 |
| `infer:GemmaRmsNorm` | 0 | 0→5 | 返回结果 | 已适配；默认成功范围见硬件表。GPU BF16 和模型假设仍受限制。 |
| `infer:LayerNormV4` | 0 | 0→19 | 返回结果 | 已适配；默认成功范围见硬件表。GPU BF16 和模型假设仍受限制。 |
| `infer:Mul` | 0 | 0→5 | 返回结果 | 已适配；默认成功范围见硬件表。GPU BF16 和模型假设仍受限制。 |
| `infer:RmsNorm` | 0 | 0→5 | 返回结果 | 已适配；默认成功范围见硬件表。GPU BF16 和模型假设仍受限制。 |
| `infer:ScatterNdUpdate` | 0 | 0→0 | 返回结果，FLOPs=0 | 理论 ScatterNdUpdate 已有；当前资产为 FP8+索引，需精度/索引布局校验，不能把 FP8 当 INT8。 |
| `infer:Sigmoid` | 0 | 5→5 | 返回结果 | 已适配；默认成功范围见硬件表。GPU BF16 和模型假设仍受限制。 |
| `infer:SwiGlu` | 0 | 5→5 | 返回结果 | 已适配；默认成功范围见硬件表。GPU BF16 和模型假设仍受限制。 |
| `infer:SwiGluQuant` | 0 | 0→0 | 返回结果 | 有 DequantSwigluQuant 部件候选；反量化/分组/量化输入和输出边界不同，未验证完整等价。 |
| `infer:SwigluGroupQuant` | 0 | 0→0 | 输入不全 | 有 DequantSwigluQuant 部件候选；反量化/分组/量化输入和输出边界不同，未验证完整等价。 输入还缺：routed_tokens_per_rank。 |
| `infer:Transpose` | 0 | 0→0 | 返回结果，FLOPs=0 | 已有 理论 Transpose；缺 axis/perm 实际值和适配。Transpose 理论模型只按元素量估搬运，不能验证置换差异。 |
| `infer:GroupedMatmul` | 0 | 0→0 | 返回结果 | GroupedMatmul 工程模型存在；缺 group_list 实际分组值和布局适配。 |
| `infer:GroupedMatmulSwigluQuantV2` | 0 | 0→0 | 返回结果 | 融合分组 GEMM+激活+量化；仅有 GroupedMatmul/DequantSwigluQuant 部件，完整边界未适配。 |
| `infer:MlaPrologV3` | 0 | 0→0 | 输入不全 | 有 MLA/Compressor 部件候选；Prolog/Epilog 的完整输入、阶段/量化和融合边界尚未适配，不能用整个 MLA 代替。 输入还缺：kv_lora_rank, qk_nope_head_dim, qk_rope_head_dim。 |
| `infer:QuantLightningIndexer` | 0 | 0→0 | 上游失败 | 有 LightningIndexer 候选，量化版需核对；上游单算子输出还缺 sparse_count。 |
| `infer:MoeGatingTopK` | 0 | 0→5 | 上游失败 | 已适配；默认成功范围见硬件表。GPU BF16 和模型假设仍受限制。 |
| `infer:MoeDistributeCombineV3` | 0 | 0→0 | —（非 infer / 排除） | 通信：单算子目录排除，需要独立通信契约。 输入还缺：ep_size。 |
| `infer:MoeDistributeDispatchV3` | 0 | 0→0 | —（非 infer / 排除） | 通信：单算子目录排除，需要独立通信契约。 |
| `infer:SituAndMul` | 0 | 0→0 | 返回结果 | 可考虑 Swiglu/Swish+Mul；先核对门控拆分、双输入和融合输出边界。 |
| `infer:SparseAttentionSharedKV` | 0 | 0→0 | 返回结果 | 工程 SparseAttnSharedkv 已有；需要 layout/tail_dim、KV窗口、稀疏索引等契约。 |
| `infer:AllGather` | 0 | 0→0 | —（非 infer / 排除） | 通信：单算子目录排除，需要独立通信契约。 |
| `infer:AllReduce` | 0 | 0→0 | —（非 infer / 排除） | 通信：单算子目录排除，需要独立通信契约。 |
| `infer:MoECombine` | 0 | 0→0 | —（非 infer / 排除） | 通信：单算子目录排除，需要独立通信契约。 |
| `infer:MoEDispatch` | 0 | 0→0 | —（非 infer / 排除） | 通信：单算子目录排除，需要独立通信契约。 |
| `infer:Embedding` | 0 | 0→0 | 返回结果，FLOPs=0 | Gather 候选存在，但该资产只有整数 x/indices，没有浮点权重表；需修正模板，不可直接复用 train:embedding。 |
| `infer:EngramGate` | 0 | 0→0 | 输入不全 | 未找到已验证的同边界可调用模型；需补模型/组合适配，不能只改名称。 输入还缺：engram_head_dim, engram_max_ngram_size, engram_n_heads。 |
| `infer:EngramLookup` | 0 | 0→0 | 输入不全 | 未找到已验证的同边界可调用模型；需补模型/组合适配，不能只改名称。 输入还缺：engram_head_dim, engram_num_embeddings。 |
| `infer:END` | 0 | 0→0 | 返回结果，FLOPs=0 | 流程标记，不是需要性能评估的计算算子；应从可评估目录中剔除。 |
| `infer:START` | 0 | 0→0 | 返回结果，FLOPs=0 | 流程标记，不是需要性能评估的计算算子；应从可评估目录中剔除。 |
| `infer:GatedResidual` | 0 | 0→0 | 输入不全 | 未找到已验证的同边界可调用模型；需补模型/组合适配，不能只改名称。 输入还缺：hc_count, hc_lowrank。 |
| `infer:ColumnParallelLinearQuant` | 0 | 0→0 | 返回结果 | 量化线性，需 scale/offset、布局与分片口径；不是普通 Linear 改名。 |
| `infer:ColumnParallelLinear` | 0 | 0→0 | 返回结果 | 已有 MatMul/Linear 基础模型；需按实际权重方向、3D batch 展平和分片边界接入，属于我们未适配。 |
| `infer:GroupMatMul` | 0 | 0→0 | 返回结果 | 候选 GroupedMatmul；需 batch/expert 与 group_list 的明确转换，不能只按名字合并。 |
| `infer:Linear` | 0 | 0→0 | 返回结果 | 已有 MatMul/Linear 基础模型；需按实际权重方向、3D batch 展平和分片边界接入，属于我们未适配。 |
| `infer:MatMul` | 0 | 0→0 | 返回结果 | 已有 MatMul/Linear 基础模型；需按实际权重方向、3D batch 展平和分片边界接入，属于我们未适配。 |
| `infer:RowParallelLinear` | 0 | 0→0 | 返回结果 | 已有 MatMul/Linear 基础模型；需按实际权重方向、3D batch 展平和分片边界接入，属于我们未适配。 |
| `infer:MHCHead` | 0 | 0→0 | 返回结果 | 有 HcPre/HcPostTriton/HcPreSinkhorn 等候选；需核对完整融合边界和参数，尚未证明可直接替代。 |
| `infer:MHCPost` | 0 | 0→0 | 返回结果 | 有 HcPre/HcPostTriton/HcPreSinkhorn 等候选；需核对完整融合边界和参数，尚未证明可直接替代。 |
| `infer:MHCPre` | 0 | 0→0 | 返回结果 | 有 HcPre/HcPostTriton/HcPreSinkhorn 等候选；需核对完整融合边界和参数，尚未证明可直接替代。 |
| `infer:Compressor` | 0 | 0→0 | 返回结果 | 理论 Compressor 已有；需转置权重、补 eps/weight、compress_ratio/coff/rope_dim/cur_seq_len，并核对融合范围。 |
| `infer:IndexCompressorEpilog` | 0 | 0→0 | 返回结果，FLOPs=0 | 有 MLA/Compressor 部件候选；Prolog/Epilog 的完整输入、阶段/量化和融合边界尚未适配，不能用整个 MLA 代替。 |
| `infer:IndexPrologV4` | 0 | 0→0 | 返回结果 | 有 MLA/Compressor 部件候选；Prolog/Epilog 的完整输入、阶段/量化和融合边界尚未适配，不能用整个 MLA 代替。 |
| `infer:KVCompressorEpilog` | 0 | 0→0 | 返回结果，FLOPs=0 | 有 MLA/Compressor 部件候选；Prolog/Epilog 的完整输入、阶段/量化和融合边界尚未适配，不能用整个 MLA 代替。 |
| `infer:MLAEpilogV4` | 0 | 0→0 | 返回结果 | 有 MLA/Compressor 部件候选；Prolog/Epilog 的完整输入、阶段/量化和融合边界尚未适配，不能用整个 MLA 代替。 |
| `infer:MLAPrologV4` | 0 | 0→0 | 返回结果 | 有 MLA/Compressor 部件候选；Prolog/Epilog 的完整输入、阶段/量化和融合边界尚未适配，不能用整个 MLA 代替。 |
| `infer:LightningIndexer` | 0 | 0→0 | 返回结果 | 工程 LightningIndexer 已有；输入布局和扩展参数未接。 |
| `infer:MoEGate` | 0 | 0→0 | 返回结果，FLOPs=0 | 有 GEMM、MoeGatingTopK/TopKV2 部件；是否含门控投影/hash/分组不同，需要完整契约或组合模型。 |
| `infer:MoEGateHashTopK` | 0 | 0→0 | 返回结果 | 有 GEMM、MoeGatingTopK/TopKV2 部件；是否含门控投影/hash/分组不同，需要完整契约或组合模型。 |
| `infer:MoEGateTopK` | 0 | 0→0 | 返回结果 | 有 GEMM、MoeGatingTopK/TopKV2 部件；是否含门控投影/hash/分组不同，需要完整契约或组合模型。 |
| `infer:MoETopK` | 0 | 0→0 | 返回结果 | 有 GEMM、MoeGatingTopK/TopKV2 部件；是否含门控投影/hash/分组不同，需要完整契约或组合模型。 |
| `infer:AddRMSNormQuant` | 0 | 0→0 | 返回结果 | 有 RmsNorm/AddRmsNorm 部件；额外 bias/gate/quant 融合边界未建适配，未发现可直接替代的同边界注册模型。 |
| `infer:RMSNormGated` | 0 | 0→0 | 返回结果 | 有 RmsNorm/AddRmsNorm 部件；额外 bias/gate/quant 融合边界未建适配，未发现可直接替代的同边界注册模型。 |
| `infer:RMSNormQuant` | 0 | 0→0 | 返回结果 | 有 RmsNorm/AddRmsNorm 部件；额外 bias/gate/quant 融合边界未建适配，未发现可直接替代的同边界注册模型。 |
| `infer:PLELayer` | 0 | 0→0 | 输入不全 | 未找到已验证的同边界可调用模型；需补模型/组合适配，不能只改名称。 输入还缺：hc_count, heads_per_ngram, ngram_size, ngram_vocab_size_base, ple_embed_dim。 |
| `infer:RopeComplex` | 0 | 0→0 | 返回结果 | 理论 RotaryPositionEmbedding 候选需 x/sin/cos 三输入；当前模板没有完整 sin/cos 表，布局语义待核对。 |
| `infer:RopeInterLeave` | 0 | 0→0 | 返回结果 | 同上，另需确认 interleave 规则和 Q/K 两路输出。 |
| `infer:QSAIndexer` | 0 | 0→0 | 输入不全 | 未找到已验证的同边界可调用模型；需补模型/组合适配，不能只改名称。 输入还缺：indexer_head_dim, indexer_kv_heads, indexer_n_heads。 |
| `infer:DynamicQuant` | 0 | 0→5 | 返回结果 | 已适配；默认成功范围见硬件表。GPU BF16 和模型假设仍受限制。 |
| `infer:SparseIndexSelect` | 0 | 0→0 | 上游失败 | 没有已验证同边界模型；上游输出形状也缺 index_topk。 |
| `infer:TorchAdd` | 0 | 0→19 | 返回结果 | 已适配；默认成功范围见硬件表。GPU BF16 和模型假设仍受限制。 |
| `infer:TorchCos` | 0 | 0→0 | 返回结果，FLOPs=0 | 未找到已验证的同边界可调用模型；需补模型/组合适配，不能只改名称。 |
| `infer:TorchCumsum` | 0 | 0→0 | 返回结果 | 已有 工程 Cumsum；当前配置无 axis 实际值，需要补语义和适配。 |
| `infer:TorchMm` | 0 | 14→14 | 返回结果 | 已适配；默认成功范围见硬件表。GPU BF16 和模型假设仍受限制。 |
| `infer:TorchMul` | 0 | 0→19 | 返回结果 | 已适配；默认成功范围见硬件表。GPU BF16 和模型假设仍受限制。 |
| `infer:TorchSin` | 0 | 0→0 | 返回结果，FLOPs=0 | 未找到已验证的同边界可调用模型；需补模型/组合适配，不能只改名称。 |
| `infer:TorchSoftmax` | 0 | 0→19 | 返回结果 | 已适配；默认成功范围见硬件表。GPU BF16 和模型假设仍受限制。 |
| `infer:TorchSort` | 0 | 0→0 | 返回结果 | 未找到已验证的同边界可调用模型；需补模型/组合适配，不能只改名称。 |
| `infer:TorchSum` | 0 | 0→0 | 返回结果 | 理论 ReduceSum 已有；资产输出指向沿 S 维归约，需显式 reduce_axis/keepdim 和输出适配。 |
| `infer:vision_encoder_block` | 0 | 0→0 | 输入不全 | 未找到已验证的同边界可调用模型；需补模型/组合适配，不能只改名称。 输入还缺：vision_hidden_size, vision_intermediate_size, vision_patch_tokens。 |
| `infer:vision_patch_embed` | 0 | 0→0 | 输入不全 | 未找到已验证的同边界可调用模型；需补模型/组合适配，不能只改名称。 输入还缺：vision_hidden_size, vision_in_channels, vision_patch_size, vision_patch_tokens, vision_temporal_patch_size。 |
| `infer:vision_patch_merger` | 0 | 0→0 | 输入不全 | 未找到已验证的同边界可调用模型；需补模型/组合适配，不能只改名称。 输入还缺：vision_hidden_size, vision_out_hidden_size, vision_patch_tokens, vision_spatial_merge_size。 |
| `infer:vision_text_embedding_merge` | 0 | 0→0 | 输入不全 | 未找到已验证的同边界可调用模型；需补模型/组合适配，不能只改名称。 输入还缺：hc_count, vision_merged_tokens。 |

## 路径与原始证据

- [默认组合 CSV](audits/2026-09-23-operator-method/cases.csv)：9,500 行，逐硬件/方法的状态、原因、耗时。
- [默认实际执行 JSONL](audits/2026-09-23-operator-method/executions.jsonl)：413 次调用，保留源码身份/时延/异常。
- [Python 3.11 对照 CSV](audits/2026-09-23-operator-method/python311-control/cases.csv) 与 [结果](audits/2026-09-23-operator-method/python311-control/executions.jsonl)：相同默认组合。
- [输入模板及原仓库相对路径](audits/2026-09-23-operator-method/templates.json)：每条包含 shape、dtype、未解析变量、source.path 和 sha256。原资产路径通常为 `modeling/backend/inference/data/operators/`；默认值在 `backend/web/services/infer/operator_catalog.py`。
- [上游 Roofline 对照](audits/2026-09-23-operator-method/upstream-roofline.jsonl)：164 个检查，128 次执行、36 次输入阻塞；上游基准版本 `b1e5bdcabd5f5470335f925310feba7023a946ad`。
- [补充输入对照](audits/2026-09-23-operator-method/supplemental.jsonl)：70 个检查，57 次执行、13 次阻塞，包含确切修改后的输入。
- [当前环境](audits/2026-09-23-operator-method/environment.json)、[对照环境](audits/2026-09-23-operator-method/python311-control/environment.json) 和 [方法汇总](audits/2026-09-23-operator-method/summary.json)。

### 复现

```bash
# 默认环境，输出到新目录避免覆盖本次证据
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 .venv/bin/python -B tools/audit_evaluations.py --output /tmp/opscope-audit-new

# 可选：仅在有原仓库及其依赖时，作上游纯计算对照
../modeling/.venv/bin/python -B tools/audit_upstream_roofline.py --modeling-root ../modeling --audit-dir /tmp/opscope-audit-new

# 本次使用已有、可正常加载 SciPy 的 3.11 环境，不是项目运行依赖
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 ../modeling/tilesim-runtime/.venv/bin/python -B tools/audit_evaluations.py --output /tmp/opscope-audit-311-new
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 ../modeling/tilesim-runtime/.venv/bin/python -B tools/audit_supplemental.py --audit-dir /tmp/opscope-audit-new
```

最多两个进程，TileSim 单次模型调用上限60秒，独立临时目录，不复用计算结果；本轮未触发模型调用超时。计时从导入后开始，并非 Web 整批 worker 的60秒预算，因此不能以此证明一批所有卡片在页面上都能60秒内完成。没有实际硬件执行，也没有校验真机预测误差；成功仅指得到模型预测。

## 建议处理顺序

1. 修复/隔离当前 SciPy 环境，并让能力探测覆盖成本模型工程 API。先恢复已适配组合。
2. 对 GB200/R200 的带宽缺项补前置检查，提示具体型号/路径/key，避免点击后才报泛化失败；没有可靠来源时不伪造参数。
3. 扩展算子配置契约：默认/必填维度、axis、perm、top_k、group_list、量化参数、布局与输出；移除 START/END，明确通信边界。
4. 优先迁入上游能实跑的 Roofline 公式，以及 MatMul/Linear 变体、ReduceSum 等已有 TileSim 模型。逐项验证数学边界，而不是按名字去重或放开白名单。
5. 910B1/B4 Roofline 与 GPU BF16/内部带宽需要可靠规格来源；复杂融合算子需要单独建模，不能靠补默认值解决。

本轮仅新增审计工具/证据/文档；未改生产适配器、依赖锁文件或原 modeling 仓库，未提交或推送。

验证：24 项评估/TileSim/覆盖定向测试通过；两轮 CSV 均为 9,500 个唯一组合、各 413 条实际执行记录，成功时延均有限且为正，非成功耗时为空；所有非示例模板的来源哈希与本地原仓库一致。审计脚本语法、离线页面重新生成及差异格式检查通过。本轮没有界面改动，不重复 UI 验收。
