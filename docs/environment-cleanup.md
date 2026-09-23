# 环境配置清理

2026-09-23。引擎现已随项目提供，独立启动应只使用本项目的 `.venv` 和内置数据。旧的外部 Roofline/TileSim 目录与解释器覆盖会意外选择另一套实现，造成能力检测和结果来源与当前项目不一致。

## 变更计划

1. 删除本机仅含旧引擎路径和默认端口的 `.env`，移除过时的 `.env.example`。
2. 从独立服务配置和命令行删除 `OPSCOPE_ENGINE_ROOT`、`OPSCOPE_ENGINE_PYTHON`、`OPSCOPE_TILESIM_PYTHON` 及对应启动参数；运行时默认使用当前解释器和内置后端。
3. 启动/安装脚本不再读取 `.env`。保留实际使用的端口参数、`PYTHON_BIN` 安装回退选项，以及宿主集成所需的 `VITE_OPSCOPE_API_BASE`/`VITE_OPSCOPE_BASE` 构建变量；后两项从命令环境传入。
4. 更新当前使用文档和启动配置测试，验证默认服务的 Roofline/TileSim 能力与一条实际评估。

`EvaluationRuntime` 的构造参数仍保留给宿主注入和隔离测试，不作为独立服务的环境或 CLI 配置。

## 实施与验证

上述清理已完成。本机 `.env` 经确认只含三条旧引擎路径和两个默认端口后删除；启动脚本、服务设置与 Vite 根目录配置不再读取该文件。独立服务保留 `OPSCOPE_PORT`、`OPSCOPE_FRONTEND_PORT` 的命令环境/启动参数，`setup.sh` 的 `PYTHON_BIN` 仅用于无 uv 的 Python 选择。

通过 68 项 Python 测试、3 项前端测试、Vue 类型检查及生产构建、shell 语法检查与 `git diff --check`。直接用 `./start.sh --port=8794` 启动后，健康接口返回 200，能力接口报告 Roofline/TileSim 均可用；同一 128×128 FP16 MatMul 请求在 H200 Roofline 返回 0.0512 μs、910B1 TileSim 返回 2.996023742971288 μs。临时服务已关闭。另用命令环境设置自定义 Vite base/API 地址构建并核对产物，随后恢复默认构建。
