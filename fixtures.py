"""Deterministic synthetic fixtures for UI review, never hardware benchmarks."""

HARDWARE = [
    ("ascend", "Ascend 9382", "NPU", "Adevice03 · SoC Ascend910_9382"),
    ("h100", "NVIDIA H100", "GPU", "Hopper · 独立示例配置"),
    ("h200", "NVIDIA H200", "GPU", "Hopper · 独立示例配置"),
    ("b200", "NVIDIA B200", "GPU", "Blackwell · 详细仿真待验证"),
    ("b300", "NVIDIA B300", "GPU", "Blackwell · 详细仿真待验证"),
    ("r200", "R200", "待确认", "项目别名 · 正式 SKU 待核实"),
]
METHODS = [
    ("profile", "真机 Profiling", "采集报告", "profile"),
    ("roofline", "Roofline", "解析模型", "roofline"),
    ("tilesim", "Tilesim", "仿真", "tilesim"),
    ("method3", "方法3", "虚拟数据", "method3"),
    ("method4", "方法4", "虚拟数据", "method4"),
]
# These illustrative numbers are deliberately independent of real device specs.
VALUES = {
    "ascend": {"profile": 248.0, "roofline": 232.0, "tilesim": 260.0},
    "h100": {"profile": 162.0, "roofline": 157.0, "tilesim": 176.0},
    "h200": {"profile": 148.0, "roofline": 145.0, "tilesim": 160.0},
}

# HBM MiB, L2 hit %, matrix activity %, auxiliary activity %, HBM activity %.
RESOURCE_STATS = {
    ('ascend', 'profile'): (112, 68, 76, 19, 61),
    ('h100', 'profile'): (104, 78, 82, 14, 58),
    ('h100', 'accel'): (120, 71, 74, 19, 66),
    ('h200', 'profile'): (100, 83, 85, 12, 54),
    ('h200', 'accel'): (108, 76, 78, 17, 62),
}

VALUES.update({
    'b200': {'profile': 96.0, 'roofline': 76.0, 'tilesim': 102.0},
    'b300': {'profile': 84.0, 'roofline': 68.0, 'tilesim': 89.0},
})

# Placeholder methods have totals only, with no claimed simulator or device support.
for hardware, method3, method4 in [
    ('ascend', 255.0, 239.0), ('h100', 170.0, 158.0), ('h200', 152.0, 146.0),
    ('b200', 100.0, 92.0), ('b300', 86.0, 81.0),
]:
    VALUES[hardware].update(method3=method3, method4=method4)

# Illustrative calibration metadata, not a loaded project calibration library.
ROOFLINE_CONFIG = {
    'ascend': {'status': 'calibrated', 'label': '已校准', 'source': 'bucket',
               'source_label': '形状分桶', 'version': 'demo-cal-v1',
               'match': 'Ascend 9382 · MatMul · FP16 · M/N/K = 4096',
               'factor': 232 / 190},
    'h100': {'status': 'calibrated', 'label': '已校准', 'source': 'aggregate',
             'source_label': '聚合参数', 'version': 'demo-cal-v1',
             'match': 'H100 · MatMul · FP16', 'factor': 157 / 120},
    'h200': {'status': 'calibrated', 'label': '已校准', 'source': 'regression',
             'source_label': '回归预测', 'version': 'demo-reg-v1',
             'match': 'H200 · MatMul · FP16', 'factor': None},
    'b200': {'status': 'generic', 'label': '通用估算', 'source': 'heuristic',
             'source_label': '通用参数', 'version': 'ui-demo-v3',
             'match': '未命中校准数据', 'factor': None},
    'b300': {'status': 'generic', 'label': '通用估算', 'source': 'heuristic',
             'source_label': '通用参数', 'version': 'ui-demo-v3',
             'match': '未命中校准数据', 'factor': None},
}
RESOURCE_STATS.update({
    ('ascend', 'tilesim'): (128, 61, 71, 23, 69),
    ('h100', 'tilesim'): (116, 72, 75, 18, 64),
    ('h200', 'tilesim'): (112, 75, 79, 16, 60),
    ('b200', 'profile'): (100, 84, 87, 11, 52),
    ('b200', 'tilesim'): (108, 77, 80, 15, 59),
    ('b300', 'profile'): (98, 87, 90, 9, 49),
    ('b300', 'tilesim'): (106, 80, 83, 13, 56),
})
# Tile M/N/K, buffer stages, shared/local buffer KiB, illustrative clock MHz.
EXECUTION_CONFIG = {
    'ascend': ((128, 128, 64), 2, 128, 1500),
    'h100': ((128, 128, 64), 3, 96, 1800),
    'h200': ((128, 256, 64), 3, 128, 1800),
    'b200': ((128, 256, 128), 4, 192, 1900),
    'b300': ((256, 256, 64), 4, 224, 2000),
}
BOUND_HINTS = {
    ('ascend', 'profile'): '计算 / 搬运', ('ascend', 'tilesim'): '同步等待',
    ('h100', 'profile'): '计算', ('h100', 'tilesim'): '访存 / 同步',
    ('h100', 'accel'): '同步等待', ('h200', 'profile'): '计算',
    ('h200', 'tilesim'): '同步等待', ('h200', 'accel'): '计算 / 同步',
    ('b200', 'profile'): '计算', ('b200', 'tilesim'): '访存 / 同步',
    ('b300', 'profile'): '计算', ('b300', 'tilesim'): '同步等待',
}
