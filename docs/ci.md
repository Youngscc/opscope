# 持续集成设计与验证

## 目标与计划

为在线应用及离线页面添加单个 GitHub Actions 工作流，在 push、pull_request 和手动触发时检查现有测试、JS 语法及生成页面一致性。先配置工作流，再更新开发说明，最后本地运行相同命令。

## 实现

使用 Ubuntu、Python 3.12 和 Node.js 24，单任务执行，安装 backend/requirements-dev.txt 和 frontend/package-lock.json 对应依赖。仓库权限仅为 contents: read，checkout 不保留凭据；任务超时 10 分钟，同一分支或 PR 的新运行取消旧运行。

依次从 `tests/` 发现并运行 unittest，再运行前端状态测试、Vue TypeScript检查/Vite构建、node --check、build.py 和 git diff --exit-code -- index.html。最后一步防止源文件修改后漏提交生成页面。失败时开发者本地重新构建并提交 index.html。工作流不自动修改或提交文件，不部署，不检查已移除的 SHA256SUMS。

## 验证边界

本地八项单测、JS 语法检查、构建后 index.html 无差异及 git diff --check 均通过。本机未安装 actionlint，未运行工作流专用静态检查；GitHub 托管环境的实际运行需推送工作流后确认。此次不修改页面功能，不需要重复浏览器交互验收。

2026-09-22：新增本地评估服务的无外部依赖契约/状态测试，CI检查四份JS。真实引擎通过显式外部环境在本机验证，不是GitHub默认CI依赖。

2026-09-22框架对齐：本地47项Python测试、2项前端状态测试与构建通过；真实引擎继续仅在本机显式环境验证。GitHub托管执行待推送后验证，本轮未推送。
