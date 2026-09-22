# Python 目录整理

## 目标

根目录只保留用户直接运行的 `build.py`、`serve.py` 和启动脚本。业务实现放入
`opscope` 包，测试放入 `tests`，使离线构建、在线评估和测试的边界可直接从目录看出。

## 目录

```text
opscope/
├── offline/       # 示例数据、详情、矩阵预处理和单文件构建
└── evaluation/    # 请求契约、结果转换、worker 与运行时
tests/             # Python 和离线 JavaScript 测试
build.py           # 兼容入口，委托给 opscope.offline.build
serve.py           # FastAPI 兼容入口
```

`backend/web` 保留宿主和路由，只从 `opscope` 包导入业务能力。worker 仍以独立脚本
启动，以保持外部 Roofline/TileSim 解释器隔离；worker 同时支持包内导入和直接脚本执行。

## 兼容和验证

- `python3 -B build.py` 与 `python3 -B serve.py` 继续有效。
- 离线构建始终以仓库根目录读取 HTML/CSS/JS，并写回根目录 `index.html`。
- Python 测试入口改为 `python3 -B -m unittest discover -s tests -p 'test_*.py' -v`。
- CI、README、架构文档及项目记忆同步更新；迁移后重建页面并运行 Python、Node、Vue 检查。
