# 数据口径

## 工作负载与外层

- MatMul M=N=K=4096，FP16 输入/输出、FP32 累加；逻辑 FLOPs=2MNK=137438953472。
- 逻辑字节=(MN+MK+KN)×2=100663296 bytes=96 MiB；不是实际 HBM 流量。
- latency_us 为设备侧单 kernel 总耗时，单位 μs。有效算力=逻辑 FLOPs/总时延，单位 TFLOP/s，不是峰值利用率。
- 偏差=(方法耗时−同硬件 Profiling 参考)/参考×100%；短于参考并不代表更准确。当前参考本身也是合成数据。
- 时间图共用 320 μs 尺度，有效算力共用 2400 TFLOP/s 尺度。真实数据接入时需重新设计范围，不可直接套用固定上限。
- 外层与详情/导出共享同一数据源；实际流量、带宽、缓存命中、资源活动仅在相应示例记录中存在。

## 不同方法能展示什么

| 方法 | 当前示例 | 必须保留的边界 |
| --- | --- | --- |
| Profiling | 耗时、计数器、活动与流水 | 全部合成；并未采集真机 |
| Roofline | 总耗时、可用的计算/访存成本、校准元数据 | 不生成实际计数器、kernel 或 trace |
| Tilesim | 总耗时与详细执行示例 | 细项标“扩展字段示例”，不是原适配器真实输出 |
| Accel-Sim | H100/H200 的详细执行示例 | 本包未运行模拟器；不适用于昇腾，Blackwell 支持未验证 |

Roofline 校准 status=calibrated/generic；source=bucket/aggregate/regression/heuristic。H200 演示 regression，compute_us、memory_us、bound 为 null，不从总时延虚构分项；其他解析示例的成本也不是真实模型计算。

## 单次执行与缺失

计算活动、访存活动、等待可以重叠，不能强制相加成总时延。局部流水仅 12 个事件，核活动仅 24 个示意实例，均不是完整 trace 或实际硬件核数。Cube/Vector 与 Tensor/SIMT 使用各自原生口径，不能直接当同定义计数器横比。

available=false 表示组合缺失，reason 保留原因；零耗时/零比例与 null 不等价。R200 正式型号仍待确认。synthetic 标记在整个 payload 与各结果保留。

当前 schema 为 operator-ui-demo-v1，是展示私有结构，不保证兼容实际 modeling 的 SimResult。导出仅当前筛选结果，剔除 details HTML，保留 execution、校准来源与缺失值。
