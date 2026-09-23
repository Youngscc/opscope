# OpScope 变更记录

此处按**完成的修改任务**记录结果与验证，不按文件保存次数记流水。历史原型迭代见 [HISTORY.md](HISTORY.md)；长期项目事实见 [项目记忆](../.agent/MEMORY.md)。记录不等于已提交或已发布。

## 2026-09-23

### 优化字体层级与结果区域比例

- 在共享 [styles.css](../styles.css) 中强化耗时、硬件/方法名和分节标题的字号/字重层级，提升标签可读性；收紧详情顶部，将更多空间留给内容，调整单项摘要卡比例及双结果表格列宽。重新生成 [index.html](../index.html)，在线/离线共用样式；不修改计算或交互逻辑。
- 验证：Vue类型检查/生产构建、离线构建、14项构建与矩阵定向测试、差异格式检查通过；桌面检查矩阵、单项/双项详情、筛选、差异、JSON、长算子名称及离线双结果展示，无横向溢出，在线控制台无错误。8768已加载新静态产物，无需重启；未执行移动端检查，未提交或推送。

### 改为直接选择两张矩阵卡片比较

- 在线/离线常驻“加入对比”，标记 A/B、最多两项，取消/筛选/换选保持同步；页面移除评估时间选择区。浮窗新增同尺度总耗时图及按所选结果下载 HTML 报告，保留原始指标、不可比说明、零值与 synthetic 语义。主要修改 [ResultMatrix.vue](../frontend/src/components/ResultMatrix.vue)、[ResultDetails.vue](../frontend/src/components/ResultDetails.vue)、[矩阵预处理](../opscope/offline/matrix_data.py)、[报告路由](../backend/web/routes/opscope.py)与离线模板；见[设计](matrix-comparison.md)。
- 验证：80 项 Python 与 3 项前端测试、类型检查/构建、离线生成、JS 语法和差异检查通过；桌面选择/取消/第三项限制/筛选、单项/双项详情、差异筛选、JSON、离线页面和报告视觉验收通过。实跑 H100/H200 小型 MatMul Roofline 并下载所选结果报告成功。
- 经用户明确授权重启 8768 服务；历史接口保留但不再显示时间选择 UI。报告仍依赖服务内存快照，示例报告独立标明 synthetic。没有提交或推送。

### 修复 FP8/FP4 Roofline 峰值字段映射

- [`bundled_roofline.py`](../opscope/evaluation/bundled_roofline.py) 从已有 `_tops` 字段读取 FP8/FP4 峰值，其他浮点精度继续读取 `_tflops`；未修改硬件数值。增加目录公式回归测试，并更新[缺口地图](evaluation-gap-map.md)、[数据口径](../.agent/data-semantics.md)和[项目记忆](../.agent/MEMORY.md)。
- 验证：独立 worker 实跑 `infer:QuantBatchMatmulV3` 默认输入的 17 个非 TileSim 硬件入口，16 成功、`Adevice03_POD` 1 项因 `fp8_tops=0` 不支持、0 运行失败；Python 全量 79 项测试通过，差异格式检查通过。未重跑 9,500 格全量审计；910B1/B4 的整卡 Roofline 规格仍缺。

### 建立按任务记录的变更流程

- 增加 [变更记录 Skill](../agent_skills/opscope-change-record/SKILL.md)，并在 [AGENTS.md](../AGENTS.md) 与[项目级 Skill 分工](agent-workflows.md)中规定：每个完成的仓库文件修改任务留一条实际变更、验证和限制记录。既有设计文档与项目记忆继续承担各自职责。
- 验证：Skill 结构校验、文档链接和差异格式检查。此轮只改工作流文档，未更改评估计算或页面行为；未回填此前任务的流水，也未提交或推送。
