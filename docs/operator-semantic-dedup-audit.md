# 算子语义去重审计

## 判断标准

去重不能只比较名称。只有数学输出等价，且差异可以由 rank、batch、转置、可选输入或
辅助输出完整表达时，才合并成同一可见算子的不同输入形式。量化、通信、分片、输出布局
改变或多个算子融合会改变性能公式和数据流，只归入同一算子族，不当作同一算子。

每个候选项依次比较：数学定义、输入/输出张量、维度约束、广播和 batch 规则、dtype、
可选参数、融合边界、通信边界、FLOPs/字节公式。

## 可以合并为同一可见算子的输入形式

### MatMul

- `demo:matmul`、`train:matmul`、`infer:TorchMm`：`A @ B`，只有默认 shape/dtype 不同。
- `train:bmm`：同一矩阵收缩，多一个 batch 维；保留 batched 输入形式。
- `train:linear`、`infer:Linear`、`infer:MatMul`、`infer:MatMulV3`：`X @ Wᵀ`，保留
  weight-transposed 和二维/带前导 batch 维输入形式。

统一语义应是 `[..., M, K] × [..., K, N] -> [..., M, N]`，输入形式负责把 `[N,K]`
权重规范化为逻辑 `[K,N]`。不能在规范化前直接比较原始 shape。

### 基础逐元素和归约

- `infer:Mul` + `infer:TorchMul`：逐元素乘法；dtype/default shape 是输入形式差异。
- `train:softmax` + `infer:TorchSoftmax`：沿指定轴 Softmax；需要把 axis 加入算子配置。
- `infer:Cumsum` + `infer:TorchCumsum`：沿指定轴前缀和；一个把 axis 作为张量输入，
  一个隐含在调用参数中。

### 归一化

- `train:rms_norm` + `infer:RmsNorm`：相同 RMSNorm；推理形式额外返回 `rstd`。
- `train:layernorm` + `infer:LayerNormV4`：相同 LayerNorm 核心；保留 rank、
  normalized_shape、scale/bias 和 mean/rstd 辅助输出差异。
- `infer:AddRmsNorm` + `infer:AddRmsNormBias`：相同 residual-add + RMSNorm，`beta`
  是可选输入形式。

### 显式查表

- `train:embedding` + `infer:GatherV2`：显式表 `weight/table` 按 indices 取行；Gather 的
  axis 必须固定为词表轴后才等价。

## 同一算子族，但必须保留独立语义变体

这些项可在界面中放在同一族下，但每个变体必须有独立的 workload、支持矩阵和方法适配。

- `train:flash_attention` / `infer:FlashAttentionScore`：都是 dense attention；后者有 mask、
  scale 以及 softmax 辅助输出。不能丢掉辅助输出契约。
- `infer:SparseFlashAttention` / `infer:KvQuantSparseFlashAttention`：相同稀疏注意力族，后者
  加入 FP8 KV、分页/反量化语义。
- `infer:DynamicQuant` / `infer:DynamicQuantV2`：动态量化族；V2 有平滑参数和 offset 输出。
- `infer:GroupMatMul` / `infer:GroupedMatmul`：Grouped GEMM 族；后者使用 tensor-list、
  group_list、scale/offset 等更完整协议。
- `infer:MoEDispatch` / `infer:MoeDistributeDispatchV3`，以及 `infer:MoECombine` /
  `infer:MoeDistributeCombineV3`：相同 dispatch/combine 阶段，V3 含 DeepEP 上下文、计数、
  量化和更明确的通信协议。
- `infer:RopeComplex` / `infer:RopeInterLeave`：同属 RoPE，但复数布局与交错布局不是同一
  数学表示，保留独立语义。
- `infer:MoEGate`、`infer:MoETopK`、`infer:MoEGateTopK`、`infer:MoeGatingTopK`、
  `infer:MoEGateHashTopK`：分别是打分、TopK、融合 Gate+TopK、分组限制和哈希路由，
  只能归为 MoE Routing 族。

## 必须拆开或禁止误合并

### 两种 SwiGLU

- `train:swiglu`：输入 hidden、gate/up/down 三组权重，表示完整投影 MLP。
- `infer:SwiGlu`：单输入末维二分，执行 `silu(gate) * up`。

两者虽然同名，但 FLOPs、权重流量和输出推导完全不同。建议分别显示为“融合 SwiGLU MLP”
和“SwiGLU 激活”。`SwiGluQuant`、`SwigluGroupQuant`、`GroupedMatmulSwigluQuantV2` 还包含
量化或 Grouped GEMM，继续独立。

### Embedding 资产

`infer:Embedding` 的描述是查表，但当前输入为两个 `[B,S] int64` 张量，没有显式权重表；
输出却是 BF16 hidden。该契约无法从输入独立推导，不能与显式 `weight + indices` 的
Embedding 合并。需要先确认第一个输入是否误写、权重是否为隐式模型状态。

### 分布式 Linear

`ColumnParallelLinear` 输出分片，`RowParallelLinear` 含输出 AllReduce；它们与本地 Linear
数学主干相近，但通信和输出边界不同。保留“分布式 Linear”族，不并入普通 MatMul。
对应 Quant 版本也保留独立。

### 融合和布局变化

- `TransposeBatchMatMul` 还改变输出布局为 `[M,B,N]`，并支持 bias/scale，不能仅按多一个
  batch 维合并进普通 MatMul。
- `AddRMSNormQuant`、`RMSNormQuant`、`RMSNormGated`、`GemmaRmsNorm` 分别增加量化、门控
  或 `(1 + gamma)` 语义，不与普通 RMSNorm 去重。
- `SituAndMul` 使用 tanh/sigmoid 组合公式，不是 SiLU，也不是普通 SwiGLU。
- `GroupedMatmulSwigluQuantV2` 是 GEMM、SwiGLU、量化融合边界，不拆成任一单算子。

## 不应进入可评估算子列表

`START`、`END` 是流程边界，不是性能算子。通信条目可以保留在目录族中，但在单算子方法
没有通信模型前必须继续标记不可评估，不能通过名字相似合并到本地数据搬运算子。

## 当前实现的问题

`operator_groups()` 只对名称做大小写和下划线归一化。因此：

- 漏掉 `TorchMm/MatMulV3/BMM/Linear` 等语义别名；
- 错误合并两种 SwiGLU；
- 无法表示“同一数学操作，不同 batch/rank/转置”；
- 无法区分“同族”与“等价输入形式”。

后续目录应增加 `semantic_id`、`family_id`、`variant_id`、`equivalence`、`layout`、
`batch_semantics`、`fused_ops`、`distributed_semantics` 和规范化输入/输出契约。界面按
`semantic_id` 去重，按 `variant_id` 选择输入形式；`family_id` 只用于分类，不参与去重。

## 实施顺序

1. 先修正 SwiGLU 和 Embedding 两个现有误合并/不确定项。
2. 建立 MatMul 规范化契约，合并二维、batched、weight-transposed 输入形式。
3. 合并 Mul、Softmax、Cumsum、RMSNorm、LayerNorm 的安全别名。
4. 为量化、稀疏、分布式、融合算子增加 family/variant 层，不直接消除其独立契约。
5. 用统一输出、FLOPs 和逻辑字节测试证明每个等价组，而不是再依赖名称规则。
