---
name: opscope-change-planning
description: Scope and execute substantial OpScope changes involving multiple modules, public contracts, architecture, or performance semantics. Use for design and implementation planning; skip small, low-risk corrections.
---

# OpScope 改动规划

## 何时使用

用于跨前后端的功能、较大重构、API/核心数据结构、算子性能口径或依赖方向变更。单点展示、文字、明显无用配置清理按 [AGENTS.md](../../AGENTS.md) 做定向修改和检查即可，无须为流程而写计划。若任务涉及算子、结果或硬件，按 [项目级 Skill 分工](../../docs/agent-workflows.md) 同时阅读对应领域 Skill。

## 先确定现状与边界

读 [架构](../../ARCHITECTURE.md)、[项目记忆](../../.agent/MEMORY.md) 和相关当前能力文档；用 `git status --short` 识别已有修改与未跟踪文件。区分用户本次目标、已有工作和历史记录，不因未提交就忽略生产文件，也不把上游 modeling 当运行依赖。

把方案写入 `docs/`，只记录会影响实现选择的内容：当前问题、预期行为、模块/数据流、不能改变的不变量、缺失时的状态、可验证的验收条件和已知限制。较大改动再附文件级实施清单与顺序；小范围改动不复制模板或制造空文档。改变性能公式/硬件身份/结果契约时，同步更新当前能力说明和不变量测试；历史计划保留为过程记录，不能取代当前事实源。

## 实施与收口

按依赖顺序做可检查的小步；跨前后端时先确定后端规范化与结果口径，再接展示。生成型 `index.html` 只通过 `python3 -B build.py` 更新。测试选能证明目标行为的具体数值、状态和反例；核心链路要实际跑本项目 `.venv` 中的评估，并检查卡片、详情、比较与 JSON。缺少模型或规格应保持不支持，不能靠虚拟值让验收变绿。

完成后对照原目标逐项写出已实现、已验证、仍缺信息或外部依赖；更新 `.agent/MEMORY.md` 中稳定事实。用户尚未授权的提交、推送、PR 或部署不因为计划列出就自动执行；若已授权，继续完成，不重复请求确认。
