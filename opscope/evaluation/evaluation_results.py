"""Turn structured engine output into safe, shared matrix/detail data."""
from copy import deepcopy
from datetime import datetime, timezone

from opscope.offline.build import build_payload
from opscope.offline.matrix_data import prepare_matrix
from opscope.offline.task_details import facts
from .tilesim_details import tile_details, trace_geometry


def stamp():
    return datetime.now(timezone.utc).isoformat()


def number(value, unit=''):
    return '—' if value is None else f'{value:,.6g}{unit}'


def detail_fields(row):
    r, work, hw = row['raw_result'], row['workload'], row['hardware_snapshot']
    catalog_mode = r['engine'].get('mode') == 'catalog-analytic'
    model_label = 'Roofline · 目录公式解析' if catalog_mode else 'Roofline · 内置基础模型'
    calibration_label = '此模式未进行校准' if catalog_mode else (r['calibration_source'] or '未命中校准')
    time = lambda key: number(r.get(key), ' μs')
    rate = row['summary']['throughput']
    rate = rate + ' TFLOP/s' if rate != '—' else rate
    overview = facts([('总时延', time('latency_us')), ('有效算力', rate),
                      ('相对参考偏差', '—'), ('主要瓶颈', {'compute': '计算受限', 'memory': '访存受限', 'latency': '固定开销'}.get(r['bound'], r['bound'] or '—')),
                      ('结果 ID', row['id']), ('实际执行后端', 'Roofline'),
                      ('数据性质', '模型预测 · 非设备实测'), ('运行状态', '已完成'),
                      ('执行时间', row['task']['finished_at'])])
    inputs = [(t['name'], f"{t['shape']} · {t['dtype']}") for t in work['tensors']]
    outputs = [(t['name'], f"{t['shape']} · {t['dtype']} · {t['bytes']} B") for t in r['outputs']]
    return {
        'overview': overview,
        'latency': facts([('Profiling 参考', '—'), ('计算成本', time('compute_us')),
                          ('访存成本', time('memory_us'))]) + '<p class="note">模型预测不等于设备实测；计算与访存成本不直接相加。</p>',
        'compute': facts([('逻辑工作量', number(r['flops'] / 1e9, ' GFLOPs')),
                          ('计算成本', time('compute_us')), ('有效算力', rate)]),
        'memory': facts([('模型读取', number(r['read_bytes'] / 1048576, ' MiB')),
                         ('模型写入', number(r['write_bytes'] / 1048576, ' MiB')),
                         ('访存成本', time('memory_us')),
                         ('算术强度', number(r['arithmetic_intensity'], ' FLOP/B'))]) + '<p class="note">模型字节数不代表实际 HBM 计数器。</p>',
        'pipeline': '<p class="note">Roofline 不生成指令级流水；核活动、kernel 与 tiling 未采集。</p>',
        'inputs': facts([('算子', work['operator']), ('评估边界', '单算子解析预测，不含Host/传输；未指定kernel'),
                         ('执行选项', '默认语义；不建模布局与累加精度差异')]) + '<h4>输入</h4>' + facts(inputs) + '<h4>推导输出</h4>' + facts(outputs),
        'hardware': facts([('实际规格', hw['name']), ('芯片', hw['chip_name']),
                           ('SoC', hw.get('soc_version') or '—'),
                           ('借用规格', hw.get('borrowed_from') or '无'),
                           ('矩阵FP16峰值', number(hw.get('compute', {}).get('cube', {}).get('fp16_tflops'), ' TFLOP/s')),
                           ('矩阵BF16峰值', number(hw.get('compute', {}).get('cube', {}).get('bf16_tflops'), ' TFLOP/s')),
                           ('显存', number(hw['memory']['capacity_gb'], ' GB')),
                           ('HBM峰值带宽', number(hw['memory']['hbm_bandwidth_gbps'], ' GB/s')),
                           ('硬件规格摘要', row['provenance']['hardware_hash'])]),
        'evidence': facts([('实际方法', model_label), ('方法回退', '无'),
                           ('校准来源', calibration_label),
                           ('模型假设', r.get('model_note') or '—'),
                           ('引擎版本', r['engine']['revision']), ('配置摘要', row['provenance']['configuration_hash']),
                           ('评估程序墙钟耗时', number(r['wall_time_ms'], ' ms'))]) + '<p class="note">程序墙钟耗时与预测的算子耗时是两个指标。</p>',
    }


def completed_row(row, raw, request, job_id):
    r = dict(raw['result'])
    events = r.pop('events', [])
    config = request['configuration']
    work = {'id': request['configuration_hash'], 'operator': config['operator'],
            'tensors': config['inputs'], 'outputs': r['outputs'], 'options': config['options'],
            'boundary': config['boundary'], 'synthetic': False}
    latency = r['latency_us']
    throughput = r['flops'] / latency / 1e6 if latency > 0 else None
    calibration = r['calibration_source']
    catalog_mode = r['engine'].get('mode') == 'catalog-analytic'
    row.update(available=True, reason=None, latency_us=latency, latency=f'{latency:.3f}',
               deviation_percent=None, deviation='—', bound=r['bound'],
               source_label='目录公式' if catalog_mode else ('已校准' if calibration else '通用估算'),
               source_class='estimate-status calibrated' if calibration else 'estimate-status generic',
               workload=work, hardware_snapshot=r['hardware_spec'], raw_result=r,
               compute=number(r['compute_us'], ' μs'), memory=number(r['memory_us'], ' μs'),
               summary={'throughput': number(throughput), 'activity': [], 'memory': None},
               provenance={'contract': 'opscope-evaluation-v1', 'configuration_hash': request['configuration_hash'],
                           'hardware_hash': r['hardware_hash'], 'engine': r['engine']},
               execution={'kind': 'analytic', 'synthetic': False, 'measurement': False,
                          'source': 'Roofline 目录公式预测' if catalog_mode else 'Roofline 模型预测', 'latency_us': latency,
                          'compute_us': r['compute_us'], 'memory_us': r['memory_us'],
                          'bound': r['bound'], 'events': [], 'instances': []})
    row['task'].update(actual_backend='roofline', finished_at=raw.get('finished_at') or stamp(), wall_time_ms=r['wall_time_ms'])
    if r['backend'] == 'tilesim':
        mode = r['engine'].get('mode', 'dsl-eng')
        label = '理论预测' if mode in {'dsl-theo', 'cost-theo'} else '工程预测'
        row.update(source_label=label, source_class='estimate-status generic')
        row['task']['actual_backend'] = 'tilesim'
        row['execution'].update(kind='tile_simulation', source='TileSim ' + label, events=events,
                                trace_view=trace_geometry(events, latency) if events else None)
        row['details'] = tile_details(row)
    else:
        row['details'] = detail_fields(row)
    return row


def evaluation_payload(request, raw, job_id):
    payload = build_payload()
    status = raw.get('status', 'completed')
    payload['demo_results'] = deepcopy(payload['results'])
    payload['demo_workload'] = payload['workload']
    payload['demo_matrix'] = payload['matrix']
    payload['demo_methods'] = deepcopy(payload['methods'])
    rows = deepcopy(payload['pending_results'])
    received = {(r['hardware'], r['method']): r for r in raw['rows']}
    for row in rows:
        item = received.get((row['hardware'], row['method']))
        row.update(id=f"{job_id}-{row['hardware']}-{row['method']}", synthetic=False,
                   measurement=False, workload={'operator': request['configuration']['operator'],
                                                'tensors': request['configuration']['inputs']})
        row['task'].update(task_id=job_id, run_id=job_id, synthetic=False,
                           source='model_prediction', status=item['status'] if item else 'not_run')
        row['reason'] = item.get('reason', '尚未评估') if item else '本批次未选择此组合'
        if item and item['status'] == 'succeeded':
            completed_row(row, item, request, job_id)
    count = sum(r['available'] for r in rows)
    payload.update(schema='opscope-evaluation-v1', synthetic=False, notice='实际模型调用 · 预测结果，非设备实测',
                   results=rows, workload={'operator': request['configuration']['operator'],
                                           'boundary': request['configuration']['boundary']},
                   matrix=prepare_matrix(rows), initial_configuration=request['configuration'],
                   evaluation={'id': job_id, 'configuration_hash': request['configuration_hash'],
                               'hardware_ids': request['hardware_ids'], 'method_ids': request['method_ids'],
                               'status': status, 'completed_at': stamp() if status == 'completed' else None,
                               'success_count': count, 'finished_count': sum(r['status'] in {'succeeded', 'failed', 'unsupported'} for r in raw['rows']),
                               'total': len(request['hardware_ids']) * len(request['method_ids'])})
    for method in payload['methods']:
        method['source'] = {'roofline': '解析预测', 'tilesim': '仿真预测', 'profile': '未接入参考',
                            'method3': '未接入', 'method4': '未接入'}[method['id']]
    return payload
