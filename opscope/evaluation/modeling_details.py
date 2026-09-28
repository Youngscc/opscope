"""Display shared model fields without reconstructing native execution details."""
import json

from opscope.offline.task_details import facts
from .evaluation_results import number


def remote_details(row):
    r = row['raw_result']
    source = r['field_sources']
    def metric(label, key, unit=''):
        origin = ' · Roofline 补充' if source.get(key) == 'roofline.supplement' else ''
        return label, number(r.get(key), unit) + origin
    hardware = r['hardware_spec']
    native = r.get('model_result', {})
    components = native.get('component_latency', {})
    latency_note = ('补充分项不等于 TileSim 原生流水；分项不能直接相加。' if r['backend'] == 'tilesim'
                    else '模型预测不等于设备实测；计算与访存成本不直接相加。')
    return {
        'overview': facts([metric('总时延', 'latency_us', ' μs'), ('实际方法', r['backend']),
                            ('数据性质', '模型预测 · 非设备实测'), ('结果 ID', row['id']),
                            ('执行时间', row['task']['finished_at'])]),
        'latency': facts([metric('计算成本', 'compute_us', ' μs'), metric('访存成本', 'memory_us', ' μs')])
            + '<p class="note">' + latency_note + '</p>',
        'compute': facts([metric('逻辑工作量', 'flops', ' FLOPs'),
                          ('有效算力', row['summary']['throughput'] + ' TFLOP/s'),
                          metric('利用率', 'hw_utilization')]),
        'memory': facts([metric('读取量', 'read_bytes', ' B'), metric('写入量', 'write_bytes', ' B'),
                         metric('算术强度', 'arithmetic_intensity', ' FLOP/B')]),
        'pipeline': '<p class="note">当前模型接口未返回事件流水。</p>'
            + (facts([(key, number(value, ' μs')) for key, value in components.items()]) if r['engine']['mode'] != 'cost-theo' else ''),
        'inputs': facts([(t['name'], f"{t['shape']} · {t['dtype']}") for t in row['workload']['tensors']])
            + '<h4>输出</h4>' + facts([(t['name'], f"{t['shape']} · {t['dtype']}") for t in r['outputs']]),
        'hardware': facts([('型号', hardware['name']), ('芯片', hardware.get('chip_name', '—')),
                           ('配置摘要', r['hardware_hash'])]),
        'evidence': facts([('实际方法', r['backend']), ('模型模式', r['engine']['mode']), ('方法回退', '无'),
                           ('工作量来源', r.get('workload_source') or '—'),
                           ('SFU 成本策略', (r.get('model_workload') or {}).get('sfu_policy') or '不适用'),
                           ('有效维度参数', json.dumps(r.get('effective_parameters', {}), ensure_ascii=False)),
                           ('引擎版本', r['engine']['revision']), ('算子版本', r['operator_hash']),
                           ('校准来源', r.get('calibration_source') or '未命中校准'),
                           ('分项缺失原因', r.get('supplement_reason') or '无'),
                           ('实际模型输入', json.dumps(r.get('effective_input'), ensure_ascii=False)),
                           ('评估程序墙钟耗时', number(r['wall_time_ms'], ' ms'))]),
    }
