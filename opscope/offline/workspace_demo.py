"""Select complete synthetic scenarios for the standalone Vue workspace."""
import copy
import json

from .matrix_data import prepare_matrix


def workspace_payload(payload):
    data = copy.deepcopy(payload)
    methods = {item['id'] for item in data['methods']}
    complete = {hw['id'] for hw in data['hardware']
                if {row['method'] for row in data['results']
                    if row['hardware'] == hw['id'] and row['available']} == methods}
    data['hardware'] = [hw for hw in data['hardware'] if hw['id'] in complete]
    data['results'] = [row for row in data['results'] if row['hardware'] in complete]
    data['pending_results'] = []
    config = data['catalog']['default_config']
    catalog = data['catalog']
    catalog['operators'] = [op for op in catalog['operators'] if op['id'] == config['operator_id']]
    catalog['groups'] = [group for group in catalog['groups'] if config['operator_id'] in group['variants']]
    data['matrix'] = prepare_matrix(data['results'])
    data['presentation'] = {'mode': 'static', 'configuration_locked': True}
    return data


def write_workspace_demo(root, payload):
    target = root / 'frontend/src/data/workspace-demo.json'
    target.write_text(json.dumps(workspace_payload(payload), ensure_ascii=False, allow_nan=False))
