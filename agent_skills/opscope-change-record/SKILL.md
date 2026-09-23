---
name: opscope-change-record
description: Record each completed OpScope repository-changing task in docs/CHANGES.md, including its outcome, scope, verification, and remaining limits. Use for code, configuration, UI, test, documentation, and Skill changes; skip read-only work.
---

# OpScope 变更记录

每个**已完成的仓库文件修改任务**都在 [变更记录](../../docs/CHANGES.md) 留一条。一个任务多次编辑、修正和验证，只写一条最终记录；后续任务再修改相同文件，另写一条。只读调查、答疑、临时文件和未落入仓库的实验不记。与设计文档、项目记忆、Git 提交各司其职：这里记录本次实际改变，设计文档记录重要方案，`.agent/MEMORY.md` 保存长期有效的事实。

## 收口时填写

在实现及必要验证完成后，基于本次实际差异，在 `docs/CHANGES.md` 顶部日期区按任务新增条目，包含：

- 一句具体的结果与动机；
- 涉及的主要模块或文件，使用仓库相对链接；
- 实际完成的验证及结果；
- 尚未完成、未验证或依赖外部信息的边界。无实质限制可省略。

条目应让不在场的维护者理解改动和证据，不复制整段会话、原始日志或大段 diff。只记**本次触及的内容**，不得把工作树里先前的未提交文件误写为本次成果；不写凭据或个人环境路径。失败检查要记录真实状态，不能称为通过。用户明确要求不留记录时遵从用户指令。

这条记录不代表代码已提交、推送或发布。只有实际完成 Git 操作后才补充对应提交号或 PR；记录本身不授权这些操作。变更记录与本次文件修改一起进入后续用户授权的交付范围。
