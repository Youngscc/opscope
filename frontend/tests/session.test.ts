import test from 'node:test'
import assert from 'node:assert/strict'
import { createRequire } from 'node:module'
import { EvaluationSession } from '../src/stores/evaluation-session.ts'
const Configuration = createRequire(import.meta.url)('../../configuration.js')

test('old completion cannot replace a newly configured run', async () => {
  // Simulate a pending response completing after the user applies another configuration.
  const session = new EvaluationSession(), old = session.begin()
  let release!: (value:string) => void
  let displayed = 'new configuration'
  const response = new Promise<string>(resolve => release=resolve)
  const pending=response.then(value=>{if(session.current(old))displayed=value})
  const latest=session.begin();release('old result');await pending
  assert.equal(old.aborted,true);assert.equal(displayed,'new configuration')
  assert.equal(session.current(latest),true)
  session.cancel();assert.equal(session.current(latest),false)
})

test('shape edits preserve unknowns and enforce contraction dimensions', () => {
  // The online view reuses the offline form contract instead of inventing a new MatMul schema.
  assert.equal(Configuration.parse_shape('128, ?'),null)
  assert.deepEqual(Configuration.parse_shape('128 × 256'),[128,256])
  const config={operator_id:'demo:matmul',inputs:[{name:'A',shape:[128,256],dtype:'bf16'},{name:'B',shape:[128,128],dtype:'bf16'}],options:{}}
  assert.equal(Configuration.validate(config,{configurable:true},['bf16'])[0].field,'shape-1')
})
