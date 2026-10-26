"""Complete static-dialog samples without changing real engine contracts."""
from .task_details import facts
from .analysis_display import sample_analysis
from .execution_data import execution_record

# Fictional display configurations, not verified specifications of these SKUs.
DISPLAY_SPECS = {
    'ascend': (64, 1800, 32, 640, 24, 1500),
    'h100': (80, 3200, 48, 1000, 120, 1800),
    'h200': (144, 4800, 64, 1200, 132, 1800),
    'b200': (192, 8000, 96, 2400, 144, 1800),
    'b300': (288, 9600, 128, 2800, 160, 1800),
}


def sample_values(row):
    index = ['profile', 'method3', 'method4', 'tilesim', 'roofline'].index(row['method'])
    memory, bandwidth, l2, peak, units, clock = DISPLAY_SPECS[row['hardware']]
    latency = row['latency_us']
    traffic = [112, 128, 104, 120, 96][index]
    return dict(synthetic=True, memory_gib=memory, peak_bandwidth_gbs=bandwidth,
                l2_mib=l2, fp16_peak_tflops=peak, compute_units=units, clock_mhz=clock,
                traffic_mib=traffic, bandwidth_gbs=traffic*2**20/latency/1000,
                compute_us=round(latency*(.72+.02*index), 2),
                memory_us=round(latency*(.56+.03*index), 2),
                wait_us=round(latency*.04, 2), l2_hit=[.78,.72,.84,.69,.86][index],
                shared_utilization=.64, cycles=round(latency*clock))


def sample_sections(row, sample):
    from .build import timeline, phase_bars, heatmap
    npu = row['hardware']=='ascend'
    analytic = row['method']=='roofline'
    latency = row['latency_us']
    record = execution_record(row['hardware'], 'profile', latency)
    record.update(kind='analytic' if analytic else 'detailed',
                  compute_us=sample['compute_us'], memory_us=sample['memory_us'], wait_us=None if analytic else sample['wait_us'],
                  clock_mhz=sample['clock_mhz'], cycles=sample['cycles'])
    for event in record.get('events', []):
        if npu and event['lane_index']==2:
            event['lane']='Fixpipe 写回'
    sample['execution'] = record if not analytic else None
    row['details']['overview'] = facts([
        ('总时延', f'{latency:.2f} μs'), ('有效算力', row['summary']['throughput']+' TFLOP/s'),
        ('相对参考偏差', row['deviation']), ('主要瓶颈', '计算 / 搬运')])
    row['details']['latency'] = facts([('边界','设备侧单 kernel'),
        ('真机参考', f"{row['latency_us']/(1+(row['deviation_percent'] or 0)/100):.2f} μs")]) + phase_bars(record)
    row['details']['compute'] = facts([('逻辑工作量','137.44 GFLOPs'), ('输入 / 累加精度','FP16 / FP32'),
        ('有效算力',row['summary']['throughput']+' TFLOP/s'), ('计算活动' if not analytic else '计算成本',f"{sample['compute_us']:.2f} μs")])
    row['details']['memory'] = facts([('逻辑读取','64 MiB'), ('逻辑写入','32 MiB'),
        ('累计读写量',f"{sample['traffic_mib']} MiB"), ('平均访问带宽',f"{sample['bandwidth_gbs']:.2f} GB/s"),
        ('逻辑算术强度','1365.33 FLOP/Byte'), ('L2 命中率',f"{sample['l2_hit']*100:.1f}%")])
    row['details']['pipeline'] = ('<p>解析模型不生成执行流水。</p>' if analytic else
        facts([('计算活动',f"{sample['compute_us']:.2f} μs"), ('搬运活动',f"{sample['memory_us']:.2f} μs"),
               ('同步等待',f"{sample['wait_us']:.2f} μs")]) + heatmap(row['hardware'], record) + display_timeline(record))
    row['details']['hardware'] = facts([('硬件',row['hardware_snapshot']['name']), ('参数口径','虚拟展示配置'),
        ('显存容量',f"{sample['memory_gib']} GiB"), ('峰值带宽',f"{sample['peak_bandwidth_gbs']} GB/s"),
        ('L2 容量',f"{sample['l2_mib']} MiB"), ('FP16 峰值',f"{sample['fp16_peak_tflops']} TFLOP/s"),
        ('计算单元数',sample['compute_units']), ('时钟',f"{sample['clock_mhz']} MHz")])
    row['details']['evidence'] = facts([('方法',row['method_name']), ('任务精度','FP16 / FP32'),
        ('M / N / K','4096 / 4096 / 4096'), ('工作量','137.44 GFLOPs'),
        ('计时边界','设备侧单 kernel'), ('数据标记','synthetic')])
    if not analytic:
        row['details']['evidence'] += facts([('Tile M / N / K',' × '.join(map(str,record['tile']))),
            ('流水级数',record['stages']), ('局部缓冲',f"{record['buffer_kib']} KiB"),
            ('Block 数',record['blocks']), ('K 迭代数',record['k_iterations']),
            ('Split-K',record['split_k']), ('等效周期',f"{sample['cycles']:,}")])
    row['details']['pipeline'] = row['details']['pipeline'].replace(' · 24 个示意实例',' · 24 个实例').replace('（示意）','')


def complete_static_details(row):
    sample = sample_values(row)
    row['presentation_sample'] = sample
    sample_sections(row, sample)
    row['analysis'] = sample_analysis(row['latency_us'], npu=row['hardware']=='ascend',
                                     l2=sample['l2_hit'], clock_mhz=sample['clock_mhz'])
    row['analysis']['synthetic'] = True
    if row['hardware']!='ascend':
        row['analysis']['gpu'] = dict(shared_memory_utilization=.64,
                                     tensor_cycles=88, simt_cycles=28, load_cycles=48, store_cycles=20)


def finish_static_sections(row):
    # No invented NPU counters for GPU or trace artifacts for analytic methods.
    sample = row['presentation_sample']
    resource = row['sections']['overview'][2]
    if row['hardware']!='ascend':
        resource['facts'][2] = dict(label='共享内存占用率', value='64.0%', known=True)
    decorate_static_sections(row)
    pipe = row['sections']['execution'][1]
    if row['method']=='roofline':
        pipe.update(facts=[], extra='<p>解析模型不生成流水组件周期。</p>')
    else:
        npu = row['hardware']=='ascend'
        components = (row['analysis']['pipe_cycles']['components'] if npu else
                      {k:v for k,v in row['analysis']['gpu'].items() if k.endswith('_cycles')})
        labels = {'tensor_cycles':'Tensor', 'simt_cycles':'SIMT', 'load_cycles':'Load', 'store_cycles':'Store'}
        pipe['facts'] = [dict(label=labels.get(k,k.upper()), value=str(v), known=True) for k,v in components.items()]
        pipe['extra'] = ''
        values = list(components.values())
        for fact, value in zip(pipe['facts'], values):
            if value == max(values):
                fact.update(tone='maximum', subtitle='最高')
            elif value == min(values):
                fact.update(tone='minimum', subtitle='最低')


def decorate_static_sections(row):
    """Prepare display-only annotations from the same sample, never from UI parsing."""
    sample = row['presentation_sample']
    compute = row['sections']['cost'][0]['facts']
    compute[2].update(subtitle=f"峰值 {sample['fp16_peak_tflops']:,} TFLOP/s",
                      width=min(100, float(row['summary']['throughput'])/sample['fp16_peak_tflops']*100))
    compute[3].update(subtitle=f"占总时延 {sample['compute_us']/row['latency_us']*100:.1f}%",
                      width=sample['compute_us']/row['latency_us']*100, tone='green')
    memory = row['sections']['cost'][1]['facts']
    memory[3].update(subtitle=f"峰值 {sample['peak_bandwidth_gbs']:,} GB/s",
                     width=min(100,sample['bandwidth_gbs']/sample['peak_bandwidth_gbs']*100), tone='orange')
    memory[5].update(subtitle=f"未命中 {(1-sample['l2_hit'])*100:.1f}%",
                     width=sample['l2_hit']*100, tone='green wide-fact')
    section = row['sections']['overview'][1]
    analytic = row['method']=='roofline'
    qualifier = '成本' if analytic else '活动'
    bars = ''.join(f'<div class="overlap-bar {kind}" style="width:{sample[key]/row["latency_us"]*100:.3f}%">'
                   f'{label}{qualifier} {sample[key]:.1f} μs</div>'
                   for key,kind,label in [('compute_us','compute','计算'),('memory_us','memory','访存')])
    wait = '' if analytic else f'<p class="wait-key"><i></i>同步等待：{sample["wait_us"]:.1f} μs</p>'
    section['extra'] = ('<div class="overlap-bars">'+bars+'</div>'+wait+
                        '<p class="overlap-note">ⓘ 计算与访存可并行重叠，耗时不完全相加。</p>')


def display_timeline(record):
    from .build import timeline
    # Grey bands are gaps in this local event window, not inferred stall causes.
    gaps = []
    for lane in range(3):
        end = 0
        for event in sorted((e for e in record['events'] if e['lane_index']==lane), key=lambda e:e['start_us']):
            start = min(320, event['start_us'])
            if start > end:
                gaps.append(f'<rect class="detail-idle-guide" x="{100+end:.1f}" y="{32+lane*36}" width="{start-end:.1f}" height="24" fill="#e5e9f0"/>')
            end = min(320, max(end, event['end_us']))
        if end < 320:
            gaps.append(f'<rect class="detail-idle-guide" x="{100+end:.1f}" y="{32+lane*36}" width="{320-end:.1f}" height="24" fill="#e5e9f0"/>')
    result = timeline(record)
    at = result.index('</title>') + len('</title>')
    return result[:at] + ''.join(gaps) + result[at:]
