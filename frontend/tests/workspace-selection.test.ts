import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { createRequire } from 'node:module'
import { test } from 'node:test'
import type { ConfigAPI, Configuration as Config, Fields, Payload } from '../src/types'

const Configuration = createRequire(import.meta.url)('../../configuration.js') as ConfigAPI
const payload = JSON.parse(readFileSync(new URL('../src/data/workspace-demo.json', import.meta.url), 'utf8')) as Payload
const demo = payload.catalog.default_config as Config

test('static Mul selection exports its own inputs and keeps performance missing', () => {
  // A different operator must never inherit MatMul latency, workload or execution.
  const operator = payload.catalog.operators.find((row:Fields) => row.id === 'infer:Mul')
  const config = Configuration.from_operator(operator)
  assert.deepEqual(Configuration.validate(config, operator, payload.catalog.dtypes), [])
  const rows = Configuration.project(config, payload.results, payload.pending_results, demo)
  assert.equal(rows.length, 25)
  for (const row of rows) {
    assert.equal(row.available, false)
    assert.equal(row.latency_us, null)
    assert.equal(row.execution, undefined)
    assert.equal(row.workload.flops, null)
    assert.equal(row.workload.outputs, null)
    assert.deepEqual(row.workload.tensors, config.inputs)
    assert.equal(row.reason, '未预设该配置的示例结果')
  }
  const exported = Configuration.public_export({synthetic:true, configuration:config,
    workload:Configuration.workload(config), results:rows}, payload.catalog)
  assert.equal(exported.synthetic, true)
  assert.equal(exported.configuration.operator, 'Mul')
  assert.deepEqual(exported.configuration.inputs[0].shape, [1, 2048, 4096])
  assert.equal(exported.configuration.inputs[0].dtype, 'bf16')
})

test('static input edits clear samples and loading the exact preset restores original results', () => {
  // Matching includes shape, precision and execution options, rather than the operator name alone.
  const edits: Array<(config:Config)=>void> = [config => config.inputs[0].shape = [1024, 4096],
    config => config.inputs[0].dtype = 'bf16', config => config.options.transpose_a = true]
  for (const edit of edits) {
    const config = Configuration.clone(demo)
    edit(config)
    const rows = Configuration.project(config, payload.results, payload.pending_results, demo)
    assert.equal(rows.filter(row => row.available).length, 0)
    assert.ok(rows.every(row => row.latency_us === null))
  }
  const restored = Configuration.project(Configuration.clone(demo), payload.results, payload.pending_results, demo)
  assert.strictEqual(restored, payload.results)
  assert.equal(restored.filter(row => row.available).length, 25)
  assert.equal(restored.find(row => row.id === 'demo-ascend-profile')?.latency_us, 248)
})
