"""Typed per-operator runtime values absent from tensor shape metadata."""

PARAMETERS = {
    'infer:TorchSum': [{'name': 'axis', 'label': '归约轴', 'type': 'integer', 'default': 1}],
    'infer:TorchCumsum': [{'name': 'axis', 'label': '累加轴', 'type': 'integer', 'default': -1}],
    'infer:Cumsum': [{'name': 'axis', 'label': '累加轴', 'type': 'integer', 'default': None}],
    'infer:GatherV2': [{'name': 'axis', 'label': '查找轴', 'type': 'integer', 'default': None}],
    'infer:Transpose': [{'name': 'permutation', 'label': '置换顺序', 'type': 'permutation',
                         'default': [0, 2, 1]}],
}


def defaults(identifier):
    return {field['name']: field['default'] for field in PARAMETERS.get(identifier, [])}


def normalize(identifier, value):
    if value is None: value = defaults(identifier)
    expected = PARAMETERS.get(identifier, [])
    if not isinstance(value, dict) or set(value) != {field['name'] for field in expected}:
        raise ValueError('算子属性与模板不符')
    result = {}
    for field in expected:
        name = field['name']; item = value[name]
        if field['type'] == 'integer':
            if type(item) is not int or not -8 <= item <= 7:
                raise ValueError(f'{field["label"]}需要填写 -8 至 7 的整数')
        elif (not isinstance(item, list) or len(item) != 3 or
              any(type(n) is not int for n in item) or sorted(item) != [0, 1, 2]):
            raise ValueError('置换顺序须为 0、1、2 各一次')
        result[name] = item
    if identifier == 'infer:TorchSum' and result['axis'] != 1:
        raise ValueError('该 TorchSum 模板的输出仅对应沿序列轴归约')
    if identifier == 'infer:Transpose' and result['permutation'] != [0, 2, 1]:
        raise ValueError('该 Transpose 模板的输出仅对应 [0,2,1]')
    if identifier == 'infer:GatherV2' and result['axis'] != 0:
        raise ValueError('该 GatherV2 模板的输出仅对应 axis=0')
    if identifier == 'infer:Cumsum' and result['axis'] != 2:
        raise ValueError('该 Cumsum 资产的工作量公式仅对应最后一轴')
    if identifier == 'infer:TorchCumsum' and result['axis'] != -1:
        raise ValueError('当前 TileSim Cumsum 模型只按最后一轴建模')
    return result
