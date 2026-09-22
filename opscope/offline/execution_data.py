"""Illustrative execution records, independent of actual hardware/tool output."""
from .fixtures import BOUND_HINTS, EXECUTION_CONFIG, RESOURCE_STATS, ROOFLINE_CONFIG


def roofline_record(hardware, latency):
    calibration = dict(ROOFLINE_CONFIG[hardware])
    regression = calibration['source'] == 'regression'
    return {'kind': 'analytic', 'synthetic': True, 'source': '合成示例',
            'bound': None if regression else '计算上界',
            'compute_us': None if regression else latency,
            'memory_us': None if regression else latency * .58,
            'calibration': calibration,
            'wait_us': None, 'instances': [], 'events': []}


def execution_record(hardware, method, latency):
    if method == 'roofline':
        return roofline_record(hardware, latency)
    tile, stages, buffer_kib, clock = EXECUTION_CONFIG[hardware]
    if method == 'tilesim':
        stages = max(2, stages - 1)
    record = {'kind': 'detailed', 'synthetic': True,
              'source': '扩展字段示例' if method == 'tilesim' else '合成示例',
              'tile': list(tile), 'stages': stages, 'buffer_kib': buffer_kib,
              'clock_mhz': clock, 'cycles': round(latency * clock),
              'split_k': 1, 'blocks': (4096 // tile[0]) * (4096 // tile[1]),
              'k_iterations': 4096 // tile[2],
              'kernel': f'demo_{hardware}_gemm_{tile[0]}x{tile[1]}x{tile[2]}',
              'bound': BOUND_HINTS[(hardware, method)]}
    stats = RESOURCE_STATS[(hardware, method)]
    wait_ratio = {'profile': .04, 'tilesim': .12, 'accel': .09}[method]
    seed = sum(ord(char) for char in hardware + method)
    instances = [max(1, min(100, stats[2] + (index * 7 + seed) % 19 - 9)) for index in range(24)]
    record.update({'compute_us': latency * stats[2] / 100,
                   'memory_us': latency * stats[4] / 100,
                   'wait_us': latency * wait_ratio, 'instances': instances,
                   'events': tile_events(hardware, method, latency)})
    return record


def tile_events(hardware, method, latency):
    lanes = ['MTE2 搬入', 'Cube 计算', 'MTE3 搬出'] if hardware == 'ascend' else ['TMA 搬入', 'Tensor 计算', 'Store 搬出']
    gap = {'profile': .008, 'tilesim': .022, 'accel': .015}[method]
    events = []
    for lane, name in enumerate(lanes):
        for tile in range(4):
            start = latency * (tile * .19 + lane * (.04 + gap))
            duration = latency * (.14 + lane * .008)
            events.append({'lane': name, 'lane_index': lane, 'tile': tile,
                           'start_us': round(start, 3),
                           'end_us': round(start + duration, 3)})
    return events
