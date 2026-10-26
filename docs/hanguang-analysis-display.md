# 含光分析字段与展示设计

依据：2026-10-13 核对同级 hanguang 的 `api/common/response_models.py`、`api/performance_analysis/models.py`、`engines/mock.py` 和公共 analyze_performance 调用。当前是 Python API；HTTP、真实分析引擎尚未实现。OpScope 本轮仅调整示例与展示，不依赖该仓库运行。

## 字段映射

| 返回字段 | 展示 |
| --- | --- |
| performance.latency_us | Kernel 总耗时，μs；沿用现有结果 |
| performance.cycles | 总周期；无明确计数保持 null，不按假定频率换算 |
| metrics.l2_cache_hit_rate / mfu / ub_utilization | L2 命中率、MFU、UB 利用率；0–1 转为百分比 |
| pipe_cycles.components | AIC MAC/MTE1/MTE2、FIXPIPE、AIV VEC/MTE2/MTE3 的多核平均周期；逐项数值，不求和、不换算成时间占比 |
| trace.format / trace.file | Trace 格式与产物状态；有文件不代表已有事件内容或下载服务 |
| hardware / software / workload / implementation | 输入、硬件与实现上下文；未来适配保留版本、布局和实现身份 |

## 页面安排

矩阵单条详情在概览补充资源指标，在执行过程补充流水组件周期；双结果按相同字段对齐，缺项为“—”，不做混合周期的加速结论。现有结果选择即 A/B 对照，本轮不新增历史时间查询或恢复时间选择区。

性能优化用 L2/MFU/UB 替换“资源压力”主展示，保留最终瓶颈、局部流水和优化方向。MegaKernel 增加基线与当前实现的资源/流水对照，选中实现或更换基线时联动。后两页不展示引擎或方法选择。

Python 统一准备百分比、格式、条宽和空值。新增结构化 analysis 子集与 analysis_view；fixture 保留 synthetic，现有时延不替换为含光固定 mock 的125.6μs。NPU组件和UB只出现在NPU示例；GPU保留不适用/未提供。含光目前不直接给统一瓶颈、优化建议、融合收益或跨实现扫描，这些继续是OpScope预设展示，不能描述为接口已有结论。

验收覆盖比例转换、零/缺失、组件不相加、GPU边界、原时延一致、配置切换清空，以及单条/双条、诊断与MegaKernel联动。同步三页demo、设计交接和原生矩阵生成文件。

### 展示补全与文案精简（2026-10-14）

用户要求补全展示数据后，NPU合成示例显式设置sample_clock_mhz=1500，周期按latency_us×clock_mhz生成并标为“等效周期”，不是实测总周期，也不是型号规格；默认无时钟时仍为null，真实引擎不补值。AnalysisPanel集中展示耗时/等效周期/资源指标，组件平均周期仍独立、不相加。MegaKernel沿用预设traffic_mib，Python计算读写吞吐GB/s=MiB×2^20/μs/1000；不是新增硬件计数器。UI删除重复操作说明、装饰英文及页脚演示说明，保留全局示例、导出synthetic、单位、缺失原因和关键比较限制。详情的演示解释移入已有来源记录折叠区。
