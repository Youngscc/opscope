# 当前评估缺口与参数位置

本表按 `2026-09-23-adapted` 审计的**默认模板**统计：100 个内部模板 × 19 个硬件入口 × 5 个方法，共 9,500 格。19 个入口包含别名、Server/POD 与独立 TileSim 配置，不等于 19 种芯片。源码和输入变化后，以重新执行的结果为准；用户另行填写轴或形状后，状态也可能变化。[逐格原始状态](audits/2026-09-23-adapted/cases.csv)、[输入模板](audits/2026-09-23-adapted/templates.json)、[实际执行](audits/2026-09-23-adapted/executions.jsonl)可用于逐项核对。该审计实际调用 1,118 次，调用失败 0；`unsupported`/`blocked_input` 是前置拒绝，不是引擎运行崩溃。下列格数均为**修复前历史快照**，本页后续复验记录会注明变化。

## 通用输入缺口

每个方法都有 342 格、18 个非通信模板因默认张量维度未确定而 `blocked_input`；另有 Cumsum/GatherV2 各 19 格缺轴实际值。这些值属于**算子实例输入**，不应补到硬件配置或 TileSim 全局默认。当前模板存在 [`data/modeling-catalog.json`](../data/modeling-catalog.json)，原始公式和默认符号在 [`operator_specs.json`](../opscope/evaluation/data/operator_specs.json)；两者由 [`snapshot_catalog.py`](../tools/snapshot_catalog.py) 与 [`snapshot_operator_specs.py`](../tools/snapshot_operator_specs.py) 生成，若需长期加入项目自有默认值，应建立明确的版本化覆盖或修改可信来源后重生快照。可编辑的轴/排列契约在 [`operator_parameters.py`](../opscope/evaluation/operator_parameters.py)，请求规范化在 [`evaluation_contract.py`](../opscope/evaluation/evaluation_contract.py)。已完整的对照：`infer:MatMul` 的 `B/S/hidden_size/intermediate_size`、`infer:TorchAdd` 的输入与公式；已接轴的 `infer:TorchCumsum` 为 `axis=-1`、`infer:TorchSum` 为 `axis=1`。不要把这些值套给别的算子。

| 18 个默认形状不完整模板 | 未确定的维度符号 |
| --- | --- |
| ChunkGatedDeltaRule | key_head_dim, num_key_heads, num_value_heads, value_head_dim |
| FlashAttentionScore | qk_head_dim, qk_nope_head_dim |
| FusedInferAttentionScore | max_num_blocks, qk_head_dim, qk_nope_head_dim, qk_rope_head_dim |
| KvQuantSparseFlashAttention | index_topk, kv_lora_rank, qk_rope_head_dim |
| SparseFlashAttention | index_topk |
| CausalConv1d | num_cache_lines, state_len |
| FusedGdnGating | num_heads |
| SwigluGroupQuant | routed_tokens_per_rank |
| MlaPrologV3 | kv_lora_rank, qk_nope_head_dim, qk_rope_head_dim |
| EngramGate | engram_head_dim, engram_max_ngram_size, engram_n_heads |
| EngramLookup | engram_head_dim, engram_num_embeddings |
| GatedResidual | hc_count, hc_lowrank |
| PLELayer | hc_count, heads_per_ngram, ngram_size, ngram_vocab_size_base, ple_embed_dim |
| QSAIndexer | indexer_head_dim, indexer_kv_heads, indexer_n_heads |
| vision_encoder_block | vision_hidden_size, vision_intermediate_size, vision_patch_tokens |
| vision_patch_embed | vision_hidden_size, vision_in_channels, vision_patch_size, vision_patch_tokens, vision_temporal_patch_size |
| vision_patch_merger | vision_hidden_size, vision_out_hidden_size, vision_patch_tokens, vision_spatial_merge_size |
| vision_text_embedding_merge | hc_count, vision_merged_tokens |

逐模板原资产相对路径和未解析符号均在[输入模板 JSON](audits/2026-09-23-adapted/templates.json)；若本机有 modeling 源码，实际文件在 `../modeling/backend/inference/data/operators/`，其默认上下文在 `../modeling/backend/web/services/infer/operator_catalog.py`。Cumsum/GatherV2 的 shape 里虽有 axis 张量，但**张量形状不能表示轴的数值**；应在配置 `attributes.axis` 填 2/0。已有可运行的 TorchCumsum/TorchSum 属性是同类格式对照。

另有 6 个通信模板 × 19 入口 = 114 格/方法被有意排除：AllGather、AllReduce、MoECombine、MoEDispatch、MoeDistributeCombineV3、MoeDistributeDispatchV3。缺的是拓扑、rank/group、通信量与边界、通信成本模型；当前 [`evaluation_contract.py`](../opscope/evaluation/evaluation_contract.py) 只定义单算子设备端边界，`data/modeling-catalog.json` 中的张量形状不足以计算通信耗时。modeling 的硬件档案 `../modeling/backend/hardware/{train,infer}/` 可对照互联字段，但不是本项目已接的通信执行器。

## Roofline：573 格前置不支持

| 格数 | 缺什么 | 本项目持久化/逻辑位置 | 可比对的同类数据 |
| ---: | --- | --- | --- |
| 148 | 910B1、910B4 各 74 个可评估模板缺**该 SKU 的**矩阵/向量分精度峰值、整卡 HBM 带宽 | [`roofline_hardware.json`](../opscope/evaluation/data/roofline_hardware.json) 尚无两型号条目；新增后还须更新 [`hardware_key`](../opscope/evaluation/evaluation_contract.py) 映射和 [`engine_worker.py`](../opscope/evaluation/engine_worker.py) 的专门拒绝分支 | JSON 中 `Adevice03_Server` 是 NPU 字段格式范例、`H200_Server` 是另一完整规格；modeling `../modeling/backend/hardware/{train,infer}/Ascend-Adevice03-Server.yaml`。**数值不能照抄为 910B。** |
| 221 | 13 个推理模板没有可验证的 cube/vector 峰值单元对应；有些原资产写 `mix`，单一峰值无法直接代表混合运算 | [`operator_specs.json`](../opscope/evaluation/data/operator_specs.json) 的 `compute_unit`、[`catalog_roofline.py`](../opscope/evaluation/catalog_roofline.py) 的 `UNIT_OVERRIDE`/`unit_for` | `infer:MatMul` 对 cube，`infer:TorchAdd` 对 vector；混合算子需拆分 FLOPs 或明确模型，不是给 `mix` 随意选一列 |
| 102 | 6 个模板被显式排除：START/END 是流程标记；Embedding、MoeGatingTopK、QuantLightningIndexer、SparseIndexSelect 的当前资产/输出或上游纯算子路径尚未核准 | [`catalog_roofline.py`](../opscope/evaluation/catalog_roofline.py) 的 `EXCLUDED`；资产在 [`operator_specs.json`](../opscope/evaluation/data/operator_specs.json) | 已验证的 `train:embedding`、`infer:TorchAdd` 展示不同输入和公式；不可仅按相近名称解除排除 |
| 51 | ScatterNdUpdate、TorchCos、TorchSin 三份资产没有 `compute_flops` | [`operator_specs.json`](../opscope/evaluation/data/operator_specs.json) 的各自 `spec.compute_flops`，源资产路径由 `source.path` 指向 | `infer:TorchAdd` 有逐元素公式；`infer:Transpose` 明确 0 FLOPs、数据搬运模型。是否为 0 需按语义核对，不能因缺项自动填 0 |
| 34 | IndexCompressorEpilog、KVCompressorEpilog 公式引用的 `factor` 无值 | [`operator_specs.json`](../opscope/evaluation/data/operator_specs.json) 的 `defaults`/两份 `compute_flops`；实际运行值应进入算子属性/配置契约 | 同文件 `compress_ratio`、`top_k` 是已定义默认符号，`operator_parameters.py` 展示有实际值的属性格式；不能用别的算子 factor 猜测 |
| 17（修复前） | QuantBatchMatmulV3 的 FP8 峰值曾全部被判缺，其中 **16 格是本项目字段匹配错误**：[`peak()`](../opscope/evaluation/bundled_roofline.py) 原先按 `fp8_tflops` 查，资产实际存 `fp8_tops`；仅 `Adevice03_POD` 的 `fp8_tops=0` 是仍待核验的规格缺项 | 已修正 `bundled_roofline.py:peak` 的 FP8 单位键映射并逐型号复验；没有向硬件资产重复填数 | [`roofline_hardware.json`](../opscope/evaluation/data/roofline_hardware.json) 的 `B200_Server.compute.cube.fp8_tops=4500`、`H200_Server=1979` 是已有值；`Adevice03_POD=0` 表示未支持/未知，不能拷贝 Server 数值 |

这套数据属于 Roofline 整卡规格，不能从 TileSim 的每核缓存、指令周期或搬运通路带宽直接换算。现有 modeling 受跟踪 `backend/hardware/` 也没有 910B1/B4 的同口径整卡 Roofline 档案。

### FP8 字段修复后增量复验

将 `fp8` 峰值读取改为硬件快照已有的 `fp8_tops` 后，使用独立 Roofline worker 对 `infer:QuantBatchMatmulV3` 默认输入和全部 17 个非 TileSim 硬件入口实际执行：**16 格成功、1 格不支持、0 格运行失败**。例如 H200_Server 别名 `h200` 返回 186.64334889135927 μs，B200_Server 别名 `b200` 返回 82.08159721244445 μs，均为目录公式解析预测、非实测。`modeling:Adevice03_POD` 仍因 FP8 峰值为 0 前置拒绝。910B1/B4 的独立 Roofline 规格缺口未变。未重跑其余 9,483 格，旧 CSV 与上述 573 格总数保留为修复前审计记录，不代表当前全量统计。

上述 13 个待确认计算单元的模板为：Compressor、GroupMatMul、GroupedMatmulSwigluQuantV2、IndexPrologV4、LightningIndexer、MHCHead、MHCPost、MHCPre、MLAEpilogV4、MLAPrologV4、MoEGateHashTopK、MoEGateTopK、SparseAttentionSharedKV。

## TileSim：1,121 格前置不支持

TileSim 原始配置的**仓库持久来源**是 [`vendor/msopmodeling/msopmodeling-1.0.9-py3-none-any.whl`](../vendor/msopmodeling/msopmodeling-1.0.9-py3-none-any.whl)；安装后可读文件在 `.venv/lib/python3.11/site-packages/tilesim/core/config/arc_config/<型号>/`。`.venv` 是重建产物，不能把修改只留在那里。目前没有项目自有的 TileSim 硬件覆盖文件；要长期补参数，应先引入版本化项目资产和加载/校验逻辑，或升级经核验的 wheel。OpScope 的适配映射在 [`tilesim_contract.py`](../opscope/evaluation/tilesim_contract.py)、[`tilesim_adapters.py`](../opscope/evaluation/tilesim_adapters.py)，读取入口在 [`tilesim_worker.py`](../opscope/evaluation/tilesim_worker.py)。

| 格数 | 缺什么 | 当前可对照文件/同类数据 |
| ---: | --- | --- |
| 665 | 35 个模板尚无**同数学边界且经验证**的适配；其中一部分 TileSim 有相近模型，但缺输入、输出、融合范围或参数转换，不能笼统说 TileSim 没模型 | [`tilesim_contract.py`](../opscope/evaluation/tilesim_contract.py) 的 `OPERATOR_KINDS`/`missing_contract_reason`、[`tilesim_adapters.py`](../opscope/evaluation/tilesim_adapters.py) 的已接模型；[TileSim 模型清单](audits/2026-09-23-adapted/tilesim-model-inventory.json) 与[逐算子审计](operator-method-audit.md)列候选 |
| 336 | H200/GB200/R200 模型 YAML 缺所需 BF16 cube/向量参数；包含映射到这些模型的多种页面硬件入口 | 安装副本 `.../arc_config/H200/H200.yaml`、`GB200/GB200.yaml`、`R200/R200.yaml`；比较 `.../arc_config/910B1/910B1.yaml` 的 `cube_config.cube_repeat_cycles.BF16` 和向量配置，不能把 NPU 参数复制给 GPU |
| 20 | GB200/R200 的 MatMul 理论模式缺 `L0C → L2` 带宽 | `.../arc_config/{GB200,R200}/bandwidth_<型号>.csv`；比较 `.../arc_config/H200/bandwidth_H200.csv` 或 `910B1/bandwidth_910B1.csv` 的同名 `src_mem,dst_mem` 行，仅比字段，不比数值 |
| 5 | GB200/R200 的 TorchSum 等需 `GM → L1` 或 `L0C → L2` 路径带宽 | 同上；支持条件在 [`tilesim_contract.py`](../opscope/evaluation/tilesim_contract.py) |
| 38 | GroupedMatmul 等缺 `group_list`/`top_k` 的实际运行值和分组语义 | 当前 [`operator_parameters.py`](../opscope/evaluation/operator_parameters.py) 尚无这组属性；对照已实现的 Cumsum/GatherV2 `axis` 属性及 TileSim `MoeGatingTopK` 默认 top_k=8 的显式假设 |
| 38 | DynamicQuantV2、QuantBatchMatmulV3 缺目标 dtype、量化 scale/offset 或完整输入契约 | [`operator_specs.json`](../opscope/evaluation/data/operator_specs.json) 对应资产；对照已接的 DynamicQuant、Cast 在 [`tilesim_adapters.py`](../opscope/evaluation/tilesim_adapters.py) 中如何声明输出 dtype |
| 19 | `train:swiglu` 是融合 MLP，不能替换为 TileSim 的单输入 SwiGLU 激活 | 对照已接的 `infer:SwiGlu` 输入/输出与 `train:swiglu` 多权重模板，见 [`data/modeling-catalog.json`](../data/modeling-catalog.json) |

上表不含共通的 342 个缺形状和 38 个缺轴格，以及 114 个通信排除格；它们已在上一节解释。TileSim 工程/理论成本模型即使返回耗时也通常**没有事件流水**，这不算评估失败。只有 DSL 工程模式返回真实模拟事件。

665 格对应的 35 个模板是：AddRMSNormQuant、AddRmsNormBias、ColumnParallelLinearQuant、Compressor、DynamicMxQuant、END、Embedding、GroupMatMul、IndexCompressorEpilog、IndexPrologV4、KVCompressorEpilog、LightningIndexer、MHCHead、MHCPost、MHCPre、MLAEpilogV4、MLAPrologV4、MoEGate、MoEGateHashTopK、MoEGateTopK、MoETopK、QuantLightningIndexer、RMSNormGated、RMSNormQuant、RopeComplex、RopeInterLeave、START、ScatterNdUpdate、SituAndMul、SparseAttentionSharedKV、SparseIndexSelect、SwiGluQuant、TorchCos、TorchSin、TorchSort。其中 START/END 是流程标记，不应当为它们造模拟结果；其余是否可适配须逐个比较数学边界。

## 尚未接入的方法

Profiling 的 1,406 格、方法3/方法4 各 1,406 格是**没有真实数据源/执行器**，不是缺一个硬件数值。其余 380 格/方法缺输入、114 格/方法是通信排除。入口和原因在 [`engine_worker.py`](../opscope/evaluation/engine_worker.py) 的 `unavailable_reason`；方法列表在 [`fixtures.py`](../opscope/offline/fixtures.py)。当前运行结果只在 [`evaluation_runtime.py`](../opscope/evaluation/evaluation_runtime.py) 的内存任务里，最多保留 12 项；本项目没有 Profiling 实测文件或方法3/4 参数库可供照填。页面示例虚拟数据在 `opscope/offline/`，带 `synthetic=true`，只能比较展示字段，不能作为执行器结果。

## 查询单个失败格

在 [`cases.csv`](audits/2026-09-23-adapted/cases.csv) 用 `operator_id + hardware + method` 定位，先看 `status/reason`。`blocked_input` 对照 [`templates.json`](audits/2026-09-23-adapted/templates.json) 的张量和 `unresolved_dimensions`；`unsupported` 按本页对应代码/配置追到缺项；`failed` 才查 [`executions.jsonl`](audits/2026-09-23-adapted/executions.jsonl) 的异常。本次默认审计没有实际执行失败。用户自定义形状、dtype、属性可能改变前置判断，须按当次结果再查。
