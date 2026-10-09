import test from 'node:test'
import assert from 'node:assert/strict'
import { findDiagnosis, parseDimensions } from '../src/data/optimization'

test('diagnosis selection preserves both operator and hardware identities', () => {
  // The same operator on another SKU has its own conclusion and full result bundle.
  const b1 = findDiagnosis('matmul', 'ascend-910b1', [4096,4096,4096])!
  const b4 = findDiagnosis('matmul', 'ascend-910b4', [4096,4096,4096])!
  assert.equal(b1.latency_us, 126.4)
  assert.equal(b4.latency_us, 112.6)
  assert.equal(b4.bound, '计算受限')
  assert.equal(b4.actions[0].title, '优化矩阵分块')
  assert.equal(findDiagnosis('attention', 'ascend-910b4', [1,32,2048,128])?.focus_range, '56–88 μs')
})

test('missing diagnosis never falls back to another operator or hardware', () => {
  // Unknown combinations remain empty instead of borrowing a plausible-looking preset.
  assert.equal(findDiagnosis('matmul', 'unknown-hardware', [4096,4096,4096]), null)
  assert.equal(findDiagnosis('unknown-operator', 'ascend-910b1', [4096,4096,4096]), null)
  assert.equal(findDiagnosis('attention', 'Ascend 910B4', [1,32,2048,128]), null)
})

test('size matching uses every dimension without interpolation or fallback', () => {
  // Matching only sequence length, matrix volume, or the first axis would borrow the wrong result.
  assert.equal(findDiagnosis('matmul', 'ascend-910b1', [1024,1024,1024])?.latency_us, 12.8)
  assert.equal(findDiagnosis('matmul', 'ascend-910b1', [2048,2048,2048])?.latency_us, 34.8)
  assert.equal(findDiagnosis('matmul', 'ascend-910b1', [2048,1024,2048]), null)
  assert.equal(findDiagnosis('matmul', 'ascend-910b1', [4096,4096]), null)
  assert.equal(findDiagnosis('attention', 'ascend-910b4', [2,16,2048,128]), null)
  assert.equal(findDiagnosis('attention', 'ascend-910b4', [1,32,512,128])?.latency_us, 63.2)
})

test('custom dimensions accept positive integers and reject invalid values', () => {
  assert.deepEqual(parseDimensions([' 2048 ', '1024', '4096']), [2048,1024,4096])
  for (const value of ['', '0', '-1', '1.5', '1e3', '9007199254740992']) {
    assert.equal(parseDimensions(['1024', value, '1024']), null)
  }
  assert.equal(parseDimensions([]), null)
})
