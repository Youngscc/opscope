# 算子适配扩展（2026-09-23）

## 范围与口径

根据全目录审计扩展本地执行，不依赖外部 modeling 仓库。保留既有基础 Roofline 数值；新增目录公式使用显式标记的 catalog-analytic 路径，按输入绑定符号、推导输出、分精度 FLOPs 与硬件峰值计算 Roofline。这是目录公式解析预测，不冒充完整 Kepler 的模型图变换、校准或融合修正。缺公式、未知符号、规格为零以及不一致形状拒绝计算。

TileSim 优先接入数学边界明确的矩阵变体、归约、置换、扫描、Gather 等；更复杂候选必须核对输入/额外参数并实跑后才开放。算子参数与方法参数分开，前后端共享可编辑参数定义；未知维度不自动填1，量化数值和分组不猜测。无法证明等价的复合模型保留具体缺项。

## 实施与验证

1. 快照受跟踪算子资产/默认上下文，记录来源哈希；实现安全表达式和一致维度绑定，不执行请求中的代码。
2. 扩展输入参数契约与在线/离线编辑，加入数值/布局/输出校验。每个新模型保留假设和模式身份。
3. 接入 Roofline 目录公式与 TileSim 请求/输出/工作量；补 GB200/R200 已知缺项前置检查、完整依赖能力探测。
4. 新增具体 shape/FLOPs/bytes/输出/拒绝语义测试；实际批量执行支持组合及非默认参数，验证独立项目运行、UI详情与导出。
5. 更新覆盖清单，逐项列出仍缺外部规格或同边界模型的项目。不得把失败转换成估算成功，不改 profiling/方法3/4为虚构执行器。

## 已完成的适配

- 将82个可配置推理算子的本地 JSON 资产及符号默认值快照为 [`operator_specs.json`](../opscope/evaluation/data/operator_specs.json)。快照记录原文件 SHA256 和来源 revision；运行时仅读本仓库。`catalog_roofline.py` 限制可解析的表达式、绑定张量维度、检查原始 dtype、FLOPs、输出字节和硬件峰值。结果模式为 `catalog-analytic`；卡片显示“目录公式”，详情显示模型假设，区别于原有11类基础公式。
- `operator_parameters.py` 将 axis/permutation 作为算子配置属性。在线 Vue 和离线页面都提供编辑；Cumsum/GatherV2 缺实际 axis 时不能提交，已固定语义的 TorchSum/TorchCumsum/Transpose 只能使用与输出模板一致的轴或排列。属性进入配置摘要和 JSON。
- TileSim 增加四种三维 Linear/MatMul 变体、TorchSum、Transpose、TorchCumsum 的默认模板适配；Cumsum/GatherV2 填写合法 axis 后也能运行。三维输入只在请求中展平，逻辑输出仍保留原形状；工程/理论模式及模型假设进入结果。已知 GB200/R200 带宽缺项在调用前拦截。
- `setup.sh` 在 macOS Apple Silicon 使用 Python3.11；若锁文件选中的 SciPy wheel 无法导入，从同一 `uv.lock` 选取带 SHA256 校验的 macOS12 ARM64 wheel。项目 `.venv` 已实测能导入工程成本模型依赖，无需外部 modeling 环境。

## 全目录复验

使用**本项目** `.venv`（Python3.11.5、msopmodeling1.0.9、SciPy1.15.3），按相同的100模板×19硬件入口×5方法遍历9,500组合；总共实际调用1,118次，全部返回成功，前置不支持不计作执行失败。入口含示例别名与 Server/POD，不能当作19种独立芯片。机器可读的[汇总](audits/2026-09-23-adapted/summary.json)、[逐组合状态](audits/2026-09-23-adapted/cases.csv)、[执行结果](audits/2026-09-23-adapted/executions.jsonl)和[环境信息](audits/2026-09-23-adapted/environment.json)已保存。

| 方法 | 首次审计成功 | 本项目环境复验成功 | 新增默认成功模板 | 当前执行失败 |
|---|---:|---:|---:|---:|
| Roofline | 204 | 833 | 37（总49） | 0 |
| TileSim | 63；工作环境对照为209 | 285 | 7（总34） | 0 |
| Profiling / 方法3 / 方法4 | 0 | 0 | 0 | 未接执行器 |

TileSim 新结果包括 cost-eng 165、dsl-eng 50、dsl-theo 36、cost-theo 34；这些是模型模式，不表示真机精度认证。Cumsum/GatherV2 的2×19个默认组合因缺 axis 被列为 `blocked_input`，填值后另行实跑；在910B1上分别为8.620018 μs（axis=2，INT64）和134.468667 μs（axis=0，BF16），均由项目 `.venv` 实际返回。页面还以8硬件40组合运行 Cumsum，910B1/910B4 卡片逐步显示8.620/13.221 μs，详情含模型假设。

另以 `env -u OPSCOPE_ENGINE_ROOT -u OPSCOPE_ENGINE_PYTHON -u OPSCOPE_TILESIM_PYTHON .venv/bin/python -B -m backend.web --port=8786` 启动本地服务，排除本机旧 `.env` 的外部引擎路径。能力接口报告 Roofline/TileSim 均可用；同一 Cumsum 请求返回 H200 Roofline `catalog-analytic` 0.1365375 μs、910B1 TileSim `cost-eng` 8.620018 μs；910B1 Roofline 保持不支持。验证后临时服务关闭。

67项Python单元测试、3项前端状态测试、Vue类型检查与生产构建、离线页面生成、JS语法和差异格式检查通过。桌面浏览器核对算子属性、硬件筛选后的25/40→20/35结果、单条详情、双结果+12.1%比较和2条synthetic=true JSON预览，控制台无错误；这些界面检查用的是本机普通预览，它加载了旧 `.env` 覆盖，因此独立运行证据以以上显式清空覆盖项的HTTP实跑为准。

## 仍需信息或模型

- 910B1/B4缺可验证的整卡 Roofline 分精度峰值与 HBM 带宽；TileSim 的分层配置不能替代。GPU BF16 计算参数及 GB200/R200 若干带宽/存储键仍缺，故只报告不支持原因。
- 18个非通信模板的默认shape含未知维度；Cumsum/GatherV2另缺轴值。通信6模板缺拓扑、rank/group和通信模型。Profiling与方法3/4未接真实执行器。
- 分组/融合量化、稀疏Attention、MLA、vision等仍需 group_list、scale/offset、KV缓存布局或同边界模型。IndexCompressorEpilog/KVCompressorEpilog 的资产公式还缺实际 `factor`；13类推理资产没有经核对的 Roofline 计算单元映射，不能任意套矩阵或向量峰值。目录公式的下界可用不等于已接入完整 TileSim 流水或原 Kepler 图模型。
- 对与原仓库纯单算子路径共同可运行的37个新 Roofline 模板×2硬件作字段对照：输出shape/dtype为72/74一致，FLOPs为60/74一致。差异集中于 MatMulV3、SwiGlu、SwiGluQuant、GroupedMatmul、SituAndMul、MoEGate、RMSNormGated；原路径还有动态图层逻辑或不同符号上下文。`catalog-analytic` 刻意只按资产公式计算，不能拿它代替这些算子的原 Kepler 结果或当作同一精度基准。
