import test from 'node:test'
import assert from 'node:assert/strict'
import { findMegaCase } from '../src/data/optimization'

const selection = {family:'matmul-family', scope:'matmul', size:'4096', hardware:'ascend-910b1'}

test('MegaKernel hardware selection changes the ranking and trend together', () => {
  // Same task and size can have a different winner on another authored hardware sample.
  const b1 = findMegaCase(selection)!
  const b4 = findMegaCase({...selection, hardware:'ascend-910b4'})!
  assert.equal(b1.winner, 'mega')
  assert.equal(b1.candidates[0].latency_us, 76.8)
  assert.equal(b4.winner, 'v3')
  assert.equal(b4.candidates[0].latency_us, 68.2)
  assert.equal(b4.hardware, 'Ascend 910B4')
  assert.notDeepEqual(b1.trend, b4.trend)
  assert.equal(b4.comparisons.v3.v3.speedup, 1)
  assert.equal(findMegaCase({...selection, scope:'fused', hardware:'ascend-910b4'})?.comparisons.separate.mega.speedup_label, '1.91×')
})

test('MegaKernel requires exact family, scope, size and hardware identity', () => {
  // Missing selections must stay empty instead of falling back across scope or hardware.
  for (const change of [{hardware:'unknown'}, {hardware:'Ascend 910B4'}, {family:'attention-family'},
    {scope:'attention'}, {size:'2048'}]) {
    assert.equal(findMegaCase({...selection, ...change}), null)
  }
})
