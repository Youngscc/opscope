---
name: opscope-hardware-profile
description: Add or correct OpScope hardware catalog entries, Roofline specifications, or TileSim hardware mappings. Use when chip identity, precision peaks, HBM bandwidth, simulator parameters, or borrowed-model provenance changes; skip filter-only UI edits.
---

# OpScope 硬件配置接入

## 适用边界

用于新增/修正硬件型号、Roofline 数值规格、TileSim 模型映射或缺失原因。硬件**出现在目录**、**具备 Roofline 规格**、**具备 TileSim 模型**是三个独立事实；不能因为其中一项存在就开启另两项。先读 [项目约束](../../AGENTS.md)、[数据口径](../../.agent/data-semantics.md) 与 [现有覆盖](../../docs/modeling-coverage-plan.md)。

## 取证与落地

1. **确认身份。** 记录厂商、正式 SKU、Server/POD 或整卡边界、版本和规格来源。相似名称不自动归并；借用模拟器配置应标 `borrowed_from`，不得展示成该 SKU 的独立认证结果。所有数值记录单位与是否为整卡或单核。
2. **逐方法查缺项。** Roofline 核对所需 Cube/Vector 对应 dtype 峰值、整卡 HBM 带宽和可用效率口径，资产在 `opscope/evaluation/data/roofline_hardware.json`，解析见 `bundled_roofline.py`。TileSim 核对 `tilesim_contract.py` 映射、模型模式及固定版本 wheel 自带的 `core/config/arc_config` 参数；实际读取见 `tilesim_worker.py`。TileSim 的片上带宽或核心配置不能替代 Roofline 的整卡规格；不要推断 BF16=FP16 或用其他型号参数填空。
3. **维护来源。** 目录快照 `data/modeling-catalog.json` 可由 `tools/snapshot_catalog.py` 从可用且受跟踪的来源刷新；日常运行不依赖该来源。需要变更 TileSim 包内配置或版本时，先明确供应来源、许可证与可复现安装方式，不能直接修改已锁定 wheel 后仍沿用旧版本身份。更新硬件/配置摘要，使既有结果快照不被新规格悄悄重释。
4. **同步契约与界面。** 核对 `opscope/offline/catalog_data.py` 的目录入口、`evaluation_contract.py` 的标识、`tilesim_contract.py` 的映射及结果 `hardware_snapshot`。缺项写明确原因并保持 `unsupported`；规格为真实 0 与未知 `null` 不混用。若允许跨硬件比较，先检查是否借用模型且边界一致。

## 验收

为新增规格写具体数值/单位、来源身份、对应方法成功与缺字段不支持的测试；以代表算子在本项目 `.venv` 中实际运行 Roofline/TileSim，各自核对数值有限性、模型身份和模式。检查卡片、详情及 JSON 中显示的正式型号、借用标记与原因一致。更新 [覆盖记录](../../docs/modeling-coverage-plan.md)；缺少可信规格时，交付“仍缺哪些字段”比填一个可运行但错误的数值更正确。
