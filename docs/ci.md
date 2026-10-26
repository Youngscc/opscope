# 持续集成

默认 CI 面向当前纯前端交付：Ubuntu、Node.js 24，使用 `npm --prefix frontend ci` 安装锁定依赖，然后运行前端测试、Vue 类型检查及静态站点构建、完整展示 HTML 构建和设计交接 HTML 构建。无需 Python、后端服务或引擎环境。

工作流在 push、pull_request 和手动触发时运行，仓库权限仅为 contents: read，checkout 不保留凭据。同一分支或 PR 的新运行取消旧运行，超时为 10 分钟。工作流不提交产物、不推送或部署。

本地复现命令见[README](../README.md)。修改 Python 生成规则时，仍应手动执行对应 Python 测试并重新生成产物，见[仓库分层](repository-layout.md)。默认 CI 不覆盖历史集成服务或真实引擎。

本轮本地验证结果记录在[变更记录](CHANGES.md)；GitHub 托管执行需推送后确认。
