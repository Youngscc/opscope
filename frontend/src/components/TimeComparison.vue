<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { api_base, request } from '../api/client'
import type { Fact, Payload, Result, Section } from '../types'

interface Run { id:string; created_at:string; completed_at:string|null; operator:string; success_count:number; total:number }
interface Side { available:boolean; status:string; latency_us:number|null; latency:string; reason:string|null }
interface Pair { hardware:string; method:string; name:string; left:Side|null; right:Side|null;
  issues:string[]; delta_percent:number|null; delta_label:string; bars:number[]|null }
interface Comparison { rows:Pair[]; scale_us:number; summary:Record<string,number>; notice:string }
const props = defineProps<{refresh:number}>()
const runs=ref<Run[]>([]), left=ref(''), right=ref(''), result=ref<Comparison>()
const selected=ref(''), detail=ref<[Result|null,Result|null]>([null,null])
const detailLoading=ref(false), message=ref(''), serial=ref(0)
let cachedIds='', cachedPayloads:[Payload,Payload]|null=null
const comparable=computed(()=>result.value?.rows.filter(row=>!row.issues.length) || [])
const excluded=computed(()=>result.value?.rows.filter(row=>row.issues.length) || [])
const current=computed(()=>result.value?.rows.find(row=>key(row)===selected.value))
const tabs=computed(()=>[...new Set(detail.value.flatMap(row=>Object.keys(row?.sections||{})))])
const tabNames:Record<string,string>={overview:'结果概览',cost:'计算与访存',execution:'执行过程',context:'输入与硬件',source:'依据与数据'}
const reportUrl=computed(()=>`${api_base}/evaluations/compare/report?${new URLSearchParams({left:left.value,right:right.value})}`)
function singleUrl(job:string,row:Pair){return `${api_base}/evaluations/${job}/report?${new URLSearchParams({hardware:row.hardware,method:row.method})}`}
function key(row:Pair){return row.hardware+'|'+row.method}
function time(value:string|null){return value?new Date(value).toLocaleString('zh-CN',{hour12:false}):'时间未知'}
function runLabel(run:Run){return `${time(run.completed_at||run.created_at)} · ${run.operator} · ${run.success_count}/${run.total}`}
function facts(a:Fact[]=[],b:Fact[]=[]){return [...new Set([...a,...b].map(item=>item.label))].map(label=>({
  label, a:a.find(item=>item.label===label)?.value ?? '—', b:b.find(item=>item.label===label)?.value ?? '—'}))}
function section(row:Result|null,tab:string,id:string):Section|undefined{return row?.sections?.[tab]?.find(item=>item.key===id)}
function groups(tab:string){return [...new Set(detail.value.flatMap(row=>(row?.sections?.[tab]||[]).map(item=>item.key)))]}
function title(tab:string,id:string){return section(detail.value[0],tab,id)?.title||section(detail.value[1],tab,id)?.title||id}
async function loadHistory(){
  try {
    runs.value=await request<Run[]>('/evaluations/history')
    if(!runs.value.some(run=>run.id===left.value))left.value=runs.value[1]?.id||runs.value[0]?.id||''
    if(!runs.value.some(run=>run.id===right.value)||left.value===right.value)right.value=runs.value[0]?.id===left.value?(runs.value[1]?.id||''):(runs.value[0]?.id||'')
    await compare()
  }catch(error){message.value=String(error)}
}
async function compare(){
  const token=++serial.value
  result.value=undefined;selected.value='';detail.value=[null,null]
  if(!left.value||!right.value||left.value===right.value)return
  message.value='正在读取两次评估…'
  try {
    const params=new URLSearchParams({left:left.value,right:right.value})
    const data=await request<Comparison>('/evaluations/compare?'+params)
    if(token!==serial.value)return
    result.value=data;message.value=''
    if(data.rows.length)await choose(data.rows.find(row=>!row.issues.length)||data.rows[0]!)
  }catch(error){if(token===serial.value)message.value=String(error)}
}
async function choose(row:Pair){
  const token=serial.value;selected.value=key(row);detail.value=[null,null];detailLoading.value=true
  try {
    const ids=left.value+'|'+right.value
    if(cachedIds!==ids||!cachedPayloads){
      const jobs=await Promise.all([left.value,right.value].map(id=>request<{payload:Payload}>(`/evaluations/${id}`)))
      if(token!==serial.value)return
      cachedIds=ids;cachedPayloads=[jobs[0]!.payload,jobs[1]!.payload]
    }
    if(token!==serial.value||selected.value!==key(row))return
    detail.value=cachedPayloads.map(payload=>payload.results.find(item=>item.hardware===row.hardware&&item.method===row.method)||null) as [Result|null,Result|null]
  }catch(error){if(token===serial.value)message.value=String(error)}
  finally{if(token===serial.value&&selected.value===key(row))detailLoading.value=false}
}
watch(()=>props.refresh,loadHistory)
onMounted(loadHistory)
</script>
<template>
<section class="time-compare" aria-labelledby="time-compare-heading">
  <div class="time-compare-head"><div><div class="eyebrow">RUN HISTORY / TIME COMPARISON</div><h2 id="time-compare-heading">两次评估对比</h2><p>选择两个完成时间，查看相同硬件与方法的变化和完整结果。</p></div><div class="time-report-actions"><a v-if="result" class="button primary" :href="reportUrl" download>下载对比报告</a><button class="button" @click="loadHistory">刷新记录</button></div></div>
  <div v-if="runs.length<2" class="time-empty">{{runs.length?'再运行一次评估即可比较两个时间。':'暂无评估记录。完成两次评估后可在这里对比。'}}<small>仅保留服务内最近 12 次任务，重启服务后清空。</small></div>
  <template v-else>
    <div class="time-pickers"><label><span class="time-badge a">A</span><span>基准时间</span><select v-model="left" @change="compare"><option v-for="run in runs" :key="run.id" :value="run.id" :disabled="run.id===right">{{runLabel(run)}}</option></select></label><span class="time-arrow" aria-hidden="true">→</span><label><span class="time-badge b">B</span><span>对比时间</span><select v-model="right" @change="compare"><option v-for="run in runs" :key="run.id" :value="run.id" :disabled="run.id===left">{{runLabel(run)}}</option></select></label></div>
    <p v-if="message" class="time-message" role="status">{{message}}</p>
    <template v-if="result">
      <div class="time-summary"><div><strong>{{result.summary.comparable}}</strong><span>同口径组合</span></div><div><strong>{{result.summary.faster}}</strong><span>B 更短</span></div><div><strong>{{result.summary.slower}}</strong><span>B 更长</span></div><div><strong>{{result.summary.equal}}</strong><span>相同</span></div><div><strong>{{result.summary.not_comparable}}</strong><span>仅并排展示</span></div></div>
      <div v-if="comparable.length" class="time-chart"><div class="time-chart-head"><h3>总耗时对照</h3><span><i class="time-key a"></i>A 基准　<i class="time-key b"></i>B 对比</span></div><div class="time-chart-scale"><span>0 μs</span><span>统一刻度 {{result.scale_us}} μs</span></div><button v-for="row in comparable" :key="key(row)" class="time-chart-row" :aria-pressed="selected===key(row)" @click="choose(row)"><span class="time-row-name">{{row.name}}</span><span class="time-bar-stack"><span class="time-bar-line"><i class="time-bar a" :style="{width:row.bars![0]+'%'}"></i><em>{{row.left?.latency}} μs</em></span><span class="time-bar-line"><i class="time-bar b" :style="{width:row.bars![1]+'%'}"></i><em>{{row.right?.latency}} μs</em></span></span><strong class="time-delta" :class="row.delta_percent!==null?(row.delta_percent<0?'improved':row.delta_percent>0?'regressed':''):''">{{row.delta_label}}</strong></button></div>
      <div v-if="excluded.length" class="time-excluded"><h3>其他组合 <small>不计算变化率</small></h3><button v-for="row in excluded" :key="key(row)" :aria-pressed="selected===key(row)" @click="choose(row)"><span>{{row.name}}</span><span>A {{row.left?.latency ?? '—'}} / B {{row.right?.latency ?? '—'}} μs</span><small>{{row.issues.join('；')}}</small></button></div>
      <div v-if="current" class="time-detail"><div class="time-detail-head"><div><div class="eyebrow">SELECTED RESULT</div><h3>{{current.name}}</h3><p>{{current.issues.length?current.issues.join('；'):result.notice}}</p></div><div class="time-detail-actions"><a v-if="current.left" class="button" :href="singleUrl(left,current)" download>A 单项报告</a><a v-if="current.right" class="button" :href="singleUrl(right,current)" download>B 单项报告</a><span class="time-delta" :class="current.delta_percent!==null?(current.delta_percent<0?'improved':current.delta_percent>0?'regressed':''):''">{{current.delta_label}}</span></div></div>
        <div class="time-side-head"><div><span class="time-badge a">A</span>{{time(runs.find(run=>run.id===left)?.completed_at||null)}}<strong>{{current.left?.latency ?? '—'}} μs</strong></div><div><span class="time-badge b">B</span>{{time(runs.find(run=>run.id===right)?.completed_at||null)}}<strong>{{current.right?.latency ?? '—'}} μs</strong></div></div>
        <p v-if="detailLoading" class="time-missing" role="status">正在读取逐项详情…</p><p v-else-if="!detail[0]?.available||!detail[1]?.available" class="time-missing">{{detail[0]?.reason||current.left?.reason||'A 无结果'}}　/　{{detail[1]?.reason||current.right?.reason||'B 无结果'}}</p>
        <details v-for="tab in tabs" :key="tab" class="time-detail-group" :open="tab==='overview'"><summary>{{tabNames[tab]||tab}}</summary><div v-for="id in groups(tab)" :key="id" class="time-fact-block"><h4>{{title(tab,id)}}</h4><table><thead><tr><th scope="col">指标</th><th scope="col">A</th><th scope="col">B</th></tr></thead><tbody><tr v-for="fact in facts([...(section(detail[0],tab,id)?.facts||[]),...(section(detail[0],tab,id)?.metadata_facts||[])],[...(section(detail[1],tab,id)?.facts||[]),...(section(detail[1],tab,id)?.metadata_facts||[])])" :key="fact.label"><th scope="row">{{fact.label}}</th><td>{{fact.a}}</td><td>{{fact.b}}</td></tr></tbody></table><div class="time-extra"><div v-for="(side,i) in detail" :key="i" v-html="section(side,tab,id)?.extra||''"></div></div></div></details>
        <details class="time-detail-group"><summary>原始结果 JSON</summary><div class="time-raw"><pre v-for="(side,i) in detail" :key="i">{{JSON.stringify(side,null,2)}}</pre></div></details>
      </div>
      <p class="time-footnote">仅比较两次模型预测；图中越短表示预测耗时越小，不代表精度更高。不同配置、规格或引擎身份只并排展示。</p>
    </template>
  </template>
</section>
</template>
