"""Declarative output references for the configuration form, not performance math."""


def output_preview(op):
    from opscope.evaluation.tilesim_contract import OPERATOR_KINDS
    kind = OPERATOR_KINDS.get(op['id'])
    rank = len(op['inputs'][0]['shape']) if op['inputs'] else 0
    refs = lambda i, axes: [{'input': i, 'axis': axis} for axis in axes]
    if kind == 'matmul':
        shape = refs(0, [0]) + refs(1, [1])
        if op['id'] == 'demo:matmul':
            shape[0].update(option='transpose_a', alternate=1)
            shape[1].update(option='transpose_b', alternate=0)
    elif kind == 'linear':
        shape = refs(0, range(rank - 1)) + refs(1, [0])
    elif kind == 'bmm':
        shape = refs(0, [0, 1]) + refs(1, [2])
    elif kind in {'swish', 'gelu', 'softmax', 'sigmoid', 'cumsum', 'cast'}:
        shape = refs(0, range(rank))
    elif kind in {'mul', 'add'}:
        # The preview is valid only for identical shapes; broadcasting is left pending.
        return [{'name': 'output', 'shape_refs': refs(0, range(rank)),
                 'dtype_input': 0, 'same_shape': True}]
    else:
        return []
    return [{'name': 'C' if kind in {'matmul', 'bmm'} else 'output',
             'shape_refs': shape, 'dtype_input': 0,
             'dtype': 'fp32' if kind == 'cast' else None}]
