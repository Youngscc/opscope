# 架构

## 统一展示目录

`catalog_data.operator_groups()`按名称忽略大小写/下划线归并100个内部模板为94个可见算子。MatMul、Linear、RMSNorm、SwiGLU、Embedding只有一个列表入口，不同张量契约以中性的“输入形式”保留。内部id/domain/source不变，校验与硬件档案选择继续按原契约；界面移除来源筛选、徽标及源码详情。

`Configuration.public_export()`为JSON预览和下载生成中性operator_id/template_id及hardware标识，去掉仓库路径、来源域、目录revision和档案溯源；不修改内部数据，不丢失synthetic、性能数值、执行方法和校准来源。当前结构仍是展示私有契约，未增加导入能力。

## 当前形态

独立静态前端原型，无服务器业务代码、数据库、API 客户端或框架依赖。Python 是构建期预处理工具，不是真实性能评估器。

```text
fixtures.py → execution_data.py
       ↓              ↓
       task_details.py → build.py → matrix_data.py
       + shell.html + styles.css + app.js
                    ↓
               index.html
                    ↓
    浏览器筛选 / 比较 / 详情 / JSON 导出
```

`build.py` 的 `build_payload()` 生成私有 `operator-ui-demo-v1` 结果包。`make_result()` 生成单组合结果、格式化值、图宽和详情 HTML。`execution_record()` 生成解析或详细执行示例。浏览器读取内嵌 `result-data` JSON，用内存 state 保存当前选择，不持久化用户操作。

## 文件职责

- task_details.py：合成任务上下文、张量占用与硬件快照缺失状态；Python 预生成新增详情页签。
- matrix_data.py：统一图表尺度、点位置/条宽、详情标量/图形分组与定向成对比较说明，纯Python预处理。
- fixtures.py：硬件/方法目录、示例时间与计数器、执行配置、Roofline 校准元数据。
- execution_data.py：解析记录以及详细模拟数据；不调用真实 simulator。
- virtual_data.py：方法3/方法4的虚拟总耗时、派生有效算力、空缺执行分项及详情；不指定模拟器。
- build.py：单位换算、差值与图表预处理、详情 HTML、单文件生成。
- shell.html：结构和内嵌替换占位符；styles.css：PC 布局；app.js：展示与交互。
- test_build.py：数值、同源性、事件边界、缺失、校准合并等不变量。

## 数据边界

所有结果 synthetic=true。方法名不等于数据来源已接通。`details` 为可信内置 fixture 生成的展示 HTML，导出时移除；它不是正式 API 契约。当前 JS 使用 innerHTML 渲染可信内置数据，未来导入外部数据前必须增加校验与安全渲染，不能直接插入外部 HTML。

当前预生成85条组合记录（6个示例硬件+11个目录型号，各5方法），25条有合成结果；默认显示示例的30条。方法3与方法4各有5条虚拟总耗时，目录型号仍缺失。逻辑工作量、单kernel耗时与活动时间分开表达，计算/访存/等待允许重叠。精确字段语义见 [.agent/data-semantics.md](.agent/data-semantics.md)。

## 后续边界

开发验证由 [.github/workflows/ci.yml](.github/workflows/ci.yml) 执行：单元测试、JS 语法检查、重新构建并检查 index.html 无差异。它不参与页面运行或部署，具体约定见 [CI 说明](docs/ci.md)。

不把现有内嵌 HTML 结构直接固化成公共 API。接入应先设计独立结构化结果契约及来源/版本/单位，再由后端适配器产生可展示数据；参见 [.agent/integration.md](.agent/integration.md)。

## 单算子任务详情

结果附带 task、workload、hardware_snapshot；全部由构建期生成，不代表真实任务服务。原八类详情内容保留在 details，matrix_data 将其分成五个UI页签，并预提取用于双结果逐行对齐的标量。单条和双条都进入原生dialog，共用滚动区、焦点与关闭行为。

主界面固定硬件行×方法列；JS只负责筛选、主指标选择、图表行/列聚焦、详情和导出。图表采用HTML/CSS标记，其刻度和百分比坐标由Python根据全部结果统一生成，筛选不会悄悄重定标。matrix.pairs 保存有方向的 A/B 比较说明；跨硬件又跨方法、输出/计时边界不一致或真实来源未校验时不生成比值。当前只有合成fixture契约，不是通用真实数据校验服务。

全局 JSON 导出筛选范围，详情 JSON 导出当前一或两条结果；两者移除 details/sections/matrix 等新旧展示字段，保留原始上下文、执行记录和 synthetic。字段背景见 [详情设计](docs/task-detail.md)，当前UI见 [矩阵设计](docs/result-matrix-design.md)。

## 算子目录与配置

`tools/snapshot_catalog.py`按需读取modeling受跟踪源码中的训练OP_CATALOG、推理资产及公共硬件顶层字段，写入`data/modeling-catalog.json`。日常构建由`catalog_data.py`读取本地快照；没有原仓库或YAML依赖。硬件按系统名列出，但`profiles`分别保留train/infer路径与内容摘要，不合并两域规格。旧示例硬件拥有独立id和分组。

`configuration.js`仅负责表单语法、部分维度约束及配置匹配，`catalog-ui.js`负责搜索/编辑/应用。三个JS文件由build.py内嵌；Node只用于验证。Python安全求值已知模板维度，未知项为null。用户编辑配置不做FLOPs或输出形状推导；输出、工作量、耗时保持空缺。已有真实接口不支持的额外属性不擅自添加。

应用配置时，同时更换标题、结果上下文与导出内容，清空比较和图表聚焦。只有完整匹配合成默认配置才恢复25条fixture结果；其余组合用Python预生成的空模板并绑定当前输入。配置在内存中保存，关闭/取消浮窗不提交草稿。详情和全局JSON增加configuration与catalog_revision，仍保留synthetic=true。实现计划与目录范围见 [算子目录设计](docs/operator-catalog-plan.md)。
