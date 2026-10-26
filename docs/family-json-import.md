# 算子族 JSON 导入

MegaKernel 左侧“导入 JSON”读取本地文件，整份替换当前会话的族目录；取消或校验失败保留原目录。刷新恢复内置目录；切换工作台保留当前导入。模板可从界面下载，也见 [模板文件](../data/opscope-families.example.json)。不上传文件、不保存到服务或执行代码。

```json
{
  "schema": "opscope-families-v1",
  "families": [{
    "id": "my-matmul",
    "name": "矩阵乘实现",
    "source_family_id": "matmul-family",
    "members": [
      {"id": "matmul/v1", "name": "基础实现", "kind": "operator"},
      {"id": "matmul/mega", "name": "流水实现", "kind": "operator"},
      {"id": "my/new", "name": "新融合实现", "kind": "fusion"}
    ]
  }]
}
```

- `id` 是稳定身份；族 ID 不重复，族内成员 ID 不重复；名称可修改。
- `kind`：`operator` 单算子、`fusion` 融合算子、`sequence` 算子组合。
- `source_family_id` 可选，关联内置结果目录及输入契约：`matmul-family`、`bmm-family`、`shared-family`、`fused-family`、`attention-family`。已知成员必须属于所引用的同一计算语义。新族没有对应数据目录时省略此字段，成员会列为待接入。
- 已有成员按 ID 绑定当前硬件及完整尺寸的预设结果。导入只筛选和重命名，不计算性能、图宽、加速比，不按照名称匹配。新成员保留定义并显示待接入，不填零或借用别人的结果。
- 限制：1 MB、最多100个族，每族最多100个成员，文本1–120字符；非JSON、版本不符、重复ID、非法类型、跨语义成员都拒绝。
- 当前“导出对比数据”包含导入后的当前族定义及筛选结果；`synthetic` 继续保留。性能接口接入后应由后端提供同一身份下的结果及预处理比较关系。
