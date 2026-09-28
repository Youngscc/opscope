# 共享算子覆盖（2026-09-28）

OpScope 继续通过 HTTP 复用 modeling 的目录、硬件、Roofline 与 TileSim。此次补齐的是目录配置和共享后端适配，不新增 OpScope 性能公式，也不修改 modeling 前端。

## 实测范围

可见目录共 100 个模板（11 个基础模板、89 个资产模板）。使用 H200_Server 的 train 硬件档案、各模板默认形状和参数，直接执行严格服务。结果是模型预测，不是真机测量或任意形状/全硬件的支持认证。

| 审计配置 | 成功 | 不支持 | 未决超时 |
| --- | ---: | ---: | ---: |
| Roofline，目录默认精度 | 93 | 7 | 0 |
| TileSim，目录默认精度 | 11 | 89 | 0 |
| TileSim，显式将 BF16 输入改为 FP16 | 24 | 76 | 0 |

首轮每项 10 秒；RowParallelLinear 默认精度、ColumnParallelLinear FP16 两项延长至 60 秒复验成功，已用复验结果替换，未把超时计入“不支持”。第三行是独立配置实验，**系统不会自动将 BF16 降为 FP16**。测试用 msopmodeling 1.0.9；不支持包含原生模型拒绝、原生异常和严格契约拒绝，逐项原因见 CSV。

- [300 项结果、输入、参数、版本摘要与原因](audits/2026-09-28-shared-operator-h200.csv)
- [本次硬件和算子定义快照](audits/2026-09-28-shared-operator-h200-snapshots.json)
- [修改前 Roofline 初查：55 成功/45 不支持](audits/2026-09-24-shared-roofline-h200.csv)

## 补齐内容

- modeling 从资产输入、权重、输出及必要计算表达式统一提取符号，提供可编辑参数及边界。不能从输入唯一确定的 B、S、kv_len、头数、视觉参数、列表参数等显式传输。未知符号保持缺失，不默认填 1。补充示例值仅用于单算子配置，不代表某个完整模型或硬件事实；目录参数的 `source` 区分来源。
- 严格校验形状、dtype、参数白名单与固定轴合同。保留 BOOL、UINT64 和 FP32 累加/统计输出；允许资产明确声明的零尺寸可选输出。单算子不再调用会改写形状的整图阶段逻辑。
- Roofline 优先复用已登记公式；缺项直接调用 Kepler 算子已有工作量计算器，分离矩阵、向量、SFU 和实际张量字节。Linear 系列使用资产 NK 权重合同，避免套入 KN 公式。SFU 沿用共享 Kepler 成本策略，结果记录策略与来源。
- TileSim 补齐精确别名、可证明等价的矩阵/逐元素展平、轴与排列参数，以及 Cumsum/GatherV2/TransposeBatchMatMul 等原生工程入口。输入输出数量不随意删补，混合精度不暗改，硬件型号不借用，原生失败不回退 Roofline。
- OpScope 只展示、校验并传递这些参数；详情和 JSON 保留有效参数、模型模式、工作量来源、SFU 策略、实际原生输入。TileSim 总时间来自原生输出，计算/访存等仍明确为 Roofline 补充，不代表原生流水。

## 剩余缺口及定位

| 缺口 | 例子/需要的信息 | 维护位置与可比来源 |
| --- | --- | --- |
| 非计算模型范围 | AllGather、AllReduce、EngramPrefetch、MoeDistributeCombineV3、MoeDistributeDispatchV3、START、END 共 7 个 Roofline 拒绝项；需要通信拓扑/链路或不应作为计算任务的控制语义 | modeling `backend/inference/data/operators/`、`backend/inference/kepler/engine/bridge.py`；通信要走既有通信模型，不能虚构 FLOPs |
| 原生算子不存在 | VisionEncoderBlock、MHCPre、RMSNormQuant、CausalConv1d 等 | worker 环境 `tilesim/core/common/entity.py` 的 OpType 与 `tilesim/core/pipeline/` 原生实现；modeling `backend/simulator/backends/tilesim_strict.py` 不能替代缺失的原生算法 |
| 资产与原生输入输出边界不同 | LayerNorm/LayerNormV4 缺原生要求的第三输入；基础 RMSNorm 仅一个输出，原生要求 y/rstd；FlashAttentionScore、AddRmsNorm 输出数不符；稀疏注意力/indexer 原生要求更多输入 | modeling `backend/web/services/train/op_sim.py`、`backend/inference/data/operators/`；可对照成功的资产 RmsNorm（x/gamma→y/rstd）。需要明确真实张量/属性合同，不能凭空补 gamma/beta 或删输出 |
| 型号/精度或原生执行限制 | 默认 BF16 与显式 FP16 通过数不同；部分枚举存在但对应模式无实现；部分 GELU、Compressor、FA 请求产生原生异常 | worker 安装的 `tilesim/core/config/arc_config/H200/`、`core/pipeline/tilesim_theo/` 与工程实现；实际错误和配置见 CSV，不统称为“缺硬件数据” |
| 当前适配主动拒绝 | 不等价广播展平、混合输入输出精度的 MatMul、缺 axis 的 Gather、融合量化边界 | modeling `backend/simulator/backends/tilesim_strict.py`、`tilesim.py`；有可证明等价的合同后再扩展，保留现在的具体拒绝原因 |

资产定义优先维护于 modeling `backend/inference/data/operators/`（运行时已有资产库条目还需按既有资产版本流程更新）；符号 schema 在 `backend/web/services/train/strict_dimensions.py`，工作量复用在 `strict_workload.py`。不要修改 `.venv` 安装副本作为永久修复，也不要在 OpScope 复制一份资产兜底。详细后端不变量见[能力说明](../../modeling/docs/architecture/specs/strict-operator-evaluation.md)。

## 验证

- OpScope 97 项 Python 测试、5 项前端测试、类型与生产构建、离线生成及 JS 语法检查通过。
- modeling 严格契约与覆盖测试 26 项通过。扩大回归 187 通过、3 失败；3 项在原始 f571e9f 同样复现（两个 RMSNorm 公式期望、一个 AllReduce 桥接断言）。全量 pytest 仍被原有 5 个导入收集错误阻断；validation.cli 4/4，通过不代表真机精度认证。
- 无 NumPy/SciPy/Torch/TileSim 的 OpScope 环境，经 HTTP/worker 实跑 RmsNorm：FP16 x=[128,128]、gamma=[128]、B=1、S=128，H200_Server。Roofline 0.0345333333 μs、TileSim 0.6943698719 μs。页面核验配置、筛选、卡片、详情与双结果对比。测试服务 8802/8803 使用隔离任务库，原 8768 未动。
- modeling 环境同版本 SciPy 1.15.3 的 macOS 14 wheel 出现本机动态库加载错误，改装锁文件已有的 macOS 12 wheel 后工程 API 可导入；未给 OpScope 增加计算依赖。

未完成：全硬件、任意形状/精度认证、原生 TileSim 缺失模型、真实流水、生产身份集成与旧引擎副本物理清理。以上失败边界已明确保留，不以“目录补齐”宣称全部组合能运行。
