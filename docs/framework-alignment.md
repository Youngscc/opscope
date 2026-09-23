# 前后端框架对齐设计与实施计划

2026-09-22。用户要求项目启动后通过端口访问，并为后续接入 modeling 保持框架一致。

## 依据与范围

只读核对本地 modeling 的 backend/web/app.py、requirements.txt、start.sh，以及配套 zrt-sim-ui 的 package.json、vite.config.ts、src/main.ts：后端 FastAPI/Uvicorn，前端 Vue 3 + TypeScript + Vite + Pinia + Vue Router。后端仓库已拆分前端，因此本项目采用 frontend/ 与 backend/web/，不改两个外部仓库。

新增同栈依赖用于应用生命周期、路由、响应式组件与构建。无需引入未使用的 Element Plus/ECharts；保留现有视觉与Python预处理图表。性能计算继续在隔离worker，不将模型依赖装入Web环境。根index.html仍为build.py生成的离线产物，在线入口改为Vue单文件组件，不用iframe包装旧页。

## 架构与接口

- frontend/src/pages/OpScopePage.vue为可移植页面，components拆分配置、矩阵、图表、详情、流水与导出；Pinia store持有当前配置/筛选/批次。Vue Router独立入口，卸载中断轮询，配置变更使旧响应失效。
- /api/opscope独立APIRouter提供bootstrap、capabilities、evaluations提交/查询/快照。供modeling include_router，运行时通过app.state.opscope_runtime注入；不直接依赖modeling任务库。原始性能契约保持不变。
- API基址可通过VITE_OPSCOPE_API_BASE配置；Vite开发代理同源，生产FastAPI同时托管dist，避免部署两个公开端口。API和前端资源严格分路由，不将未知API伪装成HTML。
- 默认127.0.0.1:8768。./start.sh安装本项目隔离环境的已声明依赖、构建Vue后启动Uvicorn；参数可改端口和引擎路径。不自动杀其他服务。支持--dev启动Vite热更新+独立后端端口，退出清理自身子进程。
- 静态/演示启动不要求外部modeling存在。通过本地忽略的.env配置实际解释器，示例.env.example只用可移植占位说明。
- 独立启动保留请求体64KiB限制与Host/Origin校验。后续合入时由modeling自己的认证中间件保护router，不能将当前无登录的本地入口直接公开。

## 计划

- [x] FastAPI模块、命名空间API、运行配置与应用生命周期
- [x] Vue/TS/Pinia/Router项目与可复用页面组件，保留现有交互和数据口径
- [x] 一键启动、开发代理、依赖锁与CI
- [x] API/组件状态单测、类型检查、构建、桌面端到端实际运行
- [x] README、架构与记忆更新，记录后续集成入口与未验证范围

## 验收

命令启动后在单一端口访问Vue页面，保留94算子、硬件/方法筛选、编辑清空旧结果、同批评估/图表、模态详情、双比较、流水选核/分页、完整JSON及HTML快照。验证FastAPI在宿主挂载router的路径，不连宿主业务数据库。测试实际Roofline/TileSim成功及未适配状态，保留synthetic/null语义。原离线构建与既有数据测试仍通过。

## 后续合入 modeling 的入口

后端提供可复用 `APIRouter`，不绑定独立服务的 Host/Origin 中间件。将路由及其依赖的数据/适配器模块移入宿主包后，在宿主 lifespan 中建立 `EvaluationRuntime`，赋给 `app.state.opscope_runtime`，再 `app.include_router(router)`；宿主退出时调用 runtime.close()。实际导入路径随合入后的包名调整；两个仓库都叫 `backend`，不能简单同时加入 Python 搜索路径。现已用独立 FastAPI 宿主验证注入和挂载，但没有修改 modeling 的应用、任务队列或数据库。

前端以 `frontend/src/pages/OpScopePage.vue` 为页面入口，由宿主复用现有 Pinia/Router 实例，将本页注册到宿主路由即可；不要重复执行本项目 main.ts。组件还依赖共享 styles.css、configuration.js 和 Vite shared-configuration 插件，迁移时一并带入或转为宿主模块。API前缀可以设为 `VITE_OPSCOPE_API_BASE=/zrt-sim-server/api/opscope`。`VITE_OPSCOPE_BASE` 仅用于宿主/反向代理提供的部署子目录，资源挂载和路由fallback由宿主配置；当前独立服务保持默认 `/`，页面路径为 `/opscope`。

Web依赖在本项目环境，Roofline与TileSim依赖仍在各自解释器。宿主认证、任务持久化、用户权限和测量数据需在真正合入时对接；本次只是技术栈与模块边界对齐。

后续独立化更新：Roofline 最小后端与 TileSim wheel 已迁入本仓库，默认统一安装到 OpScope `.venv`，不再需要外部解释器；子进程和 TileSim 临时目录隔离保持不变。宿主仍可通过参数覆盖解释器。详见[内置引擎迁移](bundled-engines.md)。

## 已验证（2026-09-22）

- `./start.sh` 在8768提供Vue页面、API、接口文档和HTML快照；外部引擎路径仅保存在本地忽略的.env。
- `./start.sh --dev --port=8769 --frontend-port=5174` 启动成功；无引擎时能力为ready=false、仍可取示例；Vite代理健康和能力接口均200。Ctrl+C后两个端口均释放。
- 47项Python测试、2项前端状态测试、TypeScript检查、生产构建、离线生成、JS语法和diff格式检查通过。依赖安装npm audit为0漏洞；这不是安全审计。Starlette/httpx组合有测试客户端弃用提示，测试仍通过。
- 浏览器默认4096² FP16运行7/40成功，910B1/910B4分别390.8914486042133与627.7357897236953μs，比较+60.6%；其余组合明确缺失原因。
- 流水默认24核/53,888事件，切AIC_23后2,205事件，翻页41–80正常。双条JSON保留各53,888完整事件，synthetic=false，去除展示几何及详情HTML。
- 修改形状时K不匹配被拒绝；128² BF16应用后0/40，重新运行7/40，TileSim分别2.996/4.442μs。算子目录94项，硬件搜索910B正确，桌面布局无页面横向溢出，控制台无错误。
- 实际HTML快照接口200/attachment，内嵌7条成功预测和synthetic=false。浏览器file://打开仍未验收；本轮未测试下载落盘。

未实际合入modeling、未运行真机精度认证、未推送或部署。CI托管运行待后续推送验证。根目录离线应用与Vue页面共用Python数据与配置契约，但保留各自渲染实现，后续改交互需关注两个入口的一致性。
