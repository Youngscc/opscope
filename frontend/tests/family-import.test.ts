import {test} from 'node:test'
import assert from 'node:assert/strict'
import {parseFamilyImport,familyTemplate,familyResult} from '../src/data/family-import'
import {findDimensionCase} from '../src/data/optimization'
test('family JSON round-trip retains names and member ownership',()=>{
 const data=familyTemplate();const parsed=parseFamilyImport(JSON.stringify(data))
 assert.equal(parsed.length,5);assert.equal(parsed[1].calculation_type,'bmm');assert.equal(parsed[0].members.length,5)
})
test('invalid catalog and mixed semantics fail before replacing state',()=>{
 assert.throws(()=>parseFamilyImport('{}'),/格式/)
 const data=familyTemplate();data.families[0].members.push(data.families[1].members[0])
 assert.throws(()=>parseFamilyImport(JSON.stringify(data)),/不能混合/)
 data.families[0].members.pop();data.families.push(data.families[0])
 assert.throws(()=>parseFamilyImport(JSON.stringify(data)),/重复/)
})
test('custom family has no borrowed performance and unknown members remain distinct',()=>{
 const parsed=parseFamilyImport(JSON.stringify({schema:'opscope-families-v1',families:[{id:'rms',name:'RMSNorm',members:[{id:'rms/v1',name:'rms_v1',kind:'operator'}]}]}))
 assert.equal(parsed[0].calculation_type,'custom');assert.equal(familyResult(null,parsed[0]),null)
 const family=parseFamilyImport(JSON.stringify(familyTemplate()))[0]
 family.members=family.members.filter(m=>m.id==='matmul/v2')
 const result=familyResult(findDimensionCase('matmul','ascend-910b1',[1,4096,4096,4096]),family)
 assert.ok(result);assert.equal(result.candidates.length,1);assert.equal(result.winner,result.baseline)
 assert.equal(result.candidates[0].member_id,'matmul/v2')
})
