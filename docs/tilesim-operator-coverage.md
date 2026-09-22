# TileSim 算子覆盖扩展

## 目标

把已安装 `msopmodeling 1.0.9` 中能够与 OpScope 当前算子模板对齐的模型接入 TileSim 列。支持以实际公开 API 调用成功为准；模型存在但缺少轴、排列、分组边界等运行值时，继续显示具体缺项，不按名称宣称支持。

## 接入原则

- MatMul 与 FlashAttention 保留现有 DSL 工程模型和流水。
- 其余算子优先使用 TileSim 工程成本模型；工程模型未实现而理论模型可运行时，结果明确标为理论模式。
- 每个适配器负责输入形状、输出形状、dtype 和逻辑工作量，不复用 MatMul 公式。
- 补充的常量输入必须是语义确定的值。例如无 bias 的 LayerNorm 可用零 beta 表达，但结果注明 TileSim 仍按完整 affine 模型估算。
- 不能从当前配置得知 scalar/tensor 内容的算子保持不支持，例如未知 transpose perm、Gather axis 和 group list。
- TileSim 失败不回退到 Roofline，也不产生虚拟结果。

## 本轮范围

首批覆盖当前目录中契约完整、与 TileSim 模型可以直接或等价转换的算子族：

- 矩阵：MatMul、Linear、BMM 及等价 Torch/推理别名。
- Attention：当前已验证的稠密 FlashAttention。
- 归一化：LayerNorm、RMSNorm、AddRmsNorm、GemmaRmsNorm。
- 激活与逐元素：SiLU、GELU、Softmax、Mul、Add、Sigmoid、SwiGLU 激活。
- 数据访问：训练 Embedding 的固定 axis=0 Gather。
- 转换与路由：BF16→FP32 Cast、DynamicQuant、默认 top_k=8 的 MoeGatingTopK、TransposeBatchMatMul。

融合 SwiGLU MLP 与 SwiGLU 激活保持分离。带未知轴、未知排列、未知分组列表、通信或复合边界的模板不开放，并返回缺少的配置项。

## 验证

1. 契约测试核对每个开放模板的 TileSim 算子、模式、输入输出和限制原因。
2. 使用 910B1/910B4 对默认形状实际调用已安装 API，校验时延为有限正数、实际后端为 TileSim。
3. 回归 MatMul/FlashAttention 流水、逐卡发布、详情和 JSON，不改变原有结果。
4. 前端仍由结果状态驱动，不新增静态“支持”标记。

## 实施与实跑

已登记26个目录模板；infer:FlashAttentionScore默认 head_dim 未填写且默认序列规模超过本地流水上限，保持具体缺项。改成完整、相同且在事件上限内的Q/K/V后可以运行；实测[1,8,512,128]在910B1/910B4分别为13.977425/18.839385μs，各1328个事件。其余25个默认模板在910B1和910B4上逐项调用成功。

代表性结果：

| 模板 | 910B1 μs | 910B4 μs | 模式 |
| --- | ---: | ---: | --- |
| LayerNorm [1024,4096] BF16 | 54.266292 | 72.481067 | 成本模型工程 |
| RMSNorm [1024,4096] BF16 | 20.136326 | 24.294752 | 成本模型工程 |
| BMM [32,128,512]×[32,512,128] BF16 | 132.570359 | 238.107421 | 成本模型工程 |
| GELU [1024,4096] BF16 | 12.661508 | 17.565150 | 成本模型工程 |
| SwiGLU激活 [1,2048,22016] BF16 | 113.286202 | 174.596383 | 成本模型理论 |
| DynamicQuant [1,2048,4096] BF16 | 4.447863 | 4.520897 | 成本模型工程 |

LayerNorm缺少beta时补零beta；LayerNormV4缺少affine张量时按单位gamma、零beta建模，并在详情中显示假设。GemmaRmsNorm使用普通RMSNorm成本模型，额外加法只进入逻辑工作量。以上是模型接口验证，不是真机精度认证。

项目虚拟环境59项Python测试、3项前端状态测试、JavaScript语法、Vue类型检查/构建、离线生成和差异格式检查通过。
