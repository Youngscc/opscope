"""Synthetic totals for unnamed methods; never invent an execution backend."""
from .task_details import facts, hardware_detail, input_detail, task_overview


def virtual_result(row, latency, reference, summary, max_time):
    error = (latency - reference) / reference * 100
    row.update({'latency_us': latency, 'latency': f'{latency:.2f}',
                'bar_width': round(latency / max_time * 100, 3),
                'deviation_percent': error, 'deviation': f'{error:+.1f}%',
                'error_class': 'near' if abs(error) <= 5 else 'far',
                'compute': '—', 'memory': '—', 'bound': None,
                'source_label': '虚拟数据', 'summary': summary,
                'execution': {'kind': 'virtual', 'synthetic': True, 'source': '虚拟数据',
                              'latency_us': latency, 'compute_us': None, 'memory_us': None,
                              'wait_us': None, 'bound': None, 'events': [], 'instances': []}})
    note = '<p class="note">手工虚拟耗时，仅用于界面对比；未指定实际方法或执行后端。</p>'
    absent = '<div class="empty-detail"><span class="empty-mark">—</span><p>仅提供虚拟总耗时，暂无分项数据。</p></div>'
    row['details'] = {
        'latency': facts([('总时延', f'{latency:.2f} μs'), ('边界', '设备侧单 kernel'),
                          ('Profiling 参考', f'{reference:.2f} μs'), ('偏差', f'{error:+.1f}%')]) + note,
        'compute': facts([('有效算力（FLOPs / 总时延）', summary['throughput'] + ' TFLOP/s'),
                          ('计算分项', None), ('资源活动', None)]) + note,
        'memory': facts([('逻辑读写', f"{row['workload']['logical_bytes'] / 1024 ** 2:g} MiB"),
                         ('实际流量', None), ('访存分项', None)]) + absent,
        'pipeline': '<div class="empty-detail"><span class="empty-mark">—</span><p>虚拟方法没有执行记录，不生成指令级流水。</p></div>',
        'evidence': facts([('数据性质', '手工虚拟数据'), ('实际后端', None),
                           ('执行内核 / Tiling', None), ('原始报告', None)]) + note,
        'inputs': input_detail(row['workload']),
        'hardware': hardware_detail(row['hardware_snapshot']),
    }
    row['details']['overview'] = task_overview(row, row)
    return row
