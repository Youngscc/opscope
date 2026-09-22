# 建模组件复用可行性分析

日期：2026-09-22。范围：源码分析与无持久化的本地单算子调用；未接入服务、修改页面、安装依赖或运行真机算子。

## 结论与证据

可以复用建模组件。Roofline 在本机已有环境可运行；TileSim 只有适配器，本体和硬件配置未安装。当前 index.html 是静态展示，不能独立执行本机 Python。建议保留页面，以可选的 Python 服务提供评估，或离线预计算后生成可双击查看的结果快照。

核查 modeling 已跟踪源码基线 b1e5bdcabd5f5470335f925310feba7023a946ad；现有未提交 AGENTS.md/stats.json 未修改。使用 modeling/.venv/bin/python，Python 3.11.16，PYTHONPATH=backend/train，-B 禁止字节码写入。torch/numpy/yaml/pydantic 可发现；未安装新包。未调用任务提交路由或查询用户任务数据库。

- 真实调用 `run_op_sim(OpSimRequest(..., simulation='roofline'))`：OP_CATALOG 全部11个基础模板 × H100_Server/H200_Server/Adevice03_Server，共33次成功，实际返回 backend=roofline。这是可运行性检查，不是准确性认证、任意形状覆盖或94个目录算子的完整认证。
- 独立构造 MatMul A/B/C=[4096,4096]、FP16，直接调用 RooflineSimulator：H200_Server 总耗时277.935194μs、计算277.935194μs、访存24.672376μs；FLOPs137438953472，读67108864B、写33554432B，bound=compute。H100同配置总耗时277.935194μs、访存35.351465μs；Adevice03_Server总耗时522.184474μs、访存74.017129μs。没有分配这些张量或执行设备kernel，以上都是模型预测。
- 默认校准库 default_lib_dir() 返回 None，三个直接调用 calibration_source 均为空，不能称作已校准结果。
- `_TILE_SIM_AVAILABLE=False`，modeling/tilesim 目录不存在，当前解释器不能发现 tilesim/api 模块。未检查外部机器上是否另有安装。仓库跟踪的是适配器与检查脚本，不包含 TileSim 本体；`.gitignore` 忽略 tilesim*。

## 可复用边界

| 组件 | 可复用内容 | 接入限制 |
| --- | --- | --- |
| RooflineSimulator | 总耗时、计算/访存成本、工作量、瓶颈、校准来源 | 需准确的 OpNode、输出形状及硬件规格；未知算子有通用公式兜底，不能将成功返回当作完整支持 |
| 单算子服务 | 11种基础模板、输入元数据、输出推导、硬件加载 | 请求主要是算子/硬件/输入/方法；页面转置/layout/累加精度等必须逐项适配或显式拒绝，不能忽略 |
| TilesimSimulator | 算子命名/shape映射及 op_latency_predict 调用路径 | 先取得本体、依赖及正确硬件配置；当前 backend_type='theo'，不是默认提供完整流水的执行模拟 |
| Kepler目录与桥接 | 更广的算子定义、张量角色及输出/公式构造 | 不直接把推理Web总结果作为独立Roofline或TileSim列；其默认路径有自动选择/回退，Web结果 backend 固定写 kepler |
| Lookup/Profiling | 精确匹配已有测量记录的查询思路 | 需要可访问数据及硬件/内核/软件身份；查询不会自动运行真机测量 |
| 硬件目录 | 本地规格加载、档案与参数 | 目录存在不等于所有方法适配，Server/POD名称不意味着已运行完整集群模型 |

## 必须处理的问题

1. **方法强制选择**：训练单算子策略只显式识别 roofline/lookuptable，传 tilesim 会落到默认 LOOKUP_FIRST，不是纯TileSim。通用Hub优先链包含Lookup→TileSim→Roofline；OpScope应使用独立适配器，TileSim不可用就显示不可用，不能拿回退的Roofline填入TileSim列。Roofline校准保留同一列元数据。
2. **实例与缓存隔离**：SimCache键不含方法策略、完整硬件配置、引擎/校准版本；Roofline又可能直接返回 node.sim_result 已有结果，TileSim会原地更新该对象。每个方法使用独立节点和运行上下文；后续缓存包含完整工作负载、硬件摘要、方法及版本。不能仅把同一个Hub循环换方法。
3. **硬件对应**：现有映射H100/H800/A100/B300/GB300都指H200配置，Adevice03指910B4而加载的soc为Ascend910_9382；B200指GB200配置。前两种差异已由源码/加载值核对，未量化误差；GB200是否适合所选B200需单独验证。上线矩阵前建立方法级硬件白名单，不能照搬映射宣称精确型号支持。
4. **统一算子契约**：同名算子可能输入顺序、融合边界、输出辅助张量、FLOPs不同。页面保持中性算子名，内部先定义规范工作负载，再给各方法转换。此前FlashAttention入口差异见接入记忆；本次未修复或重新穷尽验证。转置、layout、精度、mask等实际支持范围需校验。
5. **近似转换透明**：TileSim适配中包含补输入/输出、dtype改写、shape展平和padding等。只有等价转换才能直接参与比较；近似转换须保留变更说明，无法保证等价的组合先禁用。
6. **详情来源隔离**：TileSim适配器只保存result['latency']，现有update_sim_result只更新总耗时/backend/confidence，其余字段可能是零默认值或此前Roofline值。不能当作TileSim计算/访存分解或测得瓶颈。缺失输出变为null，不能画假流水；算子逻辑工作量可独立计算并标明来源。后续取得本体才能核实可扩展的细项。
7. **测量参考**：run_op_sim中的profiling_hit对Roofline也可能为true，推理schema也有true默认值；不能作为测量来源凭证。没有同契约真机参考就只显示总耗时，偏差为null。模型调用产生的是预测，仍区别于设备实测。
8. **OpScope接入改动**：需要运行状态、批次绑定、配置摘要校验、结构化结果转换和安全展示；现有details HTML仅可信fixture，不能接受外部HTML。comparison_issues目前刻意拒绝非fixture比较，需正式契约校验替换；图表尺度由后端按本批数据重新生成。真实评估与方法3/4示例分开，不能沿用固定synthetic=true或用演示参考算误差。

## 建议路径（未实施）

采用可选的本地服务模式：浏览器→OpScope评估服务→规范化工作负载→Roofline/TileSim/测量数据适配器→统一结果→矩阵、图表、浮层、JSON。服务同时提供页面，避免file://直连Python及跨域配置问题；导出的离线HTML继续可直接查看。

第一阶段仅做Roofline最小闭环：从MatMul、BMM、RMSNorm、Softmax及已核对硬件起步，按组合显示未运行/运行中/成功/失败/不支持。原FlashAttention先核对输出与计时边界，再纳入严格比较。仅有形状元数据的预测不要求本机有目标GPU/NPU。

开发阶段允许显式配置外部modeling路径并固定版本，使用其已验证Python环境运行小型worker，避免复制整个Web、身份、数据库及模型训练系统。这只是可选开发依赖，不把个人绝对路径写入OpScope发布要求。长期将实际依赖闭包及硬件资产整理为可版本化计算包；依赖清单需实际导入验证，不能假定单拷贝roofline.py即可独立运行。

第二阶段取得TileSim本体与环境，先校验一个准确硬件+一个MatMul的纯TileSim结果，再逐步扩展算子和dtype；每项登记支持条件、近似转换和实际返回字段。第三阶段引入可追溯Profiling参考与可比性验证。

离线备选：Python CLI预计算→标准结果JSON→build生成含实际预测的单文件HTML；比在线服务改动小，但更改参数后仍需重新计算/生成，不能实现页面点击即运行。

## 源码依据

- [单算子构造与执行](../../modeling/backend/web/services/train/op_sim.py)
- [Roofline公式与执行](../../modeling/backend/simulator/backends/roofline.py)
- [TileSim适配](../../modeling/backend/simulator/backends/tilesim.py)、[硬件与输入转换](../../modeling/backend/simulator/backends/utils.py)
- [策略](../../modeling/backend/policy_model/priority_model.py)、[缓存](../../modeling/backend/simulator/cache.py)、[结果字段](../../modeling/backend/simulator/result.py)
- [Kepler采用与回退](../../modeling/backend/inference/kepler/engine/layers/op_base.py)、[推理Web结果](../../modeling/backend/web/services/infer/op_sim.py)
- [OpScope当前结构](../ARCHITECTURE.md)、[历史接入记录](../.agent/integration.md)

上述跨仓库链接仅作本机审计定位，不是OpScope离线运行依赖；TileSim内部实现、完整算子/硬件覆盖、精度、实际采集和部署依赖仍未验证。
