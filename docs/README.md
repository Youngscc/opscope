# OpScope 文档导航

## 使用与运行

- [README](../README.md)：项目简介、启动方式和验证命令
- [uv 环境配置](environment.md)：从零创建 `.venv`、requirements 文件、依赖更新、启动与验证命令
- [项目级 Skill 设计](agent-workflows.md)：算子接入、评估结果核验和硬件配置的适用边界
- [环境配置清理](environment-cleanup.md)：移除旧外部引擎路径与无用 `.env` 配置
- [框架对齐](framework-alignment.md)：Vue/FastAPI 端口服务和宿主接入边界
- [本地评估设计](live-evaluation-plan.md)：Roofline 与 TileSim 的本地调用方式
- [内置引擎迁移](bundled-engines.md)：脱离外部 modeling 仓库的公式、规格、wheel 与验证边界
- [CI 说明](ci.md)：GitHub Actions 检查范围
- [打包说明](PACKAGING.md)：独立目录和发布边界
- [Python 目录整理](python-layout.md)：业务分包、稳定入口和测试位置

## 界面与数据

- [结果矩阵设计](result-matrix-design.md)：硬件×方法矩阵、图表和浮窗详情
- [任务详情](task-detail.md)：单个结果的详情字段
- [算子目录方案](operator-catalog-plan.md)：算子、输入形状和 dtype 配置
- [算子语义去重审计](operator-semantic-dedup-audit.md)：按数学逻辑、batch、布局和融合边界识别等价项
- [逐结果更新](incremental-results.md)：评估结果逐卡返回和轮询协议
- [两次评估对比](time-comparison.md)：按时间选择两批结果、同口径图表和并排详情
- [独立 HTML 报告](html-reports.md)：A/B 对比报告与单项事件明细报告的内容和边界
- [数据语义](../.agent/data-semantics.md)：缺失、合成、预测和实测的口径

## 建模与 TileSim

- [全目录算子与方法实跑审计](operator-method-audit.md)：9,500 个默认组合、环境对照、逐模板缺项与上游责任划分
- [算子适配扩展](operator-adaptation-plan.md)：目录公式 Roofline、新 TileSim 模型、算子属性和独立环境复验
- [当前评估缺口与参数位置](evaluation-gap-map.md)：逐类缺项、持久化路径、可对照的同类规格和原始审计入口
- [建模复用分析](modeling-reuse-analysis.md)：建模仓库的复用边界
- [覆盖计划与实跑记录](modeling-coverage-plan.md)：硬件映射、FlashAttention 和缺失配置
- [TileSim 接入设计](tilesim-integration-plan.md)：TileSim 进程隔离和支持范围
- [TileSim 算子覆盖](tilesim-operator-coverage.md)：算子契约、模型选择和缺项口径
- [TileSim 输出清单](tilesim-output-inventory.md)：字段、单位和占位值审计
- [TileSim 输出审计](tilesim-output-audit/)：实际输出样本、复现脚本和哈希
- [安装记录](tilesim-installation.md)：独立 TileSim 环境和依赖记录

## 历史与设计记录

- [变更记录](CHANGES.md)：按完成的修改任务记录结果、验证和限制
- [结果矩阵实施计划](result-matrix-plan.md)
- [虚拟方法](virtual-methods.md)
- [历史记录](HISTORY.md)
