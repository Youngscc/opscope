# OpScope Agent 工作指引

## 开始工作

1. 阅读本文件、[项目记忆](.agent/MEMORY.md)和 [ARCHITECTURE.md](ARCHITECTURE.md)。
2. 修改数据时读 [.agent/data-semantics.md](.agent/data-semantics.md)；接入后端时读 [.agent/integration.md](.agent/integration.md)。
3. 这是独立项目，不能假设存在原 modeling 仓库、数据库、凭据、个人 Skill 或开发服务。记忆中的原项目审计是历史背景，不是本项目能力。

## 项目级 Skill

Skill 保存在 `agent_skills/`，按任务选择并阅读；用户指令和本项目数据口径优先。它们只依赖本仓库，上游 modeling 可作为额外对照，不是运行前提。

- 新增算子或扩展方法适配：[算子接入](agent_skills/opscope-operator-onboarding/SKILL.md)。
- 核查异常结果、公式或结果契约：[评估核验](agent_skills/opscope-evaluation-review/SKILL.md)。
- 新增/修正硬件规格或映射：[硬件配置](agent_skills/opscope-hardware-profile/SKILL.md)。
- 跨模块功能、重构或公共契约变化：[改动规划](agent_skills/opscope-change-planning/SKILL.md)；单点低风险改动沿用简化流程。
- 每个完成的仓库文件修改任务：[变更记录](agent_skills/opscope-change-record/SKILL.md)，在 `docs/CHANGES.md` 留一条最终记录；只读任务不记。
- 用户要求提交、推送或 PR：[Git 交付](agent_skills/opscope-git-delivery/SKILL.md)。

一项任务跨这些边界时组合使用，不因文件名相近就全量套用。

## 产品约束

- PC 优先、简洁直观；外层关键比较，点开看细节。标签和数值保持靠近。
- 不恢复重复实验的样本分布、p50/p95、直方图。单次执行的核活动/流水是另一类信息，可以保留。
- Roofline 只有一个方法，校准是结果元数据；不要自动恢复成两个方法。
- 合成数据必须保留全局“示例数据”与导出 synthetic 标记；未连接实际来源前，禁止冒充真实测量。
- 缺失用 null / “—”或原因表示；零值是合法值。未知型号和未验证支持不能自动填为已支持。

## 实现与验证

- 修改源文件后用 `python3 -B build.py` 生成 index.html，不直接修改生成文件。
- Python 负责性能口径、数值、聚合、图宽等预处理；JS 负责选择、筛选和展示。后续在线化时计算放在后端。
- 在线应用使用 Vue 3/TypeScript/Vite/Pinia/Vue Router 与 FastAPI/Uvicorn，保持与 modeling 同栈；原生 HTML/CSS/JS 离线导出保留。引入其他依赖前说明必要性与影响。
- 保持既有命名和格式；新增函数尽量不超过 50 行、参数不超过 5 个，注释解释必要的原因。
- 小范围展示调整采用定向检查；新增功能、接口或核心数据结构先写 docs/ 设计与计划，更新架构和相关测试。
- 改变性能公式、硬件身份、方法边界或结果口径时，同步更新对应的持续维护能力说明及不变量测试；改变模块分层或依赖方向时，在设计文档中记录取舍。历史计划不能替代当前有效的能力说明。
- 数据测试要核对具体数值、状态和缺失语义，测试注释说明观测点。
- 常用验证：`.venv/bin/python -B -m unittest discover -s tests -p 'test_*.py' -v`、`npm --prefix frontend test`、`npm --prefix frontend run build`；离线 JS 运行 `node --check app.js`。
- UI 改动检查桌面布局、筛选、详情、双结果比较和 JSON；不要把临时手机视口留给用户。不能运行的检查必须明确记录。
- 不自动删除用户文件、添加远程、推送、部署或发布；用户已授权的任务直接完成，不反复确认。

## 更新记忆

完成后更新 .agent/MEMORY.md；稳定语义放专题文件。区分已实现、已验证、历史发现、待验证。只保存与本项目相关的信息，不写凭据或无关用户数据。所有文档内部引用使用相对路径。

每次完成仓库文件修改还应按[变更记录 Skill](agent_skills/opscope-change-record/SKILL.md)更新 `docs/CHANGES.md`。一项任务只留一条，不为每次中间编辑单独记；它不代替设计文档、项目记忆或 Git 历史。
