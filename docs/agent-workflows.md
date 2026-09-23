# OpScope 项目级 Skill 设计

## 目标与边界

将新增算子、核验评估结果、接入硬件档案三个重复且容易静默出错的工作流固化为仓库内的 `agent_skills/<name>/SKILL.md`。Skill 只描述本项目的判断依据、文件入口、验证和交付；不依赖原 modeling 仓库、个人目录、任务数据库或真机数据，也不授权提交、推送或发布。

原 modeling 的 `create-builtin-operator`、`calibrate-infer-model-accuracy` 和硬件能力规格是参考。原项目的 Kepler 模型类、校准桶、TP/EP/offload、数据库资产与 GitCode 发布流程不属于 OpScope 当前能力，不搬入新 Skill。

## 分工

| Skill | 触发 | 核心检查 | 不适用 |
| --- | --- | --- | --- |
| `opscope-operator-onboarding` | 新增算子或给现有算子增加方法适配 | 算子语义、张量/属性、公式、方法能力和实际执行 | 纯 UI 或纯硬件变更 |
| `opscope-evaluation-review` | 数值异常、结果字段或评估公式变化 | 静态配置、运行时选路、结果/导出三层一致性 | 仅改变文字或颜色 |
| `opscope-hardware-profile` | 新增/修正硬件规格或 TileSim 映射 | 正式型号、单位、来源、方法独立性及缺失状态 | 仅调整筛选器外观 |

三者可组合使用。算子接入后若更改性能公式或结果口径，同时运行结果核验；硬件规格改变后同样核验受影响的算子。能力规格与测试保持在项目现有 `docs/`、`.agent/data-semantics.md` 和 `tests/`，不在 Skill 中复制不断变化的详细数据表。

## 项目推进与交付

modeling 的计划流程主要在 `AGENTS.md`，专门的交付 Skill 则绑定 GitCode。OpScope 使用三项职责不同的项目流程，避免重复领域 Skill 或套用 GitCode 门禁：

| Skill | 触发 | 核心检查 | 不适用 |
| --- | --- | --- | --- |
| `opscope-change-planning` | 跨模块功能、重构、公共契约或性能口径变化 | 明确范围、设计取舍、验收证据与当前文档归属 | 单点低风险修正 |
| `opscope-change-record` | 每个已完成的仓库文件修改任务 | 在 `docs/CHANGES.md` 留一条实际结果、验证与剩余限制 | 只读调查与中间保存 |
| `opscope-git-delivery` | 用户要求分类提交、推送或创建 PR | 从实际差异选文件、按职责分组、验证提交与远端状态 | 只读审查或普通编码 |

变更记录按**逻辑任务**而非文件保存次数填写；重大变更仍需设计/计划，稳定事实仍归项目记忆，提交记录归 Git。三个 Skill 不要求创建新任务、额外审批或一律发 PR。提交/推送/发布行为仍以用户已授权的范围为准；Skill 本身不扩大授权。当前工作树包含未跟踪的生产文件，不能采用 modeling 的“默认忽略未跟踪文件”或“冲突时一律覆盖本地”规则。

## 实施计划

- [x] 创建三个带 `name`、`description` 和明确适用边界的 Skill。
- [x] 在 `AGENTS.md` 加入触发入口，并在文档导航登记。
- [x] 用 skill-creator 的 `quick_validate.py` 检查结构，再核对链接、项目文件路径和现有工作树不受影响。
- [x] 创建并登记两项项目管理 Skill，保持与现有 `AGENTS.md` 分工清晰。
- [x] 增加按任务记录的 Skill 与 `docs/CHANGES.md`，不回填无法逐项核实的历史任务。
- [x] 校验新增 Skill 结构、链接及差异格式。

这次只增加工作流文档，不调整计算代码或现有测试结果。

## 验证

六个 Skill 均通过 `quick_validate.py`。检查仓库内相对链接、Skill 触发入口与 `git diff --check`；没有安装依赖、调用外部服务或修改 modeling。使用 Skill 时按实际任务选定定向测试；本轮只有文档变更，不重跑评估矩阵。
