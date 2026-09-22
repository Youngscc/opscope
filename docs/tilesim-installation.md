# TileSim 本地独立安装

2026-09-22，用户授权安装。采用官方文档发布的 `msopmodeling==1.0.9` wheel，源码仓库的匿名克隆要求认证，改用包安装。

## 安装边界

安装位置为外部 modeling 项目内的 `tilesim-runtime/.venv`，不修改原 `.venv`。该包固定 NumPy、Pandas、SciPy 等依赖，单独环境可避免影响现有 Roofline 服务。目录匹配原 modeling 的 `tilesim*` 忽略规则，不随 OpScope 交付。

此步骤只安装并验证引擎；现有 OpScope 服务仍使用原解释器，不自动接入新环境。后续接入需独立进程、显式解释器配置、请求/结果契约转换、硬件白名单和测试，不能简单替换原解释器或共享包路径。

## 已确认的兼容性差异

- 1.0.9 的 `op_latency_predict` 返回 `(结果字典, 优化建议列表)`；modeling 旧适配器按字典读取，不能直接连接。
- modeling 的 `build_tilesim_input` 固定 `backend_type=theo`，不是 `eng` 工程级仿真。
- 包中带有芯片 YAML 不代表对应硬件已获验证。已有 Ascend9382→910B4 及多个 GPU→H200 的旧映射不能直接复用。

## 验证计划

- [x] 完成隔离环境安装并执行 pip check。
- [x] CLI 帮助和直接 API 导入。
- [x] 910B1 MatMul 工程模式单次预测，保存输入/原始输出。
- [x] 记录实际版本、依赖锁定和验证结论。

## 验证结果与使用

Python 3.11 独立环境安装 `msopmodeling==1.0.9` 成功，`pip check` 无冲突，CLI 帮助与理论/工程 API 导入正常。SciPy 1.15.3 默认 macOS 14 ARM64 wheel 在本机出现 Mach-O `__thread_bss` 加载错误；替换为同版本 `macosx_12_0_arm64` wheel 后成功，未修改第三方源码或放宽依赖版本。

从 modeling 目录执行：

```sh
MPLCONFIGDIR=/tmp/opscope-tilesim-mpl XDG_CACHE_HOME=/tmp/opscope-tilesim-cache \
  tilesim-runtime/.venv/bin/msopmodeling \
  -i tilesim-runtime/matmul-eng.json -s 910B1 \
  -o tilesim-runtime/matmul-eng-result.json
```

输入为 MatMul `[2048,512] × [512,1024]`，FLOAT16 输入、FLOAT32 输出，`backend_type=eng`。实跑 CLI 成功，预测总时延 `10.936681071217901 µs`，CUBE `6.642162162162163 µs`、MTE2 `6.832540105999664 µs`。分项可重叠，不应相加。这是引擎可运行验证，不是真机测量或精度认证，也不证明所有硬件/算子支持。

`tilesim-runtime` 保存输入、原始 JSON、运行日志、`requirements.lock` 和 `installation.json`（wheel SHA256、版本、引擎路径及验证状态）。安装包和安装日志保留在 `tilesim-install`。两目录都是本地外部依赖，不纳入 OpScope 源码。

当前 8768 服务仍使用原 modeling `.venv`，其 TileSim 缺失状态指所配置的解释器；本次没有更改服务、旧适配器或硬件映射。公开版本的工程模式使用单独的 `op_latency_predict_engineering` 接口，后续应显式接入，不能只更改导入路径。

## 流水导出核查（2026-09-22，已实跑）

1.0.9包含两条不同的工程实现：CLI的eng选择 `op_latency_predict_engineering` 汇总预测；DSL `EngMatmulL0` 经 `EngineeringOperator`→规则流水评估器产生 `OperatorResult.trace`。后者事件带name/ts/dur/pid/tid，格式为Chrome Trace `traceEvents`；Optim内部也写trace.json，但多候选循环会覆盖文件，后续接入应直接取所选结果的trace，不能盲读最后文件。

直接调用DSL MatMul，910B1、24 AIC、FP16输入/FP32输出、[2048,512]×[512,1024]、单候选tm128/tn256/tk1=256/tk0=64，成功输出1736事件、24个核、CUBE/AIC_MTE1/AIC_MTE2/AIC_FIXPIPE四种通道，预测8.559025912870776µs。保存于外部tilesim-runtime/matmul-dsl-trace.json，复现脚本verify-dsl-trace.py。事件时间非负且duration>0核对通过。

该预测与此前CLI工程路径10.936681µs属于不同模型实现，不可把流水嫁接到CLI汇总结果。事件是Tile操作级模拟，不是真机指令采样；尚未验证其他算子/硬件的流水支持，未接OpScope UI。
