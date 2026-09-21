# 架构

## 当前形态

独立静态前端原型，无服务器业务代码、数据库、API 客户端或框架依赖。Python 是构建期预处理工具，不是真实性能评估器。

```text
fixtures.py → execution_data.py
       ↓              ↓
             build.py
       + shell.html + styles.css + app.js
                    ↓
               index.html
                    ↓
    浏览器筛选 / 比较 / 详情 / JSON 导出
```

`build.py` 的 `build_payload()` 生成私有 `operator-ui-demo-v1` 结果包。`make_result()` 生成单组合结果、格式化值、图宽和详情 HTML。`execution_record()` 生成解析或详细执行示例。浏览器读取内嵌 `result-data` JSON，用内存 state 保存当前选择，不持久化用户操作。

## 文件职责

- fixtures.py：硬件/方法目录、示例时间与计数器、执行配置、Roofline 校准元数据。
- execution_data.py：解析记录以及详细模拟数据；不调用真实 simulator。
- build.py：单位换算、差值与图表预处理、详情 HTML、单文件生成。
- shell.html：结构和内嵌替换占位符；styles.css：PC 布局；app.js：展示与交互。
- test_build.py：数值、同源性、事件边界、缺失、校准合并等不变量。

## 数据边界

所有结果 synthetic=true。方法名不等于数据来源已接通。`details` 为可信内置 fixture 生成的展示 HTML，导出时移除；它不是正式 API 契约。当前 JS 使用 innerHTML 渲染可信内置数据，未来导入外部数据前必须增加校验与安全渲染，不能直接插入外部 HTML。

当前 24 条组合记录中 17 条可展示，7 条缺失。逻辑工作量、单 kernel 耗时与活动时间分开表达，计算/访存/等待允许重叠。精确字段语义见 [.agent/data-semantics.md](.agent/data-semantics.md)。

## 后续边界

不把现有内嵌 HTML 结构直接固化成公共 API。接入应先设计独立结构化结果契约及来源/版本/单位，再由后端适配器产生可展示数据；参见 [.agent/integration.md](.agent/integration.md)。
