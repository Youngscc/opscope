import { ref } from 'vue'
import { workspaceFamilies, type MegaCase } from './optimization'
export type ImportedFamily = typeof workspaceFamilies[number] & {source_family_id?:string}
export const familyCatalog=ref<ImportedFamily[]>(structuredClone(workspaceFamilies))
const kinds:Record<string,string>={operator:'算子',fusion:'融合算子',sequence:'算子组合'}
function text(value:unknown, field:string):string {
  if(typeof value!=='string' || !value.trim() || value.length>120) throw new Error(`${field} 需要填写 1–120 字符的文本`)
  return value.trim()
}
export function parseFamilyImport(source:string):ImportedFamily[] {
  const data=JSON.parse(source)
  if(data?.schema!=='opscope-families-v1' || !Array.isArray(data.families) || !data.families.length || data.families.length>100)
    throw new Error('需要 opscope-families-v1 格式，包含 1–100 个算子族')
  const ids=new Set<string>()
  return data.families.map((item:any)=>{
    const id=text(item?.id,'族 ID'), name=text(item?.name,'族名称')
    if(ids.has(id)) throw new Error(`族 ID 重复：${id}`)
    ids.add(id)
    const sourceFamily=item.source_family_id==null?undefined:workspaceFamilies.find(f=>f.id===item.source_family_id)
    if(item.source_family_id!=null && !sourceFamily) throw new Error(`未知结果目录：${item.source_family_id}`)
    if(!Array.isArray(item.members) || !item.members.length || item.members.length>100) throw new Error(`${name} 需要 1–100 个成员`)
    const memberIds=new Set<string>()
    const members=item.members.map((m:any)=>{
      const mid=text(m?.id,'成员 ID'), mname=text(m?.name,'成员名称')
      if(memberIds.has(mid)) throw new Error(`成员 ID 重复：${mid}`)
      memberIds.add(mid)
      if(!Object.hasOwn(kinds,m.kind)) throw new Error(`${mname} 的 kind 应为 operator、fusion 或 sequence`)
      const owner=workspaceFamilies.find(f=>f.members.some(v=>v.id===mid))
      if(owner && owner.id!==sourceFamily?.id) throw new Error(`${mname} 属于 ${owner.name}，请使用对应 source_family_id，不能混合计算语义`)
      return {id:mid,name:mname,kind:m.kind,kind_label:kinds[m.kind]!,scope_id:sourceFamily?.scopes[0].id ?? id}
    })
    return {id,name,definition:'manual',synthetic:true,source_family_id:sourceFamily?.id,
      calculation_type:sourceFamily?.calculation_type ?? 'custom',default_size:sourceFamily?.default_size ?? '',
      scopes:sourceFamily?structuredClone(sourceFamily.scopes):[{id,name,member_count:members.length,sizes:[]}],member_count:members.length,members}
  })
}
export function familyTemplate() {
  return {schema:'opscope-families-v1',families:workspaceFamilies.map(f=>({id:f.id,name:f.name,source_family_id:f.id,
    members:f.members.map(({id,name,kind})=>({id,name,kind}))}))}
}
export function familyResult(source:MegaCase|null, family:ImportedFamily):MegaCase|null {
  if(!source) return null
  const candidates=source.candidates.filter(c=>family.members.some(m=>m.id===c.member_id)).map(c=>{
    const member=family.members.find(m=>m.id===c.member_id)!
    return {...c,name:member.name,kind:member.kind,kind_label:member.kind_label}
  })
  if(!candidates.length) return null
  // Keep Python-owned ordering, pair geometry and values. Only select known members.
  return {...source,family_id:family.id,candidates,trend:{...source.trend,series:source.trend.series.map(row=>({...row,name:candidates.find(c=>c.id===row.id)?.name ?? row.name}))},winner:candidates[0].id,
    baseline:candidates.some(c=>c.id===source.baseline)?source.baseline:candidates[candidates.length-1].id}
}
