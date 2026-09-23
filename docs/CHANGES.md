# OpScope 变更记录

此处按**完成的修改任务**记录结果与验证，不按文件保存次数记流水。历史原型迭代见 [HISTORY.md](HISTORY.md)；长期项目事实见 [项目记忆](../.agent/MEMORY.md)。记录不等于已提交或已发布。

## 2026-09-23

### 修复 FP8/FP4 Roofline 峰值字段映射

- [`bundled_roofline.py`](../opscope/evaluation/bundled_roofline.py) 从已有 `_tops` 字段读取 FP8/FP4 峰值，其他浮点精度继续读取 `_tflops`；未修改硬件数值。增加目录公式回归测试，并更新[缺口地图](evaluation-gap-map.md)、[数据口径](../.agent/data-semantics.md)和[项目记忆](../.agent/MEMORY.md)。
- 验证：独立 worker 实跑 `infer:QuantBatchMatmulV3` 默认输入的 17 个非 TileSim 硬件入口，16 成功、`Adevice03_POD` 1 项因 `fp8_tops=0` 不支持、0 运行失败；Python 全量 79 项测试通过，差异格式检查通过。未重跑 9,500 格全量审计；910B1/B4 的整卡 Roofline 规格仍缺。

### 建立按任务记录的变更流程

- 增加 [变更记录 Skill](../agent_skills/opscope-change-record/SKILL.md)，并在 [AGENTS.md](../AGENTS.md) 与[项目级 Skill 分工](agent-workflows.md)中规定：每个完成的仓库文件修改任务留一条实际变更、验证和限制记录。既有设计文档与项目记忆继续承担各自职责。
- 验证：Skill 结构校验、文档链接和差异格式检查。此轮只改工作流文档，未更改评估计算或页面行为；未回填此前任务的流水，也未提交或推送。
