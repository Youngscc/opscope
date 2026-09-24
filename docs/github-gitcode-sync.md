# GitHub 主仓到 GitCode 开发分支同步

## 目标与边界

`Youngscc/opscope` 的 `main` 是本次同步的来源；目标仅为
`YYoung_G/opscope` 的 `main`。这是指定分支的单向同步，不是整仓强制镜像。
GitCode 的其他分支、标签和原团队镜像规则不在本次修改范围。

保留原始提交 SHA、作者和历史，不重新提交文件。目标分支不存在时创建；
存在时只允许快进。目标包含来源没有的提交、网络或认证失败均中止，不能强推绕过。
同步不代表合入 GitCode 主线，也不把 GitHub PR/Issue 搬到 GitCode。

## 实施与验证计划

1. 新增 `sync-to-gitcode.yml`，仅允许当前 GitHub 仓库 `main` 的 push 或手动触发。
2. 通过完整历史检出与独立脚本，只推指定引用；同仓库串行执行，执行时获取最新 main。
3. 使用本地裸仓库验证首次创建、快进、重复同步、分叉拒绝、演练无写入、其他分支/标签保留。
4. 配置令牌后先手动演练，再正式同步，对照两端 SHA。没有实际执行不能宣称远端同步成功。

## 一次性配置

在 GitCode 创建个人访问令牌：头像 → 个人设置 → 访问令牌 → 新建访问令牌。
权限需要能读取、推送目标仓库，账号本身也必须有目标分支写权限。设置有效期，
令牌仅在 GitHub 仓库 Settings → Secrets and variables → Actions 中保存为 `GITCODE_TOKEN`。
令牌不写入仓库、远程 URL 或命令行。若认证要求用户名，可设置 Actions Variable
`GITCODE_USERNAME` 为 GitCode 登录用户名；默认沿用原项目的 `oauth2` 认证方式。

GitCode 新目标仓库需先创建，建议私有空仓库，不初始化 README、许可证或 gitignore，
避免无关初始提交导致拒绝快进。同步工作流不负责创建或删除仓库。

fork 的 Actions 需启用本次同步工作流；继承的反向同步/门禁流程不应在此 fork 中启用。
原团队 `laksjdf` 仓库的工作流保持不变。私有仓库使用 GitHub 托管 Ubuntu runner，
会使用账号的 Actions 配额；不依赖原团队的 self-hosted runner。

## 操作方式

在 Actions 选择 **Sync development branch to GitCode**，从 `main` 手动运行，
首次保留 `dry_run=true`，确认成功后取消勾选再正式运行。确认正式同步成功后，设置 Actions Variable `GITCODE_SYNC_ENABLED=true`，后续 main 的 push 自动同步。未启用时自动任务跳过，手动演练仍可执行。
失败后可重跑；若报告目标有独立提交，先合并回 GitHub 并检查，再同步。

本轮仅同步这一个分支的可达历史；不含其他分支、标签、未提交文件及独立 LFS 对象。
若未来引入 Git LFS，需另行实现对象传输，不能把引用同步当作大文件同步。

## 配置文件

- [工作流](../.github/workflows/sync-to-gitcode.yml)
- [同步脚本](../.github/scripts/sync_gitcode_branch.sh)
- [隔离 Git 测试](../.github/scripts/test_sync_gitcode_branch.py)

令牌创建参见 [GitCode 官方文档](https://docs.gitcode.com/docs/help/home/user_center/security_management/user_pat/)。
