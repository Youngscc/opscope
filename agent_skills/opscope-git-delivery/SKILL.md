---
name: opscope-git-delivery
description: Prepare coherent OpScope commits and deliver authorized GitHub pushes or pull requests from the actual working-tree diff. Use when the user requests commit, push, or PR work; skip read-only review and ordinary coding.
---

# OpScope Git 交付

## 何时使用

用户要求提交、分类提交、推送或创建/更新 PR 时使用。只读查看历史或尚未进入交付阶段时不使用。本 Skill 不自行授权远程写入；用户已经授权的提交/推送/PR 应直接完成，不重复确认。项目 GitHub 是当前远端，不能套用 modeling 的 GitCode MR 标题、双仓镜像或 tester 门禁。

## 确定交付范围

读取 `git status --short`、当前分支/远端、已暂存与未暂存差异，并检查相关未跟踪文件内容。以**本次实际实现和用户目标**确定范围：未跟踪的源文件可能是功能必需；个人设置、临时 trace、审计中间产物或用户另一项工作也可能不应提交。遇到混合改动时按文件或 hunk 精确暂存，不用 `git add -A` 碰运气，不重置、清理或覆盖用户修改。

根据职责与依赖分成可理解的提交，例如运行时/契约、界面、测试/文档。不要为了凑数量拆开同一行为的必要代码，也不要把无关改动塞进一条。标题说明具体结果，风格贴近本仓库近期提交；正文只写审阅者需要的行为、口径和验证，不复制文件清单。若 PR 描述或提交范围改变，按最终实现重写说明。

## 验证与发布

在提交前完成对应测试、构建及生成文件一致性检查，检查 `git diff --check`、暂存差异、意外大文件与敏感本机配置。提交后核对每条提交包含的文件与工作树剩余改动。推送前确认目标远端/分支及远端状态；遇到分叉或冲突先检查并非破坏性地解决，不默认强推或丢弃本地更改。创建 PR 后核对标题、目标分支、描述和验证记录。

最终报告提交 SHA、推送/PR 的实际状态及未纳入的相关改动。GitHub Actions 状态必须以真实运行结果为准；本地测试通过不能表述为托管 CI 已通过。
