---
name: opscope-operator-onboarding
description: Add an operator or extend Roofline/TileSim support for an existing OpScope operator. Use for tensor contracts, operator attributes, formulas, method adapters, and coverage changes; skip UI-only and hardware-only edits.
---

# OpScope 算子接入

## 适用边界

用于新增算子、合并等价目录入口，或让现有算子在 Roofline/TileSim 新路径上运行。纯样式调整、仅改硬件规格、真机 Profiling 接入不属于本 Skill。先读 [项目约束](../../AGENTS.md)、[数据口径](../../.agent/data-semantics.md)；涉及跨模块契约时读 [架构](../../ARCHITECTURE.md)。

OpScope 必须在没有原 modeling 仓库的环境里运行。上游源码若可获得，可用它核对并通过 `tools/snapshot_catalog.py`、`tools/snapshot_operator_specs.py` 刷新受跟踪资产；常规运行和验收只依赖本仓库。不要把上游训练/推理标签、Kepler 校准桶或完整模型图流程搬入页面。

## 接入判断

1. **确定语义边界。** 写清数学操作、融合范围、是否单 kernel、输入/参数/输出张量的角色与顺序、shape/dtype/layout、影响结果的属性实际值。名称相似或多一个 batch 轴不足以证明等价；若仅张量契约不同，保留一个可见算子及不同“输入形式”，内部模板身份继续独立。未知轴、排列、量化值或维度保持未知。
2. **分别裁决方法。** Roofline 的公式、输出与单位在 `opscope/evaluation/bundled_roofline.py` 或 `catalog_roofline.py`；TileSim 的支持门槛、模式与输入映射在 `tilesim_contract.py`、`tilesim_adapters.py`、`tilesim_worker.py`。一个方法成功不证明另一个方法支持；不从 TileSim 耗时倒填 Roofline，也不静默回退。借用硬件模型要保留 `borrowed_from`。
3. **沿配置链落地。** 核对 `data/modeling-catalog.json`、`opscope/offline/catalog_data.py`、`evaluation_contract.py`、`operator_parameters.py`；属性必须参与规范化配置和摘要。若改可编辑属性，同时核对 `configuration.js` 与 `frontend/src/components/OperatorConfig.vue`，再重新生成离线 `index.html`。运行中缺项应返回原因，不用 0、默认 1 或相近算子结果填补。
4. **记录模型依据。** 对新增公式、模式或融合假设记录来源、当前可验证范围和不支持项；更新 [TileSim 覆盖](../../docs/tilesim-operator-coverage.md) 或相关能力文档。目录公式 `catalog-analytic` 只表示本地受限解析，不宣称与原 Kepler 完整图模型相同。

## 验收

- 测试至少覆盖一个正确形状的具体输出、FLOPs/逻辑字节与状态，以及一个能区分错误实现的无效形状、dtype 或属性；对 2D/3D、转置、batch、融合边界另选会改变结果的样例。不要只断言映射表里有该名字。
- 用本项目 `.venv` 实际运行新支持的算子×方法×代表硬件；核对 `actual_backend`、模式、数值有限性、详情/JSON 的来源与缺失语义。模型不可执行时保持 `unsupported` 并写明原因，不能把跳过计为执行成功。
- 相关测试命令以 `AGENTS.md` 为准。适配面很广时再运行 `tools/audit_evaluations.py` 全目录审计；不要让每个小改动都必须跑 9,500 组合。报告已验证组合与仍未验证的范围，完成代码不意味着真机精度已验证。
