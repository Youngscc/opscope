import fixture from './optimization-demo.json'
export type Diagnosis = typeof fixture.diagnostics[number]
export type DiagnosticOperator = typeof fixture.diagnostic_catalog.operators[number]
export type MegaFamily = typeof fixture.families[number]
export type Pair = {speedup:number; speedup_label:string; reduction:string; saved_label:string; speed_width:number; traffic_label:string}
export type MegaCase = Omit<typeof fixture.mega[number], 'comparisons'> & {comparisons:Record<string,Record<string,Pair>>}
export type MegaSelection = {family:string; scope:string; size:string; hardware:string}
export type Candidate = MegaCase['candidates'][number]
export const diagnostics:Diagnosis[] = fixture.diagnostics
export const diagnosticOperators = fixture.diagnostic_catalog.operators
export const optimizationHardware = fixture.diagnostic_catalog.hardware
export const diagnosticHardware = optimizationHardware
export const megaFamilies:MegaFamily[] = fixture.families
// The generated JSON has different keys per task; all pairs are validated at build time.
export const megaCases = fixture.mega as unknown as MegaCase[]
export function findMegaCase(selection:MegaSelection):MegaCase | null {
  return megaCases.find(row=>row.family_id===selection.family && row.scope_id===selection.scope &&
    row.size===selection.size && row.hardware_id===selection.hardware) ?? null
}
export function findDiagnosis(operatorId:string, hardwareId:string, dimensions:readonly number[]):Diagnosis | null {
  return diagnostics.find(row=>row.operator_id===operatorId && row.hardware_id===hardwareId &&
    row.dimensions.length===dimensions.length && row.dimensions.every((value,index)=>value===dimensions[index])) ?? null
}
export function parseDimensions(values:string[]):number[] | null {
  const dimensions = values.map(value=>Number(value.trim()))
  return values.length && values.every((value,index)=>/^\d+$/.test(value.trim()) && Number.isSafeInteger(dimensions[index]) && dimensions[index]>0) ? dimensions : null
}
export function exportDemo(kind:string, selection:unknown, data:unknown) {
  const payload = {schema:fixture.schema, synthetic:true, view:kind, selection, data}
  const url = URL.createObjectURL(new Blob([JSON.stringify(payload,null,2)], {type:'application/json'}))
  const link = document.createElement('a')
  link.href = url; link.download = `opscope-${kind}-demo.json`; link.click()
  setTimeout(()=>URL.revokeObjectURL(url), 1000)
}
