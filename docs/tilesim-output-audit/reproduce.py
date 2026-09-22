"""Inspect public and DSL outputs for one fixed operator; not accuracy validation."""
import copy
from dataclasses import asdict, fields
import importlib.metadata
import json
from pathlib import Path
import sys
site = Path(importlib.metadata.distribution('msopmodeling').locate_file(''))
sys.path.insert(0, str(site / 'tilesim'))
from api.operator_api.op_latency_predict import op_latency_predict
from api.operator_api.op_latency_predict_engineering import op_latency_predict as engineering
from api.operator_api.models.operator_api_models import OperatorPredictResponse
from core.pipeline.basic_operator import OperatorResult
from ops.engineering_model.cube_op.matmul_l0 import EngMatmulL0


def serial(value):
    if isinstance(value, dict):
        return {str(k): serial(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [serial(v) for v in value]
    return value


request = json.loads(Path('matmul-eng.json').read_text())[0]
request['accelerator'] = str(site / 'tilesim/core/config/arc_config/910B1/910B1.yaml')
request['core_num'] = 24
request['backend_type'] = 'theo'
theo, hints = op_latency_predict(copy.deepcopy(request))
assert 'error' not in theo, theo
request['backend_type'] = 'eng'
eng = engineering(copy.deepcopy(request))
assert 'error' not in eng, eng
request.update(input_dtypes=['FP16', 'FP16'], output_dtypes=['FP32'], aiv_core_num=48)
dsl = EngMatmulL0(EngMatmulL0.op_input_convert(copy.deepcopy(request))).run()
events = dsl.trace['traceEvents']
dsl_fields = asdict(dsl)
dsl_fields['trace'] = {'event_count': len(events), 'event_keys': sorted(events[0]),
                       'lanes': sorted(set(e['tid'] for e in events)),
                       'cores': len(set(e['pid'] for e in events)),
                       'max_end_us': max(e['ts']+e['dur'] for e in events)}
report = {'version': importlib.metadata.version('msopmodeling'),
          'response_fields': [f.name for f in fields(OperatorPredictResponse)],
          'internal_fields': [f.name for f in fields(OperatorResult)],
          'theo': theo, 'theo_hints': hints, 'eng': eng, 'dsl': serial(dsl_fields)}
Path('output-audit.json').write_text(json.dumps(report, indent=2, ensure_ascii=False)+'\n')
print(json.dumps(report, indent=2, ensure_ascii=False))
