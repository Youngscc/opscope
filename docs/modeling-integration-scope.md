# Modeling 接入试验边界

日期：2026-09-24。状态：已准备分支并完成源码审计与接入计划，尚未实现接入。

## 分支基线

| 仓库 | 新分支 | 创建时所在分支 | 基线提交 |
| --- | --- | --- | --- |
| modeling | `codex/opscope-modeling-integration` | `codex/development-20260910` | `f571e9f12af178cd788a9f7344451def6e35b37f` |
| zrt-sim-ui（modeling 前端） | `codex/opscope-modeling-integration` | `codex/development-20260910` | `2bb371a6e3d17795903890d3076e83f10ee90dc9` |

两边从各自当前 HEAD 建分支，保留已有未提交修改，不提交或推送。OpScope 本次保持现有分支，既有独立运行能力不变。

## 用户确定的接入原则

1. 第一阶段不改 modeling 现有前端的页面、布局、路由和交互。UI 分支先作为后续工作的准备。
2. 优先复用 modeling 后端现有 Roofline、TileSim 建模代码；OpScope 不再为这条接入链路自行实现或复制计算公式、调度模型。
3. OpScope 负责算子输入与硬件/方法配置的适配，以及结果展示、比较和报告；数值来自 modeling 后端实际执行。
4. modeling 未支持的算子、缺失参数或执行失败应明确返回原因，不静默回退至 OpScope 自有计算实现，不把示例数据当作执行结果。
5. 保留方法来源、版本、单位、缺失值与计时边界；同名算子需核对张量与数学语义，不能仅按名称替换调用。
6. 硬件规格和算子数据也统一复用 modeling 的资产、加载器及版本机制；OpScope 不再维护第二套在线参数数据。具体来源、资产权限、版本锁定及本地快照退役规则见[接入设计](modeling-backend-integration-design.md)。
7. 能复用就复用，保持 OpScope 轻量。优先使用现有接口、任务/存储/权限机制，缺口优先兼容扩展；不默认新建目录、队列或模型框架。此前提出的新模块与路由均为候选，最终以最小必要改动为准。

## 设计与下一阶段

已形成[接入设计](modeling-backend-integration-design.md)与[实施计划](modeling-backend-integration-plan.md)。推荐先新增 modeling 严格单算子服务/API，复用其 RooflineSimulator、TilesimSimulator 及现有任务系统，由 OpScope 远程 provider 调用；保持宿主前端不动，不走 TileSim 失败后回退 Roofline 的策略。

下一步按计划对齐远端与本地基线、确认 TileSim 依赖，先打通一个真实算子，再接界面并扩展目录。用相同有效配置对照 modeling 原生调用与 OpScope 接入调用，检查耗时、字段来源、缺失状态与真实输出的事件。当前仅有静态审计及依赖元数据检查，尚未验证新链路。接入验证完成前，不删除现有内置引擎及独立运行依赖。

独立运行现状见[内置引擎说明](bundled-engines.md)；该说明描述当前实现，本页描述接入试验的目标，不能互相当作已实现的能力。
