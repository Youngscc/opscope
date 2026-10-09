"""Synthetic UI scenarios; none of these values are inferred from evaluations."""
import json
from copy import deepcopy


def timeline(scale=1.0, profile="waiting"):
    ranges = {
        "waiting": [[(0, 12), (20, 16), (48, 12), (66, 12)],
                    [(13, 10), (37, 10), (61, 9), (79, 12)],
                    [(24, 6), (49, 6), (73, 6), (93, 7)]],
        "compute": [[(0, 9), (19, 9), (39, 9), (59, 9)],
                    [(10, 22), (36, 22), (60, 22), (86, 10)],
                    [(33, 5), (59, 5), (83, 5), (96, 4)]],
        "memory": [[(0, 10), (24, 19), (52, 12), (76, 10)],
                   [(11, 17), (44, 13), (65, 11), (87, 10)],
                   [(29, 7), (58, 6), (77, 8), (97, 3)]],
    }[profile]
    lanes = [("MTE2", "数据搬入", "memory", ranges[0]),
             ("CUBE", "矩阵计算", "compute", ranges[1]),
             ("MTE3", "结果写回", "store", ranges[2])]
    return [{"name": name, "label": label, "kind": kind, "segments": [
        {"left": start, "width": duration, "label": f"{duration * scale:.1f} μs",
         "detail": f"{start * scale:.1f}–{(start + duration) * scale:.1f} μs"}
        for start, duration in ranges]} for name, label, kind, ranges in lanes]


def diagnostic_sizes(operator_id):
    values = (1024, 2048, 4096) if operator_id == "matmul" else (512, 2048, 4096)
    sizes = []
    for value in values:
        dims = [value] * 3 if operator_id == "matmul" else [1, 32, value, 128]
        tensors = [("A", [dims[0], dims[2]]), ("B", [dims[2], dims[1]])] if operator_id == "matmul" else [
            (name, dims[:]) for name in ("Q", "K", "V")]
        dtype = "FP16" if operator_id == "matmul" else "BF16"
        sizes.append(dict(id=str(value), dimensions=dims, shape=" × ".join(map(str, dims)),
                          inputs=[dict(name=name, shape=shape, dtype=dtype) for name, shape in tensors]))
    return sizes


def diagnostic_catalog():
    return {
        "operators": [dict(id="matmul", name="MatMul", dtype="FP16", axes=["M", "N", "K"],
                           input_template="A [M, K] · B [K, N]", default_size="4096", sizes=diagnostic_sizes("matmul")),
                      dict(id="attention", name="Attention", dtype="BF16", axes=["B", "H", "S", "D"],
                           input_template="Q / K / V [B, H, S, D]", default_size="2048", sizes=diagnostic_sizes("attention"))],
        "hardware": [dict(id="ascend-910b1", name="Ascend 910B1"),
                     dict(id="ascend-910b4", name="Ascend 910B4")],
        "synthetic": True,
    }


def primary_diagnostics():
    return [
        {"operator_id": "matmul", "hardware_id": "ascend-910b1",
         "bound": "访存受限", "title": "数据搬运让计算流水停了下来",
         "summary": "优先提高数据复用，再扩大计算与搬运的重叠。",
         "location": "数据搬入 → 矩阵计算", "latency_us": 126.4,
         "gauges": [("HBM 带宽占用", 87, "memory"), ("Cube 活跃比例", 58, "compute")],
         "focus_span": (23, 37), "focus": "等待下一块输入", "window_us": 100,
         "timeline_title": "计算在等什么？", "timeline_profile": "waiting",
         "actions": [("提高 Tile 复用", "优先", "调整 M / N 分块，减少对同一输入的重复搬入。", "验证 HBM 流量与总耗时"),
                     ("启用双缓冲", "其次", "让下一块输入的搬运与当前块计算交叠。", "验证 MTE2 / Cube 重叠"),
                     ("检查尾块负载", "后续", "缩小核间尾块差异，减少最后一轮的空闲。", "验证各核结束时间")],
         },
        {"operator_id": "attention", "hardware_id": "ascend-910b1",
         "bound": "同步等待", "title": "计算与 Softmax 之间出现了空档",
         "summary": "优先衔接 Cube 与 Vector 阶段，减少同步等待。",
         "location": "矩阵计算 → Softmax", "latency_us": 284.0,
         "gauges": [("Vector 活跃比例", 71, "memory"), ("Cube 活跃比例", 46, "compute")],
         "focus_span": (46, 74), "focus": "等待阶段同步", "window_us": 200,
         "timeline_title": "计算在等什么？", "timeline_profile": "waiting",
         "actions": [("流水化 Softmax", "优先", "将 Softmax 与下一块矩阵计算交叠执行。", "验证 Cube / Vector 衔接"),
                     ("缩短同步范围", "其次", "检查事件依赖，让可独立执行的块更早开始。", "验证关键路径等待"),
                     ("平衡两阶段分块", "后续", "协调矩阵计算与 Vector 阶段的块大小。", "验证各阶段活跃比例")],
         },
    ]


def alternate_diagnostics():
    # These are independent presentation samples, not predictions of SKU differences.
    return [
        {"operator_id": "matmul", "hardware_id": "ascend-910b4",
         "bound": "计算受限", "title": "矩阵计算占据主要执行时间",
         "summary": "优先改进分块与指令排布，提升计算吞吐。",
         "location": "矩阵计算", "latency_us": 112.6,
         "gauges": [("Cube 活跃比例", 88, "compute"), ("HBM 带宽占用", 54, "memory")],
         "focus_span": (10, 32), "focus": "矩阵计算密集区间", "window_us": 100,
         "timeline_title": "计算集中在哪？", "timeline_profile": "compute",
         "actions": [("优化矩阵分块", "优先", "调整 M / N / K 分块，提高矩阵指令的有效工作量。", "验证 Cube 活跃比例与总耗时"),
                     ("交错计算与搬运", "其次", "将后续输入预取安排到当前计算期间。", "验证搬运与计算重叠"),
                     ("减少尾块计算", "后续", "优化尾块处理，减少无效填充和重复计算。", "验证有效计算比例")],
         },
        {"operator_id": "attention", "hardware_id": "ascend-910b4",
         "bound": "访存受限", "title": "K / V 重复搬入拖慢了执行",
         "summary": "优先复用 K / V 分块，减少中间结果落存。",
         "location": "K / V 搬入 → 矩阵计算", "latency_us": 238.8,
         "gauges": [("HBM 带宽占用", 82, "memory"), ("Cube 活跃比例", 64, "compute")],
         "focus_span": (56, 88), "focus": "等待 K / V 分块", "window_us": 200,
         "timeline_title": "计算在等什么？", "timeline_profile": "memory",
         "actions": [("提高 K / V 复用", "优先", "让相邻 Query 分块共享已搬入的 K / V 数据。", "验证重复读取量与总耗时"),
                     ("减少中间结果落存", "其次", "将矩阵计算与 Softmax 中间结果保留在片上。", "验证中间结果访存量"),
                     ("调整预取时机", "后续", "在当前分块计算期间提前搬入下一块 K / V。", "验证关键路径等待")],
         },
    ]


def sized_diagnostics():
    # Each tuple authors latency/window/interval/pressure; no size-based performance extrapolation.
    variants = {
        ("matmul", "ascend-910b1"): {"1024": (12.8, 10, (2.3, 3.7), (57, 42)),
                                    "2048": (34.8, 25, (5.75, 9.25), (76, 52))},
        ("matmul", "ascend-910b4"): {"1024": (11.4, 10, (1, 3.2), (61, 38)),
                                    "2048": (30.2, 25, (2.5, 8), (79, 47))},
        ("attention", "ascend-910b1"): {"512": (74.6, 50, (11.5, 18.5), (56, 38)),
                                       "4096": (842.0, 500, (115, 185), (84, 62))},
        ("attention", "ascend-910b4"): {"512": (63.2, 50, (14, 22), (68, 49)),
                                       "4096": (716.4, 500, (140, 220), (91, 61))},
    }
    rows = []
    for template in primary_diagnostics() + alternate_diagnostics():
        for size in diagnostic_sizes(template["operator_id"]):
            row = deepcopy(template)
            variant = variants[(row["operator_id"], row["hardware_id"])].get(size["id"])
            if variant:
                latency, window, span, pressures = variant
                row.update(latency_us=latency, window_us=window, focus_span=span,
                           gauges=[(label, value, kind) for (label, _, kind), value in zip(row["gauges"], pressures)])
            row.update(size_id=size["id"], dimensions=size["dimensions"], shape=size["shape"], inputs=size["inputs"])
            rows.append(row)
    return rows


def diagnostic_cases():
    catalog = diagnostic_catalog()
    operators = {row["id"]: row for row in catalog["operators"]}
    hardware = {row["id"]: row for row in catalog["hardware"]}
    cases = sized_diagnostics()
    for case in cases:
        operator = operators[case["operator_id"]]
        case.update(id=f'{case["operator_id"]}/{case["hardware_id"]}/{case["size_id"]}', synthetic=True,
                    operator=operator["name"], dtype=operator["dtype"],
                    hardware=hardware[case["hardware_id"]]["name"], latency=f'{case["latency_us"]:.1f}')
        case["gauges"] = [dict(label=label, value=value, kind=kind) for label, value, kind in case["gauges"]]
        case["actions"] = [dict(title=title, priority=priority, detail=detail, check=check)
                           for title, priority, detail, check in case["actions"]]
        duration = case["window_us"]
        case["timeline"] = timeline(duration / 100, case.pop("timeline_profile"))
        if case["operator_id"] == "attention":
            case["timeline"][2].update(name="VECTOR", label="Softmax", kind="vector")
        start, end = case.pop("focus_span")
        case["focus_region"] = dict(start_us=start, end_us=end, left=round(start / duration * 100, 3),
                                    width=round((end - start) / duration * 100, 3))
        case["focus_range"] = f"{start:g}–{end:g} μs"
        case["window"] = f"局部窗口 · 0–{duration} μs"
        case["ticks"] = [f"{duration * i / 4:g}" for i in range(4)] + [f"{duration} μs"]
    return cases


def implementation_specs(scope):
    # Membership and types are authored explicitly, never inferred from a kernel name.
    return {
        "matmul": [
            ("v1", "matmul_v1", "operator", "基础实现", 1, 144, ["MatMul"]),
            ("v2", "matmul_v2", "operator", "双缓冲", 1, 120, ["MatMul"]),
            ("v3", "matmul_v3", "operator", "Tile 复用", 1, 96, ["MatMul"]),
            ("linear", "linear", "operator", "无 bias", 1, 104, ["Linear · bias=false"]),
            ("mega", "megakernel_mm", "operator", "多阶段流水", 1, 96, ["MatMul"]),
        ],
        "fused": [
            ("separate", "MatMul + Bias + GELU", "sequence", "分算子", 3, 192, ["MatMul", "Bias", "GELU"]),
            ("linear", "linear + gelu", "sequence", "部分融合", 2, 128, ["Linear", "GELU"]),
            ("epilogue", "epilogue_fused", "fusion", "Epilogue 融合", 1, 96, ["MatMul · Bias · GELU"]),
            ("mega", "megakernel_fused", "fusion", "MegaKernel", 1, 96, ["MatMul · Bias · GELU"]),
        ],
        "attention": [
            ("separate", "QK + Softmax + PV", "sequence", "分算子", 3, 4096, ["QKᵀ / √d", "Softmax", "PV"]),
            ("v1", "attention_v1", "operator", "基础实现", 1, 2048, ["Attention"]),
            ("v2", "flash_attention_v2", "fusion", "分块融合", 1, 768, ["QK · Softmax · PV"]),
            ("mega", "megakernel_attention", "fusion", "流水融合", 1, 640, ["QK · Softmax · PV"]),
        ],
    }[scope]


def mega_families():
    definitions = [("matmul-family", "MatMul", [("matmul", "矩阵乘"), ("fused", "Linear + GELU")]),
                   ("attention-family", "Attention", [("attention", "标准 Attention")])]
    kinds = {"operator": "算子", "fusion": "融合算子", "sequence": "算子组合"}
    families = []
    for family_id, name, scopes in definitions:
        members, ranges = [], []
        for scope_id, label in scopes:
            specs = implementation_specs(scope_id)
            members.extend(dict(id=f"{scope_id}/{key}", name=member_name, kind=kind,
                                kind_label=kinds[kind], scope_id=scope_id)
                           for key, member_name, kind, *_ in specs)
            ranges.append(dict(id=scope_id, name=label, member_count=len(specs), sizes=[
                dict(id=size, label=f"S = {size}" if scope_id == "attention" else f"{size}³")
                for size in ("1024", "4096")]))
        families.append(dict(id=family_id, name=name, definition="manual", synthetic=True,
                             default_size="4096", member_count=len(members),
                             members=members, scopes=ranges))
    return families


def comparisons(rows):
    return {base["id"]: {target["id"]: {
        "speedup": round(base["latency_us"] / target["latency_us"], 3),
        "speedup_label": f'{base["latency_us"] / target["latency_us"]:.2f}×',
        "reduction": f'{(base["latency_us"] - target["latency_us"]) / base["latency_us"] * 100:+.1f}%',
        "saved_label": f'{base["latency_us"] - target["latency_us"]:+.1f} μs',
        "speed_width": round(min(row["latency_us"] for row in rows) / target["latency_us"] * 100, 3),
        "traffic_label": f'{base["traffic_mib"] - target["traffic_mib"]:+g} MiB',
    } for target in rows} for base in rows}


def trends(specs, values):
    maximum = max(max(series) for series in values)
    colors = ["muted", "vector", "store", "memory", "compute"]
    return {"ticks": [f"{maximum:g}", f"{maximum / 2:g}", "0"],
            "labels": ["512", "1024", "2048", "4096"], "series": [
        {"id": spec[0], "name": spec[1], "kind": colors[i],
         "points": [{"x": 40 + j * 160, "y": round(165 - value / maximum * 140, 3),
                     "value": f"{value:g} μs"} for j, value in enumerate(series)],
         "path": " ".join(f'{40 + j * 160},{165 - value / maximum * 140:.3f}' for j, value in enumerate(series))}
        for i, (spec, series) in enumerate(zip(specs, values))]}


def performance_samples(scope, hardware_id):
    # Hardware samples are authored independently; they do not predict relative SKU speed.
    return {
        "ascend-910b1": {
            "matmul": [[4.8, 12.8, 42.6, 126.4], [3.8, 9.6, 32.8, 104.8],
                       [3.2, 7.4, 25.2, 88.6], [3.6, 8.6, 29.4, 97.2], [3.7, 8.1, 24.8, 76.8]],
            "fused": [[8.4, 22.4, 64.8, 182.4], [6.8, 17.6, 52.4, 151.2],
                      [4.2, 9.8, 34.2, 109.6], [4.8, 8.4, 28.6, 92.8]],
            "attention": [[68.4, 126.8, 412.0, 1216.0], [39.2, 72.8, 230.4, 672.0],
                          [33.6, 58.4, 178.6, 508.8], [35.4, 62.4, 164.8, 462.4]],
        },
        "ascend-910b4": {
            "matmul": [[4.4, 11.4, 30.2, 112.6], [3.4, 8.7, 26.6, 92.4],
                       [2.9, 6.8, 20.2, 68.2], [3.1, 7.9, 25.0, 86.8], [3.5, 7.2, 21.6, 70.4]],
            "fused": [[7.6, 19.8, 56.2, 161.6], [6.2, 15.4, 46.8, 134.4],
                      [3.8, 8.6, 26.4, 88.2], [4.3, 7.6, 25.8, 84.6]],
            "attention": [[59.2, 110.4, 350.8, 1028.0], [35.2, 65.6, 201.4, 591.2],
                          [29.8, 52.6, 146.2, 414.8], [31.6, 55.8, 152.8, 428.0]],
        },
    }[hardware_id][scope]


def mega_case(family, scope, small, hardware):
    specs = implementation_specs(scope)
    trend_values = performance_samples(scope, hardware["id"])
    values = [series[1 if small else 3] for series in trend_values]
    members = {row["id"]: row for row in family["members"]}
    rows = []
    for (key, name, kind, tag, launches, traffic, chain), latency in zip(specs, values):
        member = members[f"{scope}/{key}"]
        rows.append(dict(id=key, member_id=member["id"], name=name, kind=kind,
                         kind_label=member["kind_label"], tag=tag, launches=launches, chain=chain,
                         latency_us=latency, latency=f"{latency:.1f}",
                         traffic_mib=traffic / (16 if small else 1),
                         width=round(latency / max(values) * 100, 3), synthetic=True))
    rows.sort(key=lambda row: row["latency_us"])
    size = "1024" if small else "4096"
    semantic = {"matmul": "A × B · Linear 无 bias", "fused": "GELU(XW + b)",
                "attention": "softmax(QKᵀ / √d) V · 非因果 · 无 dropout"}[scope]
    trend = trends(specs, trend_values)
    trend["axis_label"] = "序列长度 S" if scope == "attention" else "M = N = K"
    return dict(id=f'{scope}-{"small" if small else "large"}/{hardware["id"]}',
                family_id=family["id"], scope_id=scope, size=size, hardware_id=hardware["id"],
                shape=f"1 × 32 × {size} × 128" if scope == "attention" else " × ".join([size] * 3),
                shape_label="B × H × S × D" if scope == "attention" else "M × N × K",
                semantic=semantic,
                synthetic=True, hardware=hardware["name"], dtype="FP16",
                baseline="v1" if scope == "matmul" else "separate", winner=rows[0]["id"],
                candidates=rows, comparisons=comparisons(rows), trend=trend)


def build_optimization_demo():
    families = mega_families()
    catalog = diagnostic_catalog()
    return {"schema": "opscope-optimization-demo-v6", "synthetic": True,
            "diagnostic_catalog": catalog, "diagnostics": diagnostic_cases(), "families": families,
            "mega": [mega_case(family, scope["id"], small, hardware) for family in families
                     for scope in family["scopes"] for hardware in catalog["hardware"] for small in (False, True)]}


def write_optimization_demo(root):
    target = root / "frontend/src/data/optimization-demo.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(build_optimization_demo(), ensure_ascii=False, indent=2) + "\n")
