# 仓库分层与纯前端入口

## 当前边界与整理方案

当前交付是三页 Vue 前端和两个独立 HTML，默认开发、构建、预览均使用本地预设 JSON。整理顺序为统一启动入口、区分工具与历史代码、更新文档导航和 CI，最后验证测试及三类构建。不改变数值口径、不删除已有业务模块。

## 目录职责

| 层 | 位置 | 使用方式 |
| --- | --- | --- |
| 当前前端 | `frontend/src/`、`frontend/tests/` | 日常开发与验证 |
| 当前展示产物 | `opscope-demo.html`、`opscope-ui-design.html` | 从前端源码生成，可独立分发 |
| 共用资源 | `styles.css`、`configuration.js`、`data/` | 仍被前端或构建工具引用，保留原位置 |
| 可选数据生成 | `build.py`、`opscope/offline/` | 修改示例规则时运行 Python；页面运行不依赖 Python |
| 历史服务与模型 | `backend/`、`opscope/evaluation/`、`vendor/` | 不在默认运行路径；部分契约仍被离线生成器引用 |
| 历史原生页面 | `app.js` 等根目录 JS、`index.html`、`demo.html` | 旧单页实现及生成产物，不作为三页应用入口 |
| 历史运行脚本 | `tools/legacy/` | 显式启用历史集成环境时使用 |

不批量搬动 Python 包和根目录共享文件，避免破坏导入路径及旧生成链路。历史文档汇总到[历史索引](legacy-index.md)，旧审计中的支持范围不代表当前前端已连接引擎。

## 模式与依赖

默认 `development`、`production` 及单文件 `demo` 模式均启用本地数据和 hash 路由。Vite 只在显式 `integration` 模式启用 API 代理；这是保留的历史兼容入口，不属于当前前端交付验收。

原安装和启动脚本保存在 `tools/legacy/setup-backend.sh`、`tools/legacy/start-backend.sh`。需要恢复历史集成验证时先阅读脚本帮助和[原环境说明](environment.md)，不要把该环境作为前端开发前置条件。历史文档中的根目录脚本路径应按上述路径替换。

## 验收

- Node 环境可独立完成前端测试、默认静态构建和两种单文件构建。
- 默认入口加载预设结果，无需 API 服务；全局示例标记与导出 synthetic 保留。
- shell 启动脚本语法与参数检查通过。
- Python 生成逻辑改动时另行运行 `.venv/bin/python -B -m unittest discover -s tests -p 'test_*.py' -v` 和 `python3 -B build.py`，之后重新生成两种单文件。

当前不更改模型计算、结果合同和导出语义；未来接入服务应另立设计与验收，而不是静默切换默认数据来源。
