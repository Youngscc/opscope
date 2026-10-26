# OpScope 变更记录

## 2026-10-26 · 汇总前端与静态展示交付

整理并提交三页参考主题与左侧输入布局、双柱状对比、CAModel命名和方法顺序、MegaKernel算子族/维度/开销展示、详情合成数据与输出张量预览，以及设计师单文件HTML和相应设计文档。公开性能来源调查独立成文档提交；本地Trace和编辑器配置不纳入。

验证：127项Python测试、13项前端测试、Vue类型检查、在线构建、两类单文件构建、离线生成、app.js语法和差异格式检查通过。保留既有大包体积告警；本轮未重复浏览器视觉验收，沿用各功能记录中的已验收结果。此次交付不代表后端已接入真实测量或全目录输出推导。

## 2026-10-15 · 配置窗口输出张量预览

将折叠的“输出模板”替换为默认展开的名称、Shape、dtype表格，使用14px数值、等宽形状和精度标签。目录由Python提供维度引用，Vue仅读取对应输入维度与dtype；覆盖矩阵乘、权重投影、BMM及部分保形算子。示例MatMul支持转置引用，Mul/Add限同形输入，未建立规则或不完整/不匹配输入保持待确认状态，不参与性能计算。

验证：6项Python定向测试、13项前端测试、类型检查、离线构建和两类单文件构建通过；浏览器验证默认MatMul、切换模板、M维联动和问号输入状态。尚未覆盖全目录输出推导，未提交推送。

## 2026-10-15 · 补全静态详情与精简说明

静态展示的25组结果补充计算/访存耗时、流量、带宽、资源指标、硬件配置和执行参数，单项详情、双结果比较与JSON使用同一份合成补充数据。GPU展示共享内存及Tensor/SIMT/Load/Store字段；Roofline不生成执行流水。清理配置弹窗和对比摘要中的演示专用说明，保留全局示例标记。见[设计](static-detail-completion.md)。

验证：12项Python定向测试、13项前端测试、类型检查和三种前端构建通过；浏览器核对NPU硬件详情、GPU计算访存/资源指标和双结果比较。静态25组详情的数值事实无占位横线。原始评估结果与未匹配配置保持缺失语义，未伪造报告或Trace文件；既有构建体积告警仍存在，未提交推送。

## 2026-10-14 · MegaKernel文字可读性

第三页成员说明、徽标、资源表、执行链和趋势图标签从原8–11px提高到12–15px，主要数值增大并加深辅助文字颜色。增加排名行高和中等桌面当前成员卡宽度，允许长名称换行，保持现有数据与交互。同步两类HTML及在线构建。

验证：类型检查、三种构建通过，1280px浏览器核对共享权重长名称及字号，无页面横向溢出。纯样式调整未重复数据测试；未提交推送，既有体积告警仍存在。

## 2026-10-14 · 区分前三族实现示例

保留MatMul分块/流水成员；BatchMatMul改为批次并行、跨批次Tile调度、分组调度及批次流水；共享权重族改为L2复用、权重驻留、Batch/M合并与权重流水。成员名、特点、执行链、时延和流量预设同步区分，目录、基线、趋势和JSON保持一致，仍为合成演示不代表真实支持。

验证：23项Python定向检查、类型检查、三种构建通过，浏览器核对BMM与共享权重成员和数值。两类HTML已同步，未提交推送；既有大包告警仍存在。

## 2026-10-14 · 拆分并列算子族

MegaKernel直接展示MatMul、BatchMatMul、共享权重矩阵乘、Linear+GELU、Attention五族，删除计算类型与对比范围控件。新增扁平workspace_families目录，维度结果family_id/member_id对应独立族，保留硬件、维度与基线选择。未改性能数值；未做HTML体积压缩。

验证：22项Python、13项前端测试、类型检查及三种构建通过；浏览器逐族切换、批次可用性、融合成员、Attention尺寸与1280px无溢出通过。两类HTML同步，既有大包告警仍存在；未提交推送。

## 2026-10-14 · MatMul计算类型与独立尺寸

诊断MatMul写回通道改为Fixpipe/L0C→GM。MegaKernel增加普通、BMM、共享权重和Linear+GELU类型，独立选择M/N/K（1024、4096）及批量类型Batch（1、4），构建96组精确匹配的虚拟组合，含完整输入形状、内存、耗时和比较。趋势固定Batch/N/K改变M，导出记录类型与维度，Attention原配置保留。详见[设计](matmul-calculation-types.md)。

验证：21项Python、13项前端测试及三种构建通过，浏览器验证BMM/共享权重的空间差异、族切换、Fixpipe、1280px布局。修复族切换时异步类型监听覆盖Attention范围的问题。两类单文件已同步；设计HTML因完整预设增至约7.9MB，生产构建有体积告警。尺寸为有限选项，全部性能是合成样例，未接真实引擎或提交推送。

## 2026-10-14 · 实现与开销对比

MegaKernel实现结构卡改为“实现与开销对比”，保留执行链/启动次数，直接展示耗时、加速比、节省时间、峰值设备内存、中间结果峰值、临时工作区及累计读写量，移除重复UB行。Python新增显式memory样例及cost_view，保留synthetic与零值，未由流量或UB倒推空间。同步两类Vue单文件与在线构建，见[开销设计](implementation-cost-comparison.md)。

验证：20项Python、13项前端测试、类型及三种构建、差异检查通过。浏览器核对默认112→100MiB、自比1.00×/100→100MiB、融合176→100MiB和中间结果64→0MiB，1280px无横向溢出或控制台错误。补正前次“执行流水”文案的旧测试断言。空间为展示预设，未接真实API；HTTP检查，未提交推送。

## 2026-10-14 · 流水标题精简

性能分析的流水图标题统一改为“执行流水”，替换“计算在等什么？”及同类问句“计算集中在哪？”。同步示例资产、展示版与设计交接HTML。类型检查、三种构建及差异检查通过；纯文案调整，未重复浏览器测试或提交推送。

## 2026-10-14 · 方法展示名称与顺序

ESL显示名改为CAModel，方法顺序为真机数据、MSKPP、CAModel、TileSim、Roofline；矩阵、筛选、柱图、详情与导出共用目录同步。method4内部标识与lookup来源保持不变，不新增执行后端。重生成原生及两类Vue单文件，更新目录顺序断言。19项Python定向检查、类型检查、三种构建及差异检查通过；未重复浏览器交互测试或提交推送。

## 2026-10-14 · 输入栏通高留白

三页左侧输入栏拉满右侧结果区高度，控件保持顶部排列，底部连续白色留白。同步在线与两类Vue单文件。类型和三种构建通过，浏览器核对三页左右等高；仅样式变更，未重复数据交互测试或提交推送。

## 2026-10-14 · 三页左侧输入布局

三页统一为标题下的左侧输入、右侧结果卡片。评估集中算子/形状/平台/方法，分析集中算子/硬件/Size，MegaKernel集中族/范围/平台/Size/基线；沿用既有选择和导出。ResultMatrix以插槽将双柱图纳入右列，窄桌面矩阵内部滚动、图表按可用宽度堆叠。侧栏筛选展开在栏内，避免遮挡后续控件。同步在线与两类Vue单文件，设计见[输入侧栏](input-sidebar-layout.md)。

验证：13项前端、8项Python定向测试、类型检查、三种构建和差异检查通过。浏览器核对三页1280px布局无整页横向溢出、硬件与基线联动、配置弹窗、筛选、双比较及两条结果JSON的synthetic标记。HTTP预览实测，file协议未实测；未修改性能口径或提交推送。

## 2026-10-14 · 评估输入区域整理

性能评估标题卡仅保留标题；所有输入张量的形状和类型移到筛选卡算子按钮后，每个形状按钮打开既有输入配置弹窗。在线运行/保存入口随配置区移动，全局示例标记保留。同步三页展示和设计交接HTML。类型及构建检查通过。

## 2026-10-14 · 三页参考图风格还原

按用户三张参考图重排性能评估、性能分析与MegaKernel页面：深蓝顶栏、面包屑、居中导航和标题卡，独立筛选/矩阵、诊断资源双列、通栏流水与建议、合并算子族配置及紧凑排名图。新增统一主题，保留算子配置、筛选、详情、双比较与导出；额外周期/吞吐进入展开区。同步在线构建与两类Vue单文件，未修改性能公式或将截图占位硬件/数值写入资产。设计见[参考图还原](reference-style-redesign.md)。

验证：13项前端、8项Python定向检查、类型检查、三种构建、离线生成及差异检查通过。1920px逐页截图校准，1280px无横向溢出；实测筛选20/20及重置、单条详情、双比较、JSON两条结果与synthetic、硬件/基线和配置弹窗，无控制台错误。使用HTTP检查交接HTML，file协议未实测；未提交推送。

## 2026-10-14 · 前两页命名调整

共享导航第一项改为“性能评估”，第二项改为“性能分析”；第二页主标题、页脚及浏览器标题同步，首屏浏览器标题改为性能评估。路由和功能保持原样，三页demo与设计交接HTML重新生成。类型检查、三种构建、4项交接测试及差异检查通过；纯文字调整未重复浏览器实测，未提交推送。

## 2026-10-14 · 补全展示数据并精简小字

[分析展示](../opscope/offline/analysis_display.py)为NPU示例加入显式时钟与等效周期；[指标面板](../frontend/src/components/AnalysisPanel.vue)集中展示耗时、周期和资源指标。[实现结构](../frontend/src/components/optimization/ImplementationFlow.vue)补回读写量并展示Python预处理吞吐。精简矩阵、配置、详情和后两页的重复说明、英文装饰与演示页脚，保留全局示例和导出标记。同步两类Vue单文件及原生生成结果，更新[口径](../.agent/data-semantics.md)。

验证：34项Python、13项前端测试、类型检查、三种构建、离线生成及差异检查通过。浏览器核对三页、单/双详情、基线联动、融合配置、JSON字段与1280px布局，无控制台错误；file协议受工具限制，使用HTTP预览，筛选未重复实测。数据仍为合成示例，未接入真实API或提交推送。

## 2026-10-14 · 重新同步交接HTML双柱状图

根目录[交接HTML](../opscope-ui-design.html)仍包含旧“全局对比”，源组件已为双图。保留旧文件临时备份后按现有构建重新生成，恢复同平台不同方法、同方法不同平台及当前分析指标。类型检查、构建和4项交接测试通过，内容断言通过；本轮未重复浏览器检查或提交推送。

## 2026-10-13 · 参考含光分析字段调整三页展示

核对含光Python分析API与mock实际返回，新增[分析展示预处理](../opscope/offline/analysis_display.py)；矩阵单条/双条详情补充资源指标、流水组件周期和Trace状态。[共享指标面板](../frontend/src/components/AnalysisPanel.vue)用于诊断页与MegaKernel基线/当前实现对照，保留统一结论与synthetic，预设资产升级v7。三页展示、设计交接和原生矩阵导出同步；映射与边界见[设计](hanguang-analysis-display.md)。

验证：37项Python定向检查、13项前端测试、类型检查、在线/静态/设计交接构建、离线生成、JS语法和差异检查通过。浏览器核对单条指标/周期、双结果缺失对齐、诊断硬件切换、MegaKernel基线自比与周期展开、JSON原始比例及synthetic；桌面1280px无横向溢出，无控制台错误。原筛选与配置清空沿用本日浏览器检查及自动测试，本轮未重复实测；未调用真实引擎、接入HTTP后端或提交推送。含光目前为mock，诊断建议与实现结构仍为人工示例。

## 2026-10-13 · 性能矩阵增加两方向柱状图

[对比图](../frontend/src/components/ComparisonChart.vue)改为并列的同平台不同方法、同方法不同平台总耗时柱状图，各自选择平台/方法；[矩阵](../frontend/src/components/ResultMatrix.vue)行列联动并保持另一轴选择。复用 Python 的统一刻度和图宽，缺失保留原因，参考偏差仍可在矩阵切换。[原生模板](../shell.html)、[交互](../app.js)、[样式](../styles.css)及三种单文件导出同步更新，包括设计师交接HTML；记录[当前设计](result-matrix-design.md)、架构与数据口径。

验证：22项Python、13项前端及11项原生JS检查通过，在线/展示/交接构建、离线生成、JS语法与差异格式检查通过。浏览器检查独立选择、行列联动、筛选回退、缺失原因、矩阵偏差、单条/双条详情及JSON；核对25条合成结果和H100 Roofline157μs，1280px无溢出，原生及两种Vue导出显示正常，无控制台错误。仅HTTP预览实测，未执行实际评估、提交推送或部署宿主。

## 2026-10-13 · UI设计师完整HTML交接文件

新增[opscope-ui-design.html](../opscope-ui-design.html)，将当前三个界面、弹窗与交互整理为单文件，可读模板、CSS和示例JSON分别标出编辑区。新增[专用构建脚本](../frontend/build-design.mjs)及build:design命令，复用Vue组件与既有数据，不安装新依赖；模板转换为浏览器JavaScript并显式注册组件，保留事件/props/slot与synthetic。同步[交接与回迁流程](ui-design-handoff.md)、README、架构和记忆。

验证：8项Python定向检查、13项前端测试、Vue类型检查、在线生产/设计版构建及差异检查通过；18块模板和内联运行脚本语法有效，两份JSON与原资产逐值一致。浏览器核对三页、算子/硬件/尺寸配置、筛选、详情/双比较/JSON与基线自比；直接编辑临时HTML中的标题、CSS与JSON均生效，1280px无横向溢出，最终预览无控制台错误。file://直接打开未实测；未运行实际评估、接入优化后端或提交推送。

## 2026-10-13 · 静态演示恢复算子选择与输入配置

[三页静态文件](../opscope-demo.html)恢复[标题选择按钮](../frontend/src/pages/OpScopePage.vue)与[配置弹窗](../frontend/src/components/OperatorConfig.vue)，沿用搜索、分类、形状、精度、应用/取消；错误链接直接定位输入，保留hash路由。[Python资产](../opscope/offline/workspace_demo.py)保留完整目录及25条空结果模板，[状态管理](../frontend/src/stores/opscope.ts)按精确配置展示预设或空结果、恢复原工作负载，持续保留示例标记和API保护。同步[静态工作台约定](static-workspace-demo.md)、README、架构、数据口径及记忆。

验证：24项Python定向检查、13项前端测试、Vue类型检查、在线/单文件构建、内联JS语法及差异检查通过。浏览器核对Mul输入与JSON、取消/Escape、非法尺寸与错误定位、尺寸编辑后0/25/恢复25/25、筛选20/20、详情/双比较、三页导航及实际JSON下载；1280px无横向溢出，控制台无错误。在线配置保留原输入和评估文案。file://直接打开未实测；未运行实际评估或提交推送。

## 2026-10-09 · 三页单文件静态演示

新增[opscope-demo.html](../opscope-demo.html)，包含填满25条虚拟结果的矩阵、性能优化和MegaKernel。[Python预设选择](../opscope/offline/workspace_demo.py)保留原数值/缺失语义；[构建脚本](../frontend/build-demo.mjs)内嵌Vue、CSS与数据，使用hash路由。静态模式固定矩阵输入、隐藏服务入口，禁止API请求；仍支持筛选、单项详情、双比较、JSON及另两页配置联动。共享页内跳转组件避免覆盖hash路由，在线构建保持服务流程。同步[说明](static-workspace-demo.md)、README、架构、数据口径及记忆。

验证：28项Python检查、11项前端测试、类型检查、在线/单文件构建、脚本语法和差异检查通过。浏览器核对25/25及20/20筛选、详情/比较/流水、JSON下载及synthetic、三页导航/刷新、键盘与配置切换，桌面无横向溢出；修复首次库构建的process引用后无新增控制台错误。内置浏览器限制file协议，file://直接打开未实测，HTTP预览只服务该单文件。未运行评估或提交推送部署。

## 2026-10-09 · 移除优化方向跳转按钮

[性能优化页](../frontend/src/pages/OptimizationPage.vue)移除“查看优化方向”页内跳转链接，避免重复指向已经展示的卡片；清理[对应样式](../frontend/src/optimization.css)，保留卡片和建议展开交互。

验证：Vue类型检查/生产构建、离线生成与差异格式检查通过；浏览器确认桌面布局、首项默认展开、第二项展开/收起正常，跳转入口已移除且控制台无错误。原矩阵筛选、详情、双结果比较和JSON未重复检查；未提交推送或部署宿主。

## 2026-10-09 · MegaKernel 硬件可选与文案精简

[MegaKernel页](../frontend/src/pages/MegaKernelPage.vue)增加与性能优化页一致的硬件选择，配置控件共用样式；移除问句标题与重复说明，保留直接标题、单位和必要语义。[预设生成器](../opscope/offline/optimization_demo.py)增加910B4独立样例，展示资产升级v6，排名、趋势、比较和JSON均按硬件匹配；未知组合保持空结果。同步设计、架构、数据口径与记忆。

验证：11项预设、11项前端测试、Vue类型检查/生产构建、离线生成和差异格式检查通过。浏览器检查硬件/族/范围/规模切换、基线自比、键盘、趋势明细、390px布局及前页控件一致性；实际导出Attention/910B4/S1024核对52.6μs、2.10×、synthetic和硬件身份，控制台无错误。已恢复桌面视口；原矩阵筛选/详情/双结果比较未重复实测。仅更新5173预览，未实际评估、部署宿主或提交推送。

## 2026-10-09 · 优化工作台分类交付

将本轮改动按预设数据与结果匹配（`3b39505`）、前端界面与路由（`d15978f`）、设计文档与维护记录分类提交，推送目标为既有origin/main。[优化工作台设计](optimization-workspaces.md)、[架构](../ARCHITECTURE.md)、[数据口径](../.agent/data-semantics.md)与使用说明覆盖最终实现。此前宿主记录、Profiling调研、个人设置和临时trace不纳入此次交付，原文件保留。

验证：35项Python检查、9项前端测试、Vue类型检查/生产构建通过，生成的两份离线HTML与基线一致，暂存差异格式检查通过。沿用实现阶段的浏览器验证，本轮未重复运行实际评估或部署宿主。

## 2026-10-09 · 性能优化支持 Size 选择与输入配置

[诊断页](../frontend/src/pages/OptimizationPage.vue)增加 Size 快捷选择，强化算子/硬件/尺寸选择框和蓝色主按钮；[输入弹窗](../frontend/src/components/optimization/DiagnosisSizeConfig.vue)支持逐维编辑、校验与应用/取消。[预设生成器](../opscope/offline/optimization_demo.py)扩展为12组结果并升级v5，完整维度参与精确匹配；自定义尺寸无结果时显示空状态，导出包含尺寸和输入张量。同步[设计](optimization-workspaces.md)、架构、数据口径与项目记忆，保持synthetic标记和最终结论展示。

验证：10项预设、9项前端测试、Vue类型检查/生产构建、离线生成与差异格式检查通过。浏览器检查Size/硬件/算子联动、草稿取消、Escape焦点回归、非法维度提示、自定义尺寸空状态、桌面与390px弹窗布局；实际导出Attention/910B4/S512核对63.2μs、完整维度、Q/K/V与synthetic，控制台无错误。原矩阵筛选/详情/双结果比较未重复实测。预览已更新并恢复默认桌面视口，未执行实际评估、部署宿主或提交推送。

## 2026-10-09 · 性能优化支持算子与硬件选择

[诊断页](../frontend/src/pages/OptimizationPage.vue)将算子与硬件选择并列，切换时保留另一项并精确匹配完整结果。[预设生成器](../opscope/offline/optimization_demo.py)提供MatMul/Attention与910B1/910B4四组独立示例；[流水组件](../frontend/src/components/optimization/PipelineChart.vue)按对应结果绘制重点区间。未知组合返回null、显示空状态并禁用导出；JSON升级v4，包含两项选择身份与synthetic。同步设计、架构和数据口径，不修改真实硬件规格、模型映射或后端计算。

验证：9项预设不变量、7项前端测试、Vue类型检查/生产构建、离线生成通过。浏览器检查四组切换、键盘选择、1440px/390px无溢出、MegaKernel往返及导出状态重置；实际下载Attention/910B4 JSON并核对238.8μs、重点区间、身份与synthetic。刷新后控制台无错误。缺失组合null经过单元测试，空状态未通过浏览器构造缺失数据实测；原矩阵筛选/详情/双结果比较未重复实测。预览已更新，未提交推送或部署宿主。

## 2026-10-08 · MegaKernel 按人工定义的族组织成员

[MegaKernel页](../frontend/src/pages/MegaKernelPage.vue)增加算子族选择、族内成员数量和算子/融合算子/算子组合标签；以MatMul、Attention两个预设族展示人工归属，同族不同计算用对比范围隔离。族切换同步重置结果选择，输入形状和趋势轴随族更新。[预设生成器](../opscope/offline/optimization_demo.py)与JSON导出升级v3，显式携带族和成员身份，保留synthetic与最终结果展示约定。同步[设计](optimization-workspaces.md)、架构和数据口径；不接入族编辑持久化或后端计算。

验证：7项预设不变量、5项前端测试、Vue类型检查/生产构建、离线生成通过；浏览器检查桌面及390px无溢出、键盘族切换、范围/规模/基线联动、自比1.00×和不同规模排名，实际导出核对Attention族、成员上下文、synthetic和2.17×。刷新后控制台无错误。原矩阵筛选/详情/双结果比较未重复实测；5173预览已更新，未提交推送或部署宿主。

## 2026-10-08 · 移除流水重播

移除[关键流水](../frontend/src/components/optimization/PipelineChart.vue)的重播按钮、状态和扫描动画，保留静态等待区间与片段时间提示；清理对应图标和样式，同步[交互说明](optimization-workspaces.md)。

验证：Vue类型检查/生产构建、离线生成通过；浏览器确认1440px桌面布局、MatMul/Attention切换及区间标记正常，重播按钮已移除，控制台无错误。此次为定向展示调整，未重复运行原矩阵筛选、双结果比较和JSON检查；5173预览已更新，未部署宿主或提交推送。

## 2026-10-08 · 优化界面聚焦最终结论

按用户要求，[性能优化页](../frontend/src/pages/OptimizationPage.vue)删除多方法证据卡、数量和来源选择，资源压力与[关键流水](../frontend/src/components/optimization/PipelineChart.vue)不再标注方法；页面直接显示任务耗时、瓶颈位置和优化方向。MegaKernel维持实现级比较，确认无评估方法信息。同步清理[预设生成器](../opscope/offline/optimization_demo.py)中的方法记录与失效样式，展示/导出资产升级到v2，仅包含结果层字段，保留synthetic；原性能矩阵不受影响。

验证：5项预设测试、Vue类型检查/生产构建、离线生成及差异格式检查通过。浏览器检查两页无方法信息、诊断切换、键盘流水重播、融合排名及390px窄屏无溢出；控制台无错误。实际下载Attention诊断JSON，确认只有工作负载选择与最终结果，无source/evidence字段，示例标记保留。预览已更新，宿主未部署。当前产品约定见[优化工作台](optimization-workspaces.md)。

## 2026-10-08 · 性能优化与 MegaKernel 界面预览

在 Vue 前端加入两个与性能矩阵并列的页面：[性能优化](../frontend/src/pages/OptimizationPage.vue)展示统一瓶颈、资源压力、多方法证据、局部流水和优化方向；[MegaKernel](../frontend/src/pages/MegaKernelPage.vue)展示同一功能族内的实现排名、可选基线、规模趋势与融合边界。使用简洁的图表和展开交互，预设数据和导出始终标记 synthetic；不实现后端性能计算。共享导航、独立样式与图表组件位于 frontend/src；[预设生成器](../opscope/offline/optimization_demo.py)由 build.py 调用，图宽和比值在Python生成。静态路由增加两个页面的刷新入口，原矩阵配置在导航返回后保留。

验证：5项新预设、14项构建/矩阵、1项HTTP静态路由及5项前端测试通过；Vue类型检查、生产构建、离线生成和差异格式检查通过。浏览器检查桌面与390px窄屏、筛选、缺失流水、重播、键盘、基线自比、规模排名变化和融合边界；两页JSON下载检查synthetic与上下文正确，控制台无错误。原矩阵可读取宿主目录，未运行评估。当前只更新本仓Vue源码；原单文件demo仍为矩阵，宿主zrt-sim未同步。减少动态效果仅静态样式核对。设计边界见[优化工作台](optimization-workspaces.md)。

## 在线 OpScope 本机免登录（2026-09-29）

同级 zrt-sim 已恢复在线构建，并在本机配置持久开启 `OPSCOPE_LOCAL_NO_LOGIN=true`。仅本地环境、回环 OpScope API 使用固定普通账户 `opscope-local`；所有本机浏览器共享该账户，提交体或旧身份头不能改变归属，其他 API 和生产认证不变。继续复用原 TaskStore、配额等待及 worker，无需交互登录，重启或前端构建后配置仍生效。静态 demo.html 保留，先前静态页面挂载已被本轮替换。

验证：新增12项身份测试、17项内嵌测试及30项配置测试通过；认证/免登录两套真实 HTTP+worker 的 MatMul/RmsNorm 双方法、报告和快照通过。另2项既有配额测试因认证环境失败，用 HEAD 身份实现同样复现；完整套件收集受两项既有 MCP 依赖导入错误阻塞。已通过统一脚本重启 Web/worker，保留数据库；无身份8000页面和 bootstrap 均200，外部 Origin 为401，浏览器在线目录及运行按钮正常。内存分组历史仍不持久化。未提交推送。见[启动说明](../../zrt-sim/docs/opscope.md)。


## /opscope 直接显示预设结果（2026-09-29）

将已生成的 demo.html 安装为同级 zrt-sim 的 `backend/web/static/opscope/index.html`，沿用现有8000代理与公共页面路由，直接显示静态预设结果。宿主 docs/opscope.md 说明当前展示模式，以及重新构建在线前端会覆盖展示产物。同步[项目记忆](../.agent/MEMORY.md)。

验证：无身份请求127.0.0.1/localhost、带/不带末尾斜杠及8001直连均200，内容与demo.html完全一致；浏览器已显示“示例数据”、25条预设结果及全局比较图。API无身份仍401。未重启服务或触发评估，未修改后端鉴权与worker，未重新运行应用测试；未提交推送。

## 静态展示页（2026-09-29）

新增单文件 [demo.html](../demo.html)，内置现有 MatMul 预设结果，无需安装或启动服务即可演示。复用[离线生成器](../opscope/offline/build.py)、共享样式与交互，固定输入并隐藏执行入口，[初始化](../evaluation-ui.js)跳过服务探测；支持筛选、详情、双结果比较和 JSON，保留合成标记与缺项原因。[使用说明](../README.md)和[架构](../ARCHITECTURE.md)同步更新。

验证：重新生成两份 HTML，14项数据/矩阵测试、4项既有评估UI测试、JS语法与静态模式无网络/不可提交定向检查通过。按用户要求未启动服务或运行评估；浏览器布局、筛选、详情、双结果和JSON交互未实测。交付仅包含本次静态展示相关改动，已有未提交调研及其他工作保留本地。

## 公开算子 Profiling 数据来源调研（2026-09-28）

新增[来源调查报告](public-operator-profiling-sources.md)与[审计摘要](research/public-profiling-audit-2026-09-28.json)，区分已发布测量、算子定义、采集工具和真实 trace。逐文件解析 FlashInfer 190 个定义及 196 个结果文件（7,735 条记录，5,474 条 PASS），读取 SOL 全部 235 个问题/3,957 个 workload，核对 KernelBench 四份共 1,000 条计时记录及 Meta 两份 trace 的字段。明确硬件、融合/计时边界、派生吞吐和计数器的区别，以及尚未确认的 Ascend 型号覆盖。

验证：统计总数与分类求和断言、JSON 解析和文档相对链接检查通过。FlagGems 结果页直接抓取 403，改用公开索引与官方源码核对结构，未宣称取得完整底层数据。未运行外部 kernel、未复测发布方性能、未接入应用或修改运行代码；因此未重跑应用测试。原有工作树修改保留，未提交/推送。

## 配额等待与原 worker 复用（2026-09-28）

同级 zrt-sim OpScope 运行时将 429/ACTIVE_RUN_QUOTA_EXCEEDED 保留为 queued/null，在后续轮询刷新结果后按顺序补交至原 TaskStore/worker。首个额度拒绝停止本轮补交；非配额错误仍失败。取消会终止未提交组合，避免取消后再次提交。未增加计算引擎或执行队列，未放宽角色配额。

验证：17项内嵌后端测试通过；隔离数据库下真实HTTP+原worker的MatMul/RmsNorm双方法、报告、快照和用户隔离通过。用户已同意清空内存展示批次并重启8001，现已仅重启Web，原worker及数据库保留。旧批次失败项不自动重试，请重新发起评估。等待补交仍依赖页面轮询，关闭页面暂停补交，Web重启丢失未提交组合。未commit/push。实现说明见 [排队计划](../../zrt-sim/docs/superpowers/plans/2026-09-28-opscope-quota-queue.md)。


## 本地测试身份入口修复（2026-09-28）

同级 zrt-sim-ui 的本地登录插件改用 Vite loadEnv 读取当前模式的 `.env.local`，同时保留进程环境优先级；仅回环连接可访问测试页面。已在本机忽略文件启用入口，密钥未纳管。入口 `?next=/opscope` 支持选择测试身份后直接进入 OpScope，其他目标回原主页。后端鉴权保持开启，未修改角色或添加主页按钮。

验证：4项定向测试通过（含真实Vite请求、生产构建不带测试入口、配置加载和非本机拒绝）。浏览器选普通用户A后OpScope加载成功，原主页显示本地用户A，再访问无参数 `/opscope` 仍成功。未运行评估任务，未commit/push。操作说明见 [UI README](../../zrt-sim-ui/README.md)。


此处按**完成的修改任务**记录结果与验证，不按文件保存次数记流水。历史原型迭代见 [HISTORY.md](HISTORY.md)；长期项目事实见 [项目记忆](../.agent/MEMORY.md)。记录不等于已提交或已发布。

## 2026-09-28

### 记录 OpScope 统一使用前端8000入口

修正同级zrt-sim-ui开发代理：页面/静态资源 `/opscope` 和 `/api/opscope` 转发至8001，明确监听127.0.0.1；主页按钮保持不变。同步两仓启动说明与[项目记忆](../.agent/MEMORY.md)。真实HTTP验证页面、JS/CSS、原主页及健康接口200，未登录API401，原代理检查2项通过。本仓无运行代码修改，未提交推送；生产反向代理仍需部署对应规则。

### 记录 OpScope 完整内嵌 zrt-sim

同级 zrt-sim/main 工作树已迁入页面、矩阵、详情、双结果对比、HTML/JSON/离线导出，同端口 `/opscope`，仍不添加原主页入口。任务、目录、身份和建模均内部复用宿主；无需独立 OpScope 服务。此仓库只更新[项目记忆](../.agent/MEMORY.md)，实现与启动见 [zrt-sim 文档](../../zrt-sim/docs/opscope.md)。

41项相关后端、9项前端、独立构建、真实HTTP四组合和宿主E2E4/4通过；宿主回归的2项失败、全量触及的20项失败均在未修改main复现，不宣称全量通过。浏览器矩阵/浮窗/JSON通过；下载HTTP200但落盘事件未确认；离线file://视觉检查受浏览器策略阻止。批次分组暂为有界单进程内存，底层任务持久化不变。本轮未commit/push，原EAGLE目录、独立UI和旧服务未改。


### 记录 fork main 拉取状态

本地独立 zrt-sim 仓库从 `11cd61ca` 快进到 `fc84cdef`，GitHub fork 已包含上游最新 main，GitCode 镜像同 SHA；工作树干净，原 modeling 的 EAGLE 分支未动。[项目记忆](../.agent/MEMORY.md)同步记录新的本地基线。本轮无新代码提交、无测试重跑、未重启服务。

### 记录 fork 自动门禁停用

按用户要求，仅在 Youngscc/zrt-sim 设置中停用 CI、覆盖率、门禁管理/监控与 GitCode PR Gate，共五项；取消四个未完成门禁任务。仓库测试与镜像同步保留，未修改代码或工作流文件，main 未设分支保护。通过 GitHub API 回读状态；这是远端设置操作，不构成测试通过或代码提交。持续约束记录于[项目记忆](../.agent/MEMORY.md)。

### 纠正共享后端的 GitHub main 基线

更新[项目记忆](../.agent/MEMORY.md)，明确旧集成分支带入独立 EAGLE 开发历史的原因和纠正结果。原 modeling 开发分支已恢复；共享后端改为从 fork main 独立移植，实现 `ff6c7dcb` 与交付记录 `11cd61ca` 已推送到 Youngscc/zrt-sim main，默认整模型 TileSim 选择保持原行为。OpScope 本轮无运行代码变更，97项Python与5项前端测试通过；后端211项定向、69项原接口、E2E4/4和HTTP四组合通过。全套及扩大回归仍有与原main同环境一致的失败，不宣称全量通过；旧运行服务未重启。

### 启动本机 PostgreSQL 并解除数据库连接阻塞

Docker 因旧用户磁盘路径与 macOS 配置权限无法正常启动，改用 Homebrew PostgreSQL 16.15。服务已启动并注册登录启动，仅监听 localhost:5432；沿用 modeling 现有配置创建 zrt 账号与数据库，实际 SQL 连接验证通过。未修改项目连接配置、未重启 Web/worker、未主动重置 Docker 数据。具体机器环境事实记入[项目记忆](../.agent/MEMORY.md)，不记录凭据。此前阻塞的289项推理测试复跑282通过、7项断言失败，数据库初始化阻塞已解除；失败归因尚未定位，本轮未修改建模代码。

### 同步 GitHub main 到集成开发分支

- 合并 OpScope main `f04aab8` 的 GitCode 同步工作流及记录；同时将 modeling fork main `635e5558` 的主线更新合入其集成分支。文档冲突保留双方独立记录，接入实现保留，个人文件和原有未提交修改不纳入。
- 验证：OpScope 97 项 Python、5 项前端、5 项同步脚本测试通过，离线重建一致；modeling 严格26项、E2E4/4、同步脚本5项通过。推理扩大回归受未启动的本机 PostgreSQL 阻断（289项 fixture 错误），全量仍有2项 MCP 导入收集错误；未把环境阻塞视为测试通过。
- 更新仅发布至 `codex/opscope-modeling-integration`；远端 main 和 GitCode 镜像目标不变，运行服务未重启。

### 分类提交共享后端与算子覆盖改动

按环境、功能、设计文档和覆盖审计组织 OpScope 提交，并将 modeling 的共享后端实现与说明分别提交。明确纳入原忽略规则漏掉的 TileSim 适配模块；用户 trace、个人设置及 modeling 原有无关修改不纳入。GitHub 集成分支为交付目标，未合入 main，不触发仅跟随 main 的 GitCode 镜像。验证沿用本轮已完成测试，并检查暂存差异及生成文件一致性；实际推送结果以 Git 远端核对为准。

### 补齐共享目录配置及算子方法适配

- modeling 新增严格符号绑定、资产工作量与共享 SFU 策略复用，补齐合法 dtype、输出、固定轴以及 TileSim 原生理论/工程适配；宿主前端未改。OpScope 的 [provider](../opscope/evaluation/modeling_provider.py)、配置表单和[来源详情](../opscope/evaluation/modeling_details.py)只传递有界参数并展示实际模式，不复制计算公式。
- [覆盖说明](shared-operator-coverage.md)记录 100 模板的 300 项 H200 审计及资产/硬件快照：Roofline 默认 93/100 成功；TileSim 默认 11/100，显式 BF16→FP16 实验 24/100。两项审计超时延长后成功，没有计为不支持；精度不会自动转换。余项按原生模型、张量合同、硬件/精度或执行错误列出原因和路径。
- 验证：97项 Python、5项前端、类型/生产构建、离线生成、JS语法通过；modeling严格26通过，扩大回归187通过/3原始基线同样失败，全量5个原有收集错误，E2E4/4。真实 HTTP RmsNorm 双方法、桌面配置/矩阵/详情/双结果/JSON预览，以及单项/对比报告接口通过。
- 边界：不代表全硬件或任意输入已支持；未补造 TileSim 缺失算法/输入，不提供虚假流水或方法回退。原8768未改，隔离8803展示更新结果；未提交/推送。

## 2026-09-24

### GitHub 主仓到 GitCode 指定分支同步

- 新增 [同步工作流](../.github/workflows/sync-to-gitcode.yml)、分支推送脚本、隔离 Git 测试与[配置说明](github-gitcode-sync.md)。OpScope 的 main 对应 YYoung_G/opscope main；同批为 modeling、UI 的 fork 准备了 main 到原 GitCode 接入分支的映射。
- 同步保留提交身份，只允许快进；不复制其他分支/标签，不覆盖独立提交。令牌仅从 Actions Secret 读取，自动触发需显式启用变量。
- 验证：5 项本地真实 Git 测试通过，覆盖创建、快进、重复运行、分叉拒绝、演练无写入及其他分支/标签保留。三个仓库的 Actions 演练和首次正式同步成功，日志核对目标 SHA 一致，自动同步变量已启用；按用户选择保留全部已有工作流。本地未提交功能改动未发布。

### 实现共享建模后端接入与轻量环境

- 新增 [HTTP provider](../opscope/evaluation/modeling_provider.py) 与来源详情适配；复用 modeling 资产目录、硬件解析、Roofline/TileSim、既有单算子任务和 worker，保留逐格结果、比较和报告。在线提交按资产 ID/hash 固定配置，严格方法不回退、不使用本地规格补缺；同名硬件按配置 ID 区分。宿主前端无本轮源码变更。
- 增加 [轻量 requirements](../backend/requirements-modeling.txt)、`setup.sh --modeling`、启动服务 URL/身份文件配置，本地引擎变为可选 extra。OpScope 取消接口将切换配置传到上游并停止后续组合。当前能力、安装与限制见[共享模式](modeling-runtime.md)，覆盖初查见[CSV](audits/2026-09-24-shared-roofline-h200.csv)。
- 验证：OpScope 90 项 Python、4 项前端、类型/生产构建、离线生成、JS/bash 语法及差异检查通过。全新无 NumPy/SciPy/Torch/TileSim 的环境真实调用 H200_Server 128² FP16 MatMul，Roofline 0.0512μs、TileSim 0.14128508391203703μs；页面配置/筛选/逐卡/详情/双结果、JSON及两个报告接口核验。真实取消上游任务终态为 cancelled。modeling 严格与包兼容14项通过，E2E4/4；联合硬件专项34/36，全量5个收集错误阻断，未宣称全部通过。
- 边界：100模板×H200 Roofline初查55成功45不支持，不是全硬件/全方法覆盖。工程流水、完整语义去重、生产登录透传和旧副本物理清理仍未完成；独立模式显式保留。未提交/推送，未重启原8768；临时8802/8803使用隔离任务库供本轮验证。

### 收紧接入计划以优先复用并保持轻量

- 更新[设计](modeling-backend-integration-design.md)、[计划](modeling-backend-integration-plan.md)、接入边界及记忆：明确直接复用、兼容扩展、必要新增的顺序；候选新接口不再作为必建项，复用现有资产、任务、权限、存储和展示实现，增加重复模块/依赖清理验收。
- 验证：核对 modeling 现有 assets 和基础单算子路由，文档链接及差异格式检查通过。仅修改计划文档，未改变接口或运行行为，未运行功能测试，未提交或推送。

### 将硬件与算子数据复用纳入接入计划

- 补充[接入设计](modeling-backend-integration-design.md)与[实施计划](modeling-backend-integration-plan.md)：明确复用 modeling 硬件加载器、算子/硬件资产及版本权限，列出数据源、只读目录接口、同名配置边界、本地快照迁移和数据更新验收；同步接入边界与项目记忆。
- 验证：静态核对现有硬件加载、算子模板、资产查询/版本及 TileSim 配置映射路径；文档相对链接与差异格式检查通过。仅扩展计划，未修改数据或执行代码，未运行功能测试，未提交或推送。

### 制定 OpScope 复用 Modeling 后端的接入计划

- 新增[接入设计](modeling-backend-integration-design.md)与[实施计划](modeling-backend-integration-plan.md)，明确宿主前端不动、两种模型在 modeling 统一执行、OpScope 通过远程 provider 接入；列出方法回退、字段来源、近似映射、依赖及缓存问题，给出分阶段文件清单和验收标准。同步边界文档、导航与项目记忆。
- 验证：对照本地源码与依赖元数据核查调用链，检查本次文档相对链接及差异格式。本轮仅形成计划，未安装依赖、修改运行代码、执行性能预测或测试套件；新接入能力尚未实现，未提交或推送。既有未提交功能修改保持原样。

### 准备 Modeling 接入试验分支与约束

- modeling 与 zrt-sim-ui 从各自当前 HEAD 创建并切换至 `codex/opscope-modeling-integration`；在[接入边界](modeling-integration-scope.md)记录基线、保持宿主前端不动、直接复用 Roofline/TileSim 后端的原则，更新文档导航与项目记忆。
- 验证：两仓库分支、HEAD、工作区状态及已跟踪差异摘要核对，既有改动保留。本次未修改运行代码，未执行运行测试；尚未实现接入，未提交或推送，OpScope 分支保持不变。

## 2026-09-23

### 统一方法顺序并预设 lookup

- [方法目录](../opscope/offline/fixtures.py) 按真机数据、MSKPP、ESL、Roofline、TileSim排序；前三项配置为lookup，保留旧内部ID。示例、在线结果、筛选、详情/报告和JSON同步命名与预设元数据；运行时未接查表数据明确返回缺源原因，不回退计算。见[方案](method-lookup-presets.md)。
- 验证：81项Python测试、3项前端测试、类型检查/构建、离线生成、JS语法及差异检查通过。HTTP实跑H200小型MatMul，前三项unsupported且耗时为空，Roofline/TileSim分别0.0512/0.14128508391203703 μs成功；桌面顺序、lookup标签、MSKPP/ESL对比、筛选及JSON检查通过。尚未实现lookup数据导入与匹配，不将示例当真实命中；未提交或推送。

### 优化字体层级与结果区域比例

- 在共享 [styles.css](../styles.css) 中强化耗时、硬件/方法名和分节标题的字号/字重层级，提升标签可读性；收紧详情顶部，将更多空间留给内容，调整单项摘要卡比例及双结果表格列宽。重新生成 [index.html](../index.html)，在线/离线共用样式；不修改计算或交互逻辑。
- 验证：Vue类型检查/生产构建、离线构建、14项构建与矩阵定向测试、差异格式检查通过；桌面检查矩阵、单项/双项详情、筛选、差异、JSON、长算子名称及离线双结果展示，无横向溢出，在线控制台无错误。8768已加载新静态产物，无需重启；未执行移动端检查，未提交或推送。

### 改为直接选择两张矩阵卡片比较

- 在线/离线常驻“加入对比”，标记 A/B、最多两项，取消/筛选/换选保持同步；页面移除评估时间选择区。浮窗新增同尺度总耗时图及按所选结果下载 HTML 报告，保留原始指标、不可比说明、零值与 synthetic 语义。主要修改 [ResultMatrix.vue](../frontend/src/components/ResultMatrix.vue)、[ResultDetails.vue](../frontend/src/components/ResultDetails.vue)、[矩阵预处理](../opscope/offline/matrix_data.py)、[报告路由](../backend/web/routes/opscope.py)与离线模板；见[设计](matrix-comparison.md)。
- 验证：80 项 Python 与 3 项前端测试、类型检查/构建、离线生成、JS 语法和差异检查通过；桌面选择/取消/第三项限制/筛选、单项/双项详情、差异筛选、JSON、离线页面和报告视觉验收通过。实跑 H100/H200 小型 MatMul Roofline 并下载所选结果报告成功。
- 经用户明确授权重启 8768 服务；历史接口保留但不再显示时间选择 UI。报告仍依赖服务内存快照，示例报告独立标明 synthetic。没有提交或推送。

### 修复 FP8/FP4 Roofline 峰值字段映射

- [`bundled_roofline.py`](../opscope/evaluation/bundled_roofline.py) 从已有 `_tops` 字段读取 FP8/FP4 峰值，其他浮点精度继续读取 `_tflops`；未修改硬件数值。增加目录公式回归测试，并更新[缺口地图](evaluation-gap-map.md)、[数据口径](../.agent/data-semantics.md)和[项目记忆](../.agent/MEMORY.md)。
- 验证：独立 worker 实跑 `infer:QuantBatchMatmulV3` 默认输入的 17 个非 TileSim 硬件入口，16 成功、`Adevice03_POD` 1 项因 `fp8_tops=0` 不支持、0 运行失败；Python 全量 79 项测试通过，差异格式检查通过。未重跑 9,500 格全量审计；910B1/B4 的整卡 Roofline 规格仍缺。

### 建立按任务记录的变更流程

- 增加 [变更记录 Skill](../agent_skills/opscope-change-record/SKILL.md)，并在 [AGENTS.md](../AGENTS.md) 与[项目级 Skill 分工](agent-workflows.md)中规定：每个完成的仓库文件修改任务留一条实际变更、验证和限制记录。既有设计文档与项目记忆继续承担各自职责。
- 验证：Skill 结构校验、文档链接和差异格式检查。此轮只改工作流文档，未更改评估计算或页面行为；未回填此前任务的流水，也未提交或推送。
