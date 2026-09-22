'use strict';
const assert = require('node:assert/strict');
const {test} = require('node:test');
const fs = require('node:fs');
const Config = require('../configuration.js');
const payload = JSON.parse(fs.readFileSync(0, 'utf8'));
const catalog = payload.catalog;
const demo = catalog.default_config;
const op = id => catalog.operators.find(item => item.id === id);
const validate = config => Config.validate(config, op(config.operator_id), catalog.dtypes);

test('public JSON uses neutral identities, keeps synthetic and drops repository provenance', () => {
  const config = Config.from_operator(op('infer:RmsNorm'));
  config.inputs.forEach(tensor => tensor.shape = tensor.shape.map(n => n ?? 128));
  const rows = Config.project(config, payload.results, payload.pending_results, demo);
  const exported = Config.public_export({synthetic: true, configuration: config,
    workload: Config.workload(config), results: rows, catalog_revision: catalog.revision}, catalog);
  assert.equal(exported.configuration.operator, 'RMSNorm');
  assert.equal(exported.configuration.operator_id, 'rmsnorm');
  assert.equal(exported.configuration.template_id, 'rmsnorm:template-2');
  assert.equal(exported.configuration.domain, undefined);
  assert.equal(exported.configuration.source, undefined);
  assert.equal(exported.synthetic, true);
  assert.equal(exported.results.find(row => row.hardware === 'hardware:H100_Server').latency_us, null);
  assert.doesNotMatch(JSON.stringify(exported), /modeling:|backend\/|"domain"|infer:RmsNorm|catalog_revision/);
  assert.equal(config.domain, 'infer');
  assert.equal(rows.find(row => row.hardware === 'modeling:H100_Server').hardware_snapshot.selected_domain, 'infer');
});

test('shape syntax accepts supported separators, rejects unsafe or incomplete values', () => {
  for (const value of ['[2, 32, 512, 128]', '2 × 32 × 512 × 128', '2 32 512 128']) {
    assert.deepEqual(Config.parse_shape(value), [2, 32, 512, 128]);
  }
  for (const value of ['', '[]', '2, ?, 128', '2,-1', '2,0', '1e3,2', '3.5,2', '1,,2', '[2,3', '9007199254740992']) assert.equal(Config.parse_shape(value), null);
});

test('modified configuration cannot inherit latency, FLOPs, trace or inferred output', () => {
  const config = Config.clone(demo);
  config.inputs[0].shape = [1024, 4096];
  assert.equal(validate(config).length, 0);
  const rows = Config.project(config, payload.results, payload.pending_results, demo);
  assert.equal(rows.length, 95);
  for (const row of rows) {
    assert.equal(row.available, false);
    assert.equal(row.latency_us, null);
    assert.equal(row.workload.flops, null);
    assert.equal(row.workload.outputs, null);
    assert.equal(row.task.task_id, null);
    assert.equal(row.execution, undefined);
    assert.deepEqual(row.workload.tensors[0].shape, [1024, 4096]);
  }
  assert.equal(payload.results.filter(row => row.available).length, 25);
  assert.strictEqual(Config.project(Config.clone(demo), payload.results, payload.pending_results, demo), payload.results);
});

test('every demo input and advanced option contributes to example identity', () => {
  for (const edit of [c => c.inputs[0].dtype = 'bf16', c => c.options.transpose_a = true,
    c => c.options.transpose_b = true, c => c.options.layout = 'column-major',
    c => c.options.accumulator_dtype = 'fp16', c => c.domain = 'train']) {
    const config = Config.clone(demo);
    edit(config);
    assert.equal(Config.matches_demo(config, demo), false);
  }
});

test('matrix and Attention form contracts report incompatible inputs', () => {
  const matmul = Config.clone(demo);
  matmul.inputs[1].shape = [512, 256];
  assert.match(validate(matmul)[0].message, /K 不一致/);
  const attention = Config.from_operator(op('train:flash_attention'));
  assert.equal(validate(attention).length, 0);
  attention.inputs[1].shape[3] = 64;
  assert.match(validate(attention)[0].message, /head_dim/);
  const bmm = Config.from_operator(op('train:bmm'));
  bmm.inputs[1].shape[0] = 16;
  assert.match(validate(bmm)[0].message, /batch/);
  const batched = Config.from_operator(op('train:matmul'));
  batched.inputs[0].shape = [8, 32, 64];
  batched.inputs[1].shape = [8, 64, 16];
  assert.equal(validate(batched).length, 0);
});

test('all training templates are immediately configurable with their original defaults', () => {
  for (const operator of catalog.operators.filter(item => item.domain === 'train')) {
    assert.deepEqual(validate(Config.from_operator(operator)), [], operator.id);
  }
});

test('mixed dtype, unknown dimensions and excluded operators retain source semantics', () => {
  const embedding = Config.from_operator(op('train:embedding'));
  assert.equal(validate(embedding).length, 0);
  embedding.inputs[1].dtype = 'fp16';
  assert.match(validate(embedding)[0].message, /索引/);
  const flash = Config.from_operator(op('infer:FlashAttentionScore'));
  assert.equal(validate(flash).length, 3);
  flash.inputs.forEach(t => t.shape[3] = 128);
  assert.equal(validate(flash).length, 0);
  const rows = Config.project(flash, payload.results, payload.pending_results, demo);
  const h100 = rows.find(r => r.hardware === 'modeling:H100_Server');
  assert.equal(h100.hardware_snapshot.selected_domain, 'infer');
  assert.equal(h100.hardware_snapshot.catalog_profile.path, 'backend/hardware/infer/NVIDIA-H100-Server.yaml');
  assert.equal(validate(Config.from_operator(op('infer:AllReduce'))).length, 1);
});
