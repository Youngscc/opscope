# 方法顺序与 lookup 预设

矩阵、筛选、图例和报告统一使用：真机数据 → MSKPP → ESL → Roofline → TileSim。保持内部 ID `profile/method3/method4/roofline/tilesim`，避免旧任务与示例关联失效。前三项的方法配置 `backend=lookup`，后两项保持自身引擎；结果增加方法名称与预设后端，JSON 可直接识别。预设类型不等于 `actual_backend`，未执行时实际后端继续为空。

当前只预设 lookup 接入方式，不引入数据文件、查找/插值算法或外部依赖。实际评估前三项返回缺少对应 lookup 数据源的原因，不回退计算；示例保持 synthetic=true，保留原始示例数值。真机数据继续是唯一参考基线，MSKPP/ESL 结果不能自动当作真机测量。

验证覆盖示例/在线的顺序、名称、预设类型、JSON 元数据、缺源状态及空值语义；桌面检查矩阵、筛选、对比详情与导出。Python 方法目录为唯一来源。
