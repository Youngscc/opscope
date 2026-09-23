# 内置评估引擎迁移

## 目标

OpScope 克隆后只依赖本仓库和常规 Python/Node 安装步骤即可运行评估，不再要求另行取得 `modeling` 仓库、填写其绝对路径或维护外部 TileSim 虚拟环境。

## 边界

- Roofline 只迁移 OpScope 已开放的 11 个基础算子公式、输出形状推导和 11 个硬件档案；不复制 modeling 的任务系统、数据库、训练搜索、查表回退或校准库。
- 内置公式保持当前 FLOPs、读写字节、cube/vector 峰值、`compute_ratio`、HBM 带宽和 `bw_gmem_ratio` 口径。上游没有的 910B1/B4 Roofline 规格继续缺失。
- TileSim 使用已审计的 `msopmodeling 1.0.9` 原始 wheel。wheel 与许可证副本随仓库保存，依赖由 `setup.sh` 安装到 OpScope `.venv`；运行仍在隔离临时目录中，不复制生成的 trace。
- Profiling、方法3和方法4仍无真实后端。预测继续标记 `measurement=false`，不冒充真机结果。

## 结构

```text
opscope/evaluation/bundled_roofline.py
  ├─ 规范张量与输出推导
  ├─ 11 类算子工作量公式
  ├─ 内置硬件规格读取
  └─ Roofline 时延与来源信息

opscope/evaluation/data/roofline_hardware.json
  └─ 从上游受跟踪硬件档案提取的必要字段与内容摘要

vendor/msopmodeling/
  ├─ msopmodeling-1.0.9-py3-none-any.whl
  ├─ LICENSE
  └─ README.md
```

服务默认以当前 `.venv/bin/python` 启动两个 worker。环境变量和启动参数保留为高级覆盖入口，用于以后验证其他上游版本；空配置不再表示演示模式。

## 验证

1. 对 11 个基础算子核对输出形状、FLOPs、读写字节和缺失语义。
2. 对默认 MatMul 在六个服务器规格上与迁移前结果逐字段比较。
3. 在临时目录中隐藏外部 modeling 路径，验证 `/capabilities` 就绪、Roofline 批次成功。
4. 使用仓库 wheel 验证 TileSim probe 和至少一个受支持组合；若当前平台无法重新安装，必须记录为未验证，不能将 import 成功等同于模型执行成功。
5. 运行全部 Python/前端测试、生产构建和离线生成。
