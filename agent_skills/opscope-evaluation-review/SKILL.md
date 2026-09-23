---
name: opscope-evaluation-review
description: Diagnose anomalous OpScope evaluation results or validate changes to performance formulas, worker routing, result fields, and comparisons. Use static, runtime, and output evidence; skip presentation-only edits.
---

# OpScope 评估结果核验

## 何时使用

用于“两个结果为何相反”、延迟/FLOPs/字节异常、方法选路或硬件映射变化，以及结果详情/导出字段口径变更。只改颜色、文字或布局时使用 UI 定向验证即可。本 Skill 核验**模型内部一致性**；没有同边界真机参考时，不能称为预测精度校准。

先读 [数据口径](../../.agent/data-semantics.md)、[架构](../../ARCHITECTURE.md) 和相关方法的覆盖文档。无需原 modeling 仓库；若拿它作对照，记录版本、输入和方法差异，不把上游结果当 OpScope 的运行依赖。

## 三层核对

1. **静态输入与资产。** 固定算子内部模板、输入形式、所有张量 shape/dtype、属性实际值、执行选项、硬件正式型号及方法。核对 `configuration_hash`、资产/硬件来源、公式单位、输出边界。对比两条结果时先确认相同工作负载与可比性；方法、硬件同时变化或借用模型时不要直接给加速比。
2. **运行时选路。** 检查 `evaluation_contract.py` 的规范化、`engine_worker.py` 或 `tilesim_worker.py` 的实际分支、`tilesim_contract.py` 的支持条件和硬件映射。确认结果记录的 `backend`、`engine.mode`、版本/配置哈希与真正执行的路径一致。缺轴、缺规格、超预算、模型报错必须归入各自状态；不可静默采用别的方法或近似硬件。
3. **结果与展示。** 以同一请求实跑代表组合，核对输出 shape/dtype、FLOPs、逻辑读写字节、原始总时延与 `evaluation_results.py` 的外层、详情、比较和 JSON 一致。计算/访存分项与活动流水可能重叠；`null` 是未知，0 是合法数值。TileSim 理论/成本路径没有流水时不构造事件；合成示例保持 `synthetic=true`，模型预测保持 `measurement=false`。

## 证据与判定

记录请求摘要、硬件/引擎身份、每层观测到的具体值与状态，以及差异首次出现的位置。数值测试使用明确期望值和合适容差；反例必须能使错误实现失败。大范围变更可用 `tools/audit_evaluations.py` 和定向补充审计，但区分“前置不支持”“实际执行成功”“执行失败”。

只有具备独立真机数据、相同算子/kernel 边界、shape/dtype、正式 SKU 与软件版本，才计算实测偏差；否则结论限定为契约、选路和模型数值一致。报告保留未验证项，不以 API 200、能力探测或没有异常代替结果验收。
