# 共享建模后端：当前能力与启动

2026-09-24。第一阶段已实现；宿主前端没有修改。完整迁移、全目录等价性认证和旧引擎删除尚未完成。

## 启动

先在 **modeling** 启动其现有 API 和 worker，两者使用相同数据库及配置。按 modeling 的部署说明操作；仅启动 Web 而未启动 worker，任务会停留在等待中。后端须包含本轮 `strict-operator-v1` 接口。

在 **OpScope** 根目录执行：

```bash
./setup.sh --modeling
./start.sh --modeling-url=http://127.0.0.1:8001
```

`8001` 替换为 modeling 实际后端端口。OpScope 页面仍为 `http://127.0.0.1:8768/opscope`；开发模式加 `--dev`，页面端口 5173。原服务占用 8768 时可加 `--port=8803`，不会自动重启原服务。

逐条 uv 命令（全新环境）：

```bash
uv venv --python 3.11 .venv
uv sync --python 3.11 --locked --all-groups
npm --prefix frontend ci
npm --prefix frontend run build
OPSCOPE_MODELING_URL=http://127.0.0.1:8001 .venv/bin/python -B -m backend.web
```

或使用已导出的轻量 requirements，在创建 venv 后运行：

```bash
uv pip install --python .venv/bin/python -r backend/requirements-modeling.txt
```

此文件只含 Web/测试依赖，不含 TileSim、NumPy、SciPy、Torch。pip 不会卸载环境中已有的计算包；严格轻量部署使用新 venv。`uv sync` 会同步到所选依赖集。独立模式需 `./setup.sh` 或 `uv sync --locked --all-groups --extra local-engine`，然后不设置 modeling URL 启动；两种模式由配置明确选择，远程失败不切回本地。

## 身份与部署边界

当前 OpScope 是仅限本机访问的单用户工具；继续使用 modeling 原有身份、资产可见性和任务 owner 校验。受保护的 modeling 服务需要由可信登录/网关流程取得的原有加密 `x-user-*` 头，不能填明文用户名冒充身份，也无需在 OpScope 保存解密密钥。

可以把这些已授权请求头存为仓库外的 JSON 文件（键限于 `x-user-account`、`x-user-name`、`x-user-l3dept`、`x-user-l4dept`、`x-user-l5dept`），限制文件权限，再启动：

```bash
chmod 600 /absolute/path/modeling-headers.json
OPSCOPE_MODELING_HEADERS_FILE=/absolute/path/modeling-headers.json ./start.sh --modeling-url=https://your-modeling-host
```

身份文件不提交 Git、不输出到日志或结果。非本机地址携带身份时必须使用 HTTPS；重定向拒绝转发身份。未提供有效身份时按原服务返回 401/403，不关闭鉴权。生产单点登录会话透传、多用户服务部署尚未接入。

## 复用关系

| 能力 | 唯一执行/数据来源 | OpScope 的职责 |
| --- | --- | --- |
| 算子默认输入、语义、输出推导 | modeling 基础 OP_CATALOG、可见 operator assets、现有 IR 构造/桥接 | 展示后端目录、传递用户输入 |
| 硬件 | modeling 可见 hardware assets 和统一 materialize/load_spec；infer 沿用既有转换器 | 选择资产 ID，传递版本摘要 |
| Roofline | modeling RooflineSimulator | 展示结果和字段来源 |
| TileSim | modeling TilesimSimulator + 安装于 modeling 的 msopmodeling | 展示原生时延及明确标注的 Roofline 补充分项 |
| 执行/存储/权限 | 既有 simulate_op、jobs、worker、TaskStore | 保留矩阵批次和最多 12 批内存展示记录，无新增数据库或任务队列 |

仅新增一个只读归一化目录 `GET /api/train/simulate/op/catalog`。提交复用 `POST /api/train/simulate/op` 的 `strict=true`，查询/超时取消复用 `/api/jobs/{internal_run_id}`。旧客户端默认 `strict=false`，原有策略不变。每个组合独立提交，当前每批顺序执行，最多两批并行；完成即更新卡片。没有原生进度时只显示阶段。

提交时重新检查可见资产、内容 hash，并冻结有效硬件与算子快照。重名硬件用配置 ID 区分；不合并不同规格。刷新页面重新拉取目录；旧结果保持旧配置。结果保存实际方法、硬件/算子摘要、引擎 revision/源码 hash、已加载校准索引摘要、上游运行 ID 及字段来源。保留默认校准策略，不宣称全部结果均未校准。

## 结果和限制

- TileSim 调用共享原生理论模式或已适配的工程入口（由算子合同决定），原生总时延保留；计算/访存/FLOPs/字节数是 Roofline 补充。补充失败时这些值为 null，原生时延仍可成功。没有事件就不生成流水。
- 严格模式拒绝借用型号、FP8→INT8、未经核验的形状/张量数量改变；FA 的已有 BNSD→input_dict 路径单独校验。旧兼容接口的数字不能当成严格支持证明。
- 基础输入校验和资产符号绑定通过后才执行。资产包含未声明符号、没有共享 IR 或没有 Roofline 公式时明确 unsupported。已开放后端声明的有界维度/列表参数和固定轴合同，未开放任意属性/布局覆盖，算子去重只认证 MatMul/BMM 输入变体，其余合同保持独立。
- 前三种 lookup 未连接实测库。目录存在不等于每种方法均支持。
- HTTP 提交不自动重试，避免断网时重复任务；120 秒等待超时或关闭服务会请求远程取消，但不把请求成功等同于 worker 已停止。页面切换配置/关闭视图时通过 OpScope 批次取消接口停止后续提交，并请求取消当前上游任务。已实测一次上游任务进入 cancelled；网络失败时明确显示取消未确认。
- OpScope 旧引擎和快照暂保留给显式独立模式、离线示例；共享路径不读取它们计算。发布前仍需覆盖审计后再删除，不能宣称仓库已完成物理瘦身。

## 实测与验收

在隔离 SQLite、独立测试端口下，H200_Server 基础 MatMul、FP16、A/B 均 128×128：直接共享入口与 HTTP 链路 Roofline **0.0512 μs**，TileSim **0.14128508391203703 μs**。这是真实模型调用，非真机精度验证。OpScope 使用全新、没有上述数值计算包的环境。

当前 100 个模板的配置已补齐：H200 默认 Roofline 93 成功/7 非计算范围；TileSim 默认精度 11 成功，显式 BF16→FP16 配置实验 24 成功。详细输入、原因和来源见[覆盖说明](shared-operator-coverage.md)。该审计不是全硬件、任意输入或真机精度认证；不支持不会用 OpScope 本地公式兜底。

更完整的迁移验收和剩余事项见[实施计划](modeling-backend-integration-plan.md)。
