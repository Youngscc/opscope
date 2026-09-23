'use strict';
// Form contracts only. Performance math and output inference belong to the backend.
const Configuration = (() => {
  const clone = value => JSON.parse(JSON.stringify(value));

  function from_operator(op) {
    return {operator_id: op.id, operator: op.display_name || op.name, key: op.key, domain: op.domain,
      inputs: op.inputs.map(({name, role, shape, dtype}) => ({name, role, shape: [...shape], dtype})),
      options: {}, attributes: Object.fromEntries((op.parameters || []).map(field => [field.name, clone(field.default)])),
      source: clone(op.source), boundary: null};
  }

  function parse_shape(value) {
    let text = value.trim();
    if (text.startsWith('[') && text.endsWith(']')) text = text.slice(1, -1).trim();
    if (!/^\d+(?:\s*(?:[,x×]|\s)\s*\d+)*$/i.test(text)) return null;
    const shape = text.split(/[,x×\s]+/i).map(Number);
    return shape.length && shape.every(n => Number.isSafeInteger(n) && n > 0) ? shape : null;
  }

  function validate(config, op, dtypes) {
    const errors = [];
    if (!op?.configurable) return [{field: 'config-error', message: op?.reason || '算子不可用'}];
    config.inputs.forEach((tensor, index) => {
      if (!Array.isArray(tensor.shape) || !tensor.shape.length || !tensor.shape.every(n => Number.isSafeInteger(n) && n > 0)) {
        errors.push({field: `shape-${index}`, message: `${tensor.name}：请填写完整形状，每一维为正整数。`});
      }
      if (!dtypes.includes(tensor.dtype)) errors.push({field: `dtype-${index}`, message: `${tensor.name}：请选择有效 dtype。`});
    });
    if (!errors.length) errors.push(...validate_contract(config));
    for (const field of op.parameters || []) {
      const item = config.attributes?.[field.name];
      if (field.type === 'integer' && (!Number.isInteger(item) || item < -8 || item > 7))
        errors.push({field: `attribute-${field.name}`, message: `${field.label}需要填写 -8 至 7 的整数。`});
      if (field.type === 'permutation' && (!Array.isArray(item) || item.length !== 3 || item.slice().sort().join(',') !== '0,1,2'))
        errors.push({field: `attribute-${field.name}`, message: '置换顺序须为 0、1、2 各一次。'});
    }
    if (config.operator_id === 'infer:TorchSum' && config.attributes?.axis !== 1) errors.push({field: 'attribute-axis', message: '当前模板只支持沿序列轴 1 归约。'});
    if (config.operator_id === 'infer:GatherV2' && config.attributes?.axis !== 0) errors.push({field: 'attribute-axis', message: '当前模板只支持沿查找轴 0 取值。'});
    if (config.operator_id === 'infer:Cumsum' && config.attributes?.axis !== 2) errors.push({field: 'attribute-axis', message: '当前 Cumsum 资产的工作量公式只支持最后一轴 2。'});
    if (config.operator_id === 'infer:TorchCumsum' && config.attributes?.axis !== -1) errors.push({field: 'attribute-axis', message: '当前模型只支持沿最后一轴累加。'});
    if (config.operator_id === 'infer:Transpose' && config.attributes?.permutation?.join(',') !== '0,2,1') errors.push({field: 'attribute-permutation', message: '当前模板只支持置换顺序 0,2,1。'});
    return errors;
  }

  function validate_contract(config) {
    const inputs = config.inputs;
    const [a, b, v] = inputs.map(t => t.shape);
    const id = config.operator_id;
    const fail = (index, message) => [{field: `shape-${index}`, message}];
    if (['demo:matmul', 'train:matmul', 'train:bmm', 'train:linear'].includes(id)) {
      if (inputs.length !== 2) return fail(0, '当前模板需要两个输入张量。');
      if (id === 'train:linear' && (!a.length || b.length !== 2)) return fail(1, 'Linear 的 weight 需要二维形状。');
      if (id !== 'train:linear' && (a.length < 2 || b.length < 2)) return fail(0, '当前矩阵模板至少需要二维输入。');
      if (id === 'demo:matmul' && (a.length !== 2 || b.length !== 2)) return fail(0, '示例使用二维 MatMul；批量输入请选择“矩阵相乘”输入形式。');
      if (id === 'train:bmm' && (a.length !== 3 || b.length !== 3)) return fail(0, 'BMM 需要两个三维张量。');
      const ka = config.options.transpose_a ? a[a.length - 2] : a[a.length - 1];
      const kb = id === 'train:linear' || config.options.transpose_b ? b[b.length - 1] : b[b.length - 2];
      if (ka !== kb) return fail(1, `收缩维 K 不一致：${ka} 与 ${kb}。`);
      if (id === 'train:bmm' && a[0] !== b[0]) return fail(1, 'BMM 的 batch 维必须一致。');
      if (inputs[0].dtype !== inputs[1].dtype) return [{field: 'dtype-1', message: '当前矩阵模板的两个输入 dtype 必须一致。'}];
    }
    if (['train:flash_attention', 'infer:FlashAttentionScore'].includes(id)) {
      if (inputs.length !== 3 || inputs.some(t => t.shape.length !== 4)) return fail(0, '当前 Attention 模板采用 BNSD 四维输入。');
      if (a[0] !== b[0] || b[0] !== v[0] || a[1] !== b[1] || b[1] !== v[1] || a[3] !== b[3] || b[2] !== v[2]) return fail(1, 'BNSD 的 batch、头数、Q/K head_dim 和 K/V 序列长度需要匹配。');
      if (inputs.some(t => t.dtype !== inputs[0].dtype)) return [{field: 'dtype-1', message: 'Q、K、V 的 dtype 必须一致。'}];
    }
    if (id === 'train:embedding' && !['int32', 'int64'].includes(inputs[1].dtype)) return [{field: 'dtype-1', message: 'Embedding 索引需要 int32 或 int64。'}];
    return [];
  }

  function matches_demo(config, demo) {
    return ['operator_id', 'domain', 'inputs', 'options', 'attributes', 'boundary'].every(key => JSON.stringify(config[key]) === JSON.stringify(demo[key]));
  }

  function workload(config) {
    return {id: null, operator: config.operator, operator_id: config.operator_id,
      domain: config.domain, tensors: clone(config.inputs), options: clone(config.options),
      attributes: clone(config.attributes || {}),
      boundary: config.boundary, outputs: null, flops: null, logical_bytes: null,
      source: clone(config.source), status: 'configured_not_run', synthetic: true};
  }

  function project(config, baseline, templates, demo) {
    if (matches_demo(config, demo)) return baseline;
    return templates.map(template => ({...clone(template), workload: workload(config),
      hardware_snapshot: {...clone(template.hardware_snapshot),
        selected_domain: config.domain, catalog_profile: template.hardware_snapshot.catalog_profiles[config.domain] || null}}));
  }

  function public_export(payload, catalog) {
    const hidden = new Set(['domain', 'catalog_revision', 'catalog_profiles', 'catalog_profile', 'selected_domain']);
    function clean(value) {
      if (Array.isArray(value)) return value.map(clean);
      if (value === null || typeof value !== 'object') return typeof value === 'string' ? value.replace(/modeling:/g, 'hardware:') : value;
      const result = {};
      for (const [key, item] of Object.entries(value)) {
        if (hidden.has(key) || (key === 'source' && item && typeof item === 'object') || (key === 'key' && value.operator_id)) continue;
        result[key] = clean(item);
      }
      const op = catalog.operators.find(item => item.id === value.operator_id);
      if (op) {
        result.operator_id = op.group_id;
        result.operator = op.display_name;
        result.template_id = op.public_id;
        result.input_form = op.template_label;
      }
      return result;
    }
    return clean(payload);
  }

  return {clone, from_operator, parse_shape, validate, matches_demo, workload, project, public_export};
})();
if (typeof module !== 'undefined' && module.exports) module.exports = Configuration;
