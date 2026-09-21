"""Task context for synthetic single-operator results, without invented runs."""
import html

from fixtures import HARDWARE, METHODS


def workload_record():
    tensors = [{'name': name, 'role': role, 'shape': [4096, 4096],
                'dtype': 'FP16', 'bytes': 33554432}
               for name, role in [('A', 'input'), ('B', 'input'), ('C', 'output')]]
    return {'id': 'demo-matmul-4096-fp16', 'operator': 'MatMul',
            'm': 4096, 'n': 4096, 'k': 4096, 'tensors': tensors,
            'layout': 'row-major', 'transpose_a': False, 'transpose_b': False,
            'accumulator_dtype': 'FP32', 'boundary': 'device kernel only',
            'input_bytes': 67108864, 'output_bytes': 33554432,
            'logical_bytes': 100663296, 'flops': 137438953472,
            'arithmetic_intensity': 1365.3333333333333, 'synthetic': True}


def task_context(hardware, method, result_id, available):
    device = next(item for item in HARDWARE if item[0] == hardware)
    return {
        'task': {'result_id': result_id, 'workload_id': 'demo-matmul-4096-fp16',
                 'task_id': None, 'run_id': None, 'status': 'demo' if available else 'unavailable',
                 'requested_method': method, 'actual_backend': None,
                 'fallback_reason': None, 'created_at': None, 'started_at': None,
                 'finished_at': None, 'wall_time_ms': None, 'report_uri': None,
                 'source': 'synthetic_fixture', 'synthetic': True},
        'workload': workload_record(),
        'hardware_snapshot': {'id': hardware, 'name': device[1], 'family': device[2],
                              'description': device[3], 'snapshot_id': None,
                              'memory_gib': None, 'hbm_bandwidth_gbs': None,
                              'l2_mib': None, 'fp16_peak_tflops': None,
                              'compute_units': None, 'software_version': None,
                              'status': 'not_captured'},
    }


def facts(rows):
    return '<dl class="facts">' + ''.join(
        f'<div><dt>{html.escape(label)}</dt><dd>{html.escape(str(value)) if value is not None else "—"}</dd></div>'
        for label, value in rows) + '</dl>'


def task_overview(context, result):
    task = context['task']
    method = next(item[1] for item in METHODS if item[0] == task['requested_method'])
    hero = facts([('总时延', f"{result['latency_us']:.2f} μs"),
                  ('有效算力', result['summary']['throughput'] + ' TFLOP/s'),
                  ('相对参考偏差', result['deviation']), ('主要瓶颈', result['bound'])])
    identity = facts([('结果 ID', task['result_id']), ('工作负载 ID', task['workload_id']),
                      ('请求方法', method), ('实际执行后端', '未执行 · 示例数据'),
                      ('数据来源', '本地合成 fixture'), ('运行状态', '示例记录 · 非真实任务'),
                      ('任务 ID / Run ID', '未创建'), ('回退情况', '未执行，无回退记录')])
    run = facts([('创建时间', task['created_at']), ('开始 / 完成时间', None),
                 ('任务墙钟耗时', task['wall_time_ms']), ('原始报告', '未导入')])
    note = '仅演示结果；任务墙钟耗时与设备侧 kernel 时延是不同口径。'
    if task['requested_method'] == 'tilesim':
        note += ' TileSim 分项与流水为扩展字段示例，不代表当前适配器输出。'
    return ('<div class="task-metrics">' + hero + '</div><p class="note">' + note + '</p>'
            + '<details class="task-run"><summary>任务、来源与运行记录</summary>' + identity
            + '<h4>运行记录与报告</h4>' + run + '</details>')


def input_detail(workload):
    rows = ''
    for tensor in workload['tensors']:
        role = '输入' if tensor['role'] == 'input' else '输出（形状推导）'
        shape = ' × '.join(map(str, tensor['shape']))
        rows += (f'<tr><td>{role}</td><th scope="row">{tensor["name"]}</th><td>{shape}</td>'
                 f'<td>{tensor["dtype"]}</td><td>{tensor["bytes"] / 1024 ** 2:.0f} MiB</td></tr>')
    table = ('<div class="tensor-scroll" tabindex="0" role="region" aria-label="输入输出张量表">'
             '<table class="tensor-table"><caption>Tensor Footprint · 张量占用</caption>'
             '<thead><tr><th scope="col">角色</th><th scope="col">名称</th><th scope="col">形状</th>'
             '<th scope="col">精度</th><th scope="col">数据量</th></tr></thead><tbody>' + rows + '</tbody></table></div>')
    config = facts([('算子 / M · N · K', 'MatMul / 4096 · 4096 · 4096'),
                    ('布局', workload['layout']), ('转置 A / B', '否 / 否'),
                    ('累加精度', workload['accumulator_dtype']),
                    ('评估边界', '设备侧单 kernel'), ('不包含', 'Host 启动、H2D / D2H、框架开销')])
    totals = facts([('输入合计', f"{workload['input_bytes'] / 1024 ** 2:.0f} MiB"),
                    ('输出合计', f"{workload['output_bytes'] / 1024 ** 2:.0f} MiB"),
                    ('逻辑读写', f"{workload['logical_bytes'] / 1024 ** 2:.0f} MiB"),
                    ('逻辑工作量', f"{workload['flops'] / 1e9:.2f} GFLOPs"), ('计算公式', '2 × M × N × K'),
                    ('逻辑算术强度', f"{workload['arithmetic_intensity']:.2f} FLOP/Byte")])
    return config + '<h4>输入与输出</h4>' + table + '<h4>工作量与数据量</h4>' + totals + '<p class="note">张量占用不等于峰值显存；逻辑读写不等于实际 HBM 流量。</p>'


def hardware_detail(snapshot):
    identity = facts([('硬件', snapshot['name']), ('设备类型', snapshot['family']),
                      ('目录说明', snapshot['description']), ('提交时快照', '未采集')])
    specs = facts([('显存容量（GiB）', snapshot['memory_gib']),
                   ('HBM 峰值带宽（GB/s）', snapshot['hbm_bandwidth_gbs']),
                   ('L2 容量（MiB）', snapshot['l2_mib']),
                   ('FP16 峰值（TFLOP/s）', snapshot['fp16_peak_tflops']),
                   ('计算单元数', snapshot['compute_units']),
                   ('驱动 / 运行时版本', snapshot['software_version'])])
    return identity + '<h4>硬件规格</h4>' + specs + '<p class="note">未导入真实硬件快照，缺失规格不填零。执行依据中的示例时钟与 Tiling 不能用于证明硬件参数或模拟器支持。</p>'
