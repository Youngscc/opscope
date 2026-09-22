<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import Configuration from 'virtual:opscope-configuration'
import { useOpScopeStore } from '../stores/opscope'
import type { Configuration as Config, Fields } from '../types'
import Modal from './Modal.vue'
const props = defineProps<{open:boolean}>(), emit = defineEmits<{close:[]}>()
const s = useOpScopeStore(), draft=ref<Config>(), shapes=ref<string[]>([])
const search=ref(''), category=ref('all'), errors=ref<{field:string;message:string}[]>([])
const error_box=ref<HTMLElement>()
const op=computed(()=>s.data!.catalog.operators.find((op:Fields)=>op.id===draft.value?.operator_id))
const group=computed(()=>s.data!.catalog.groups.find((g:Fields)=>g.id===op.value?.group_id))
const groups=computed(()=>s.data!.catalog.groups.filter((g:Fields)=>(category.value==='all'||g.category===category.value)&&`${g.name} ${g.category}`.toLowerCase().includes(search.value.toLowerCase())))
const categories=computed(()=>[...new Set<string>(s.data!.catalog.groups.map((g:Fields)=>g.category))].sort())
function load(value:Config) {
  draft.value=Configuration.clone(value);shapes.value=value.inputs.map(t=>(t.shape||[]).map(d=>d??'?').join(', '));errors.value=[]
}
watch(()=>props.open, open=>{if(open){load(s.config!);search.value='';category.value='all'}})
function select(id:string) {
  load(id==='demo:matmul'?s.data!.catalog.default_config:Configuration.from_operator(s.data!.catalog.operators.find((op:Fields)=>op.id===id)))
}
async function apply() {
  const next=Configuration.clone(draft.value!)
  next.inputs.forEach((t,i)=>t.shape=Configuration.parse_shape(shapes.value[i]!))
  errors.value=Configuration.validate(next,op.value,s.data!.catalog.dtypes)
  if(errors.value.length){await nextTick();error_box.value?.focus();return}
  s.apply(next);emit('close')
}
</script>
<template><Modal :open="open" title="选择算子与输入配置" class-name="config-dialog" @close="emit('close')"><div v-if="draft" class="config-shell"><header class="config-header"><div><span class="eyebrow">OPERATOR CATALOG</span><h2>选择算子与输入配置</h2><p>选择算子，配置输入，比较不同硬件与方法的评估结果。</p></div><button class="button icon-button" aria-label="取消算子配置" @click="emit('close')">×</button></header>
<div class="config-body"><aside class="operator-browser" aria-label="算子目录"><label class="search-field"><span class="sr-only">搜索算子</span><input v-model="search" type="search" placeholder="搜索算子名称…"></label><div class="catalog-filters"><label><span class="sr-only">算子类别</span><select v-model="category"><option value="all">全部类别</option><option v-for="c in categories" :key="c">{{c}}</option></select></label></div><div class="catalog-count">{{groups.length}} / {{s.data!.catalog.groups.length}} 个算子</div><div class="operator-list"><button v-for="g in groups" :key="g.id" type="button" class="operator-item" :aria-pressed="g.variants.includes(draft.operator_id)" @click="select(g.variants.includes(draft.operator_id)?draft.operator_id:g.variants[0])"><span>{{g.name}}</span><small>{{g.category}}{{g.variants.length>1?` · ${g.variants.length} 种输入形式`:''}}</small></button></div><p class="catalog-scope">按算子名称与功能分类浏览</p></aside>
<form id="configuration-form" class="configuration-form" novalidate @submit.prevent="apply"><div class="config-editor"><div class="editor-title"><div><span class="eyebrow">{{op.category}}</span><h3>{{op.display_name}}</h3></div></div><p class="operator-note">{{op.reason || '按张量设置形状与精度；问号需要替换为实际大小。'}}</p><label v-if="group.variants.length>1" class="input-form-control">输入形式<select :value="draft.operator_id" @change="select(($event.target as HTMLSelectElement).value)"><option v-for="id in group.variants" :key="id" :value="id">{{s.data!.catalog.operators.find((o:Fields)=>o.id===id).template_label}}</option></select></label>
<div v-if="errors.length" ref="error_box" class="config-error" role="alert" tabindex="-1"><a v-for="e in errors" :key="e.field" :href="'#'+e.field">{{e.message}}</a></div><div class="tensor-editor-heading"><h4>输入张量</h4><span>shape · dtype</span></div><p class="shape-help">维度可用逗号或 × 分隔；问号表示尚未设置的维度。</p>
<fieldset v-for="(t,i) in draft.inputs" :key="i" class="tensor-input"><legend><b>{{t.name}}</b><span>{{t.role==='parameter'?'参数张量':'输入'}}</span></legend><div class="tensor-fields"><label>形状<input :id="'shape-'+i" v-model="shapes[i]" :aria-label="`${t.name} 形状`" :aria-invalid="errors.some(e=>e.field==='shape-'+i)" autocomplete="off"></label><label>dtype<select :id="'dtype-'+i" v-model="t.dtype" :aria-label="`${t.name} dtype`"><option v-for="d in s.data!.catalog.dtypes" :key="d" :value="d">{{d.toUpperCase()}}</option></select></label></div><p class="tensor-template">模板 {{op.inputs[i].expression}}</p></fieldset>
<div v-if="draft.domain==='demo'" class="demo-options"><h4>执行配置</h4><div class="option-grid"><label>累加精度<select v-model="draft.options.accumulator_dtype"><option value="fp32">FP32</option><option value="fp16">FP16</option></select></label><label>布局<select v-model="draft.options.layout"><option>row-major</option><option>column-major</option></select></label><label class="check-option"><input v-model="draft.options.transpose_a" type="checkbox">转置 A</label><label class="check-option"><input v-model="draft.options.transpose_b" type="checkbox">转置 B</label></div></div>
<details class="catalog-provenance"><summary>输出模板</summary><p v-for="t in op.outputs" :key="t.name"><b>{{t.name}}</b> · {{t.dtype}}<br>{{t.shape}}</p></details><p class="configuration-boundary">应用后点击“运行评估”。未适配组合将说明原因，不自动回退到其他方法。</p></div></form></div>
<footer class="config-footer"><button class="text-button" @click="search='';category='all';select('demo:matmul')">载入 MatMul 示例</button><span>修改后需重新评估</span><button class="button primary" form="configuration-form" type="submit" :disabled="!op.configurable">应用配置</button></footer></div></Modal></template>
