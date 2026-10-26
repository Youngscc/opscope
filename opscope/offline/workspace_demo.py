"""Select complete synthetic scenarios for the standalone Vue workspace."""
import copy
import json

from .matrix_data import prepare_matrix
from .presentation_details import complete_static_details, finish_static_sections


def workspace_payload(payload):
    data = copy.deepcopy(payload)
    methods = {item['id'] for item in data['methods']}
    complete = {hw['id'] for hw in data['hardware']
                if {row['method'] for row in data['results']
                    if row['hardware'] == hw['id'] and row['available']} == methods}
    data['hardware'] = [hw for hw in data['hardware'] if hw['id'] in complete]
    data['results'] = [row for row in data['results'] if row['hardware'] in complete]
    data['pending_results'] = [row for row in data['pending_results'] if row['hardware'] in complete]
    for row in data['pending_results']:
        row['reason'] = '未预设该配置的示例结果'
        row['matrix']['note'] = row['reason']
    for row in data['results']:
        complete_static_details(row)
    data['matrix'] = prepare_matrix(data['results'])
    for row in data['results']:
        finish_static_sections(row)
    for pair in data['matrix']['pairs'].values():
        if not pair['issues']:
            pair['text'] = pair['text'].split(' · ')[0]
    data['presentation'] = {'mode': 'static', 'configuration_locked': False}
    return data


def write_workspace_demo(root, payload):
    target = root / 'frontend/src/data/workspace-demo.json'
    target.write_text(json.dumps(workspace_payload(payload), ensure_ascii=False, allow_nan=False))
