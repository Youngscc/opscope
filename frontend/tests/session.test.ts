import test from 'node:test'
import assert from 'node:assert/strict'
import { createRequire } from 'node:module'
import { EvaluationSession } from '../src/stores/evaluation-session.ts'
import { initialHardwareIds } from '../src/stores/hardware-selection.ts'
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

test('TileSim startup selects catalog IDs instead of backend model names', () => {
  const hardware = [
    {id:'h200', name:'NVIDIA H200', group:'demo'},
    {id:'modeling:H200_Server', name:'H200_Server', group:'modeling'},
    {id:'tilesim:910B1', name:'Ascend 910B1', group:'tilesim'},
    {id:'tilesim:910B4', name:'Ascend 910B4', group:'tilesim'},
  ]
  assert.deepEqual(initialHardwareIds(hardware, true), ['h200','tilesim:910B1','tilesim:910B4'])
  assert.deepEqual(initialHardwareIds(hardware, false), ['h200'])
})

test('shared mode selects upstream asset identities without local hardware presets', () => {
  // Unknown upstream IDs are valid even when TileSim is unavailable.
  const remote = [{id:'asset:42:train',group:'remote'}, {id:'asset:57:infer',group:'remote'}]
  assert.deepEqual(initialHardwareIds(remote, false), ['asset:42:train','asset:57:infer'])
})

test('shared symbolic parameters use server bounds and list defaults', () => {
  // Dimension controls may exceed legacy axis bounds; unknowns still block submission.
  const op={id:'asset:1',name:'Shared',key:'Shared',domain:'operator',configurable:true,
    inputs:[{name:'x',shape:[128,128],dtype:'bf16'}],source:{sha256:'v1'},
    parameters:[{name:'S',type:'integer',default:2048,minimum:1,maximum:1048576,label:'S'},
      {name:'sizes',type:'integer_list',default:[128,256],minimum:1,maximum:1048576,label:'sizes'}]}
  const config=Configuration.from_operator(op)
  assert.deepEqual(Configuration.validate(config,op,['bf16']),[])
  config.attributes.S=0
  assert.equal(Configuration.validate(config,op,['bf16'])[0].field,'attribute-S')
  config.attributes.S=2048;config.attributes.sizes=[128,0]
  assert.equal(Configuration.validate(config,op,['bf16'])[0].field,'attribute-sizes')
})
