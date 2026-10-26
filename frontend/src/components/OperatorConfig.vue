<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import Configuration from 'virtual:opscope-configuration'
import { useOpScopeStore } from '../stores/opscope'
import type { Configuration as Config, Fields } from '../types'
import Modal from './Modal.vue'
import { STATIC_DEMO } from '../demo-mode'
const props = defineProps<{open:boolean}>(), emit = defineEmits<{close:[]}>()
const s = useOpScopeStore(), draft=ref<Config>(), shapes=ref<string[]>([])
const attributeText=ref<Record<string,string>>({})
const search=ref(''), category=ref<string[]>([]), errors=ref<{field:string;message:string}[]>([])
const error_box=ref<HTMLElement>()
const op=computed(()=>s.data!.catalog.operators.find((op:Fields)=>op.id===draft.value?.operator_id))
const group=computed(()=>s.data!.catalog.groups.find((g:Fields)=>g.id===op.value?.group_id))
const groups=computed(()=>s.data!.catalog.groups.filter((g:Fields)=>category.value.includes(g.category)&&`${g.name} ${g.category}`.toLowerCase().includes(search.value.toLowerCase())))
const categories=computed(()=>[...new Set<string>(s.data!.catalog.groups.map((g:Fields)=>g.category))].sort())
const outputRows=computed(()=> {
  if (!draft.value || !op.value) return []
  const inputs=shapes.value.map(text=>Configuration.parse_shape(text))
  const current={...draft.value, inputs:draft.value.inputs.map((t,i)=>({...t,shape:inputs[i]}))}
  const valid=!Configuration.validate(current,op.value,s.data!.catalog.dtypes).length
  return (op.value.output_preview || []).map((row:Fields)=> {
    const compatible=valid && inputs.every((shape,i)=>shape?.length===op.value.inputs[i].shape.length) && (!row.same_shape || inputs.every(shape=>JSON.stringify(shape)===JSON.stringify(inputs[0])))
    const dims=row.shape_refs.map((ref:Fields)=>inputs[ref.input]?.[ref.option && draft.value!.options[ref.option] ? ref.alternate : ref.axis])
    return {name:row.name, shape:compatible && dims.every((d:unknown)=>typeof d==='number') ? `[${dims.join(', ')}]` : '待完善输入',
      dtype:(row.dtype || draft.value!.inputs[row.dtype_input]?.dtype || '待确认').toUpperCase()}
  })
})
function load(value:Config) {
  draft.value=Configuration.clone(value);shapes.value=value.inputs.map(t=>(t.shape||[]).map(d=>d??'?').join(', '));errors.value=[]
  attributeText.value=Object.fromEntries(Object.entries(value.attributes||{}).map(([name,item])=>[name,Array.isArray(item)?item.join(','):item==null?'':String(item)]))
}
watch(()=>props.open, open=>{if(open){load(s.config!);search.value='';category.value=[...categories.value]}})
function select(id:string) {
  load(id==='demo:matmul'?s.data!.catalog.default_config:Configuration.from_operator(s.data!.catalog.operators.find((op:Fields)=>op.id===id)))
}
function focus_error(field:string) {
  // Focus the input without replacing the standalone workspace's hash route.
  const input=document.getElementById(field)
  input?.focus();input?.scrollIntoView({block:'nearest'})
}
async function apply() {
  const next=Configuration.clone(draft.value!)
  next.inputs.forEach((t,i)=>t.shape=Configuration.parse_shape(shapes.value[i]!))
  next.attributes=Object.fromEntries((op.value?.parameters||[]).map((field:Fields)=>{
    const text=(attributeText.value[field.name]||'').trim()
    return [field.name,['permutation','integer_list'].includes(field.type)?text.split(',').map((part:string)=>Number(part.trim())):text===''?null:Number(text)]
  }))
  errors.value=Configuration.validate(next,op.value,s.data!.catalog.dtypes)
  if(errors.value.length){await nextTick();error_box.value?.focus();return}
  s.apply(next);emit('close')
}
</script>
<template><Modal :open="open" title="选择算子与输入配置" class-name="config-dialog" @close="emit('close')"><div v-if="draft" class="config-shell"><header class="config-header"><div><h2>选择算子与输入配置</h2></div><button class="button icon-button" aria-label="取消算子配置" @click="emit('close')">×</button></header>
<div class="config-body"><aside class="operator-browser" aria-label="算子目录"><label class="search-field"><span class="sr-only">搜索算子</span><input v-model="search" type="search" placeholder="搜索算子名称…"></label><div class="catalog-filters"><details class="category-menu"><summary>{{category.length===categories.length?'全部类别':`已选 ${category.length} 类`}}<span class="chevron"></span></summary><div class="category-popover"><label><input type="checkbox" :checked="category.length===categories.length" :indeterminate="category.length>0 && category.length<categories.length" @change="category=($event.target as HTMLInputElement).checked?[...categories]:[]">全部类别</label><label v-for="c in categories" :key="c"><input v-model="category" type="checkbox" :value="c">{{c}}</label></div></details></div><div class="catalog-count">{{groups.length}} / {{s.data!.catalog.groups.length}} 个算子</div><div class="operator-list"><button v-for="g in groups" :key="g.id" type="button" class="operator-item" :aria-pressed="g.variants.includes(draft.operator_id)" @click="select(g.variants.includes(draft.operator_id)?draft.operator_id:g.variants[0])"><span>{{g.name}}</span><small>{{g.category}}{{g.variants.length>1?` · ${g.variants.length} 种输入形式`:''}}</small></button></div></aside>
<form id="configuration-form" class="configuration-form" novalidate @submit.prevent="apply"><div class="config-editor"><div class="editor-title"><div><h3>{{op.display_name}}</h3><span class="category-badge">{{op.category}}</span></div></div><p class="operator-note">{{op.reason || '按张量设置形状与精度；问号需要替换为实际大小。'}}</p><label v-if="group.variants.length>1" class="input-form-control">输入形式<select :value="draft.operator_id" @change="select(($event.target as HTMLSelectElement).value)"><option v-for="id in group.variants" :key="id" :value="id">{{s.data!.catalog.operators.find((o:Fields)=>o.id===id).template_label}}</option></select></label>
<div v-if="errors.length" ref="error_box" class="config-error" role="alert" tabindex="-1"><a v-for="e in errors" :key="e.field" :href="'#'+e.field" @click.prevent="focus_error(e.field)">{{e.message}}</a></div><div class="tensor-editor-heading"><h4>输入张量</h4><span>shape · dtype</span></div><p class="shape-help">维度可用逗号或 × 分隔；问号表示尚未设置的维度。</p>
<fieldset v-for="(t,i) in draft.inputs" :key="i" class="tensor-input"><legend><b>{{t.name}}</b><span>{{t.role==='parameter'?'参数张量':'输入'}}</span></legend><div class="tensor-fields"><label>形状<input :id="'shape-'+i" v-model="shapes[i]" :aria-label="`${t.name} 形状`" :aria-invalid="errors.some(e=>e.field==='shape-'+i)" autocomplete="off"></label><label>dtype<select :id="'dtype-'+i" v-model="t.dtype" :aria-label="`${t.name} dtype`"><option v-for="d in s.data!.catalog.dtypes" :key="d" :value="d">{{d.toUpperCase()}}</option></select></label></div><p class="tensor-template">模板 {{op.inputs[i].expression}}</p></fieldset>
<div v-if="op.parameters?.length" class="demo-options"><h4>算子属性</h4><div class="option-grid"><label v-for="field in op.parameters" :key="field.name">{{field.label}}<input :id="`attribute-${field.name}`" v-model="attributeText[field.name]" inputmode="numeric" autocomplete="off" :aria-invalid="errors.some(e=>e.field===`attribute-${field.name}`)"></label></div></div>
<div v-if="draft.domain==='demo'" class="demo-options"><h4>执行配置</h4><div class="option-grid"><label>累加精度<select v-model="draft.options.accumulator_dtype"><option value="fp32">FP32</option><option value="fp16">FP16</option></select></label><label>布局<select v-model="draft.options.layout"><option>row-major</option><option>column-major</option></select></label><label class="check-option"><input v-model="draft.options.transpose_a" type="checkbox">转置 A</label><label class="check-option"><input v-model="draft.options.transpose_b" type="checkbox">转置 B</label></div></div>
<section class="output-preview" aria-label="输出张量"><div class="tensor-editor-heading"><h4>输出张量</h4></div><table><thead><tr><th>名称</th><th>形状 · Shape</th><th>数据类型 · dtype</th></tr></thead><tbody><tr v-for="t in outputRows" :key="t.name"><th scope="row">{{t.name}}</th><td class="output-shape">{{t.shape}}</td><td><span class="output-dtype">{{t.dtype}}</span></td></tr><tr v-if="!outputRows.length"><td colspan="3" class="output-pending">输出形状与数据类型待确认</td></tr></tbody></table></section><p v-if="!STATIC_DEMO" class="configuration-boundary">应用后点击“运行评估”。</p></div></form></div>
<footer class="config-footer"><button class="text-button" @click="search='';category=[...categories];select('demo:matmul')">载入 MatMul 示例</button><span v-if="!STATIC_DEMO">修改后需重新评估</span><button class="button" @click="emit('close')">取消</button><button class="button primary" form="configuration-form" type="submit" :disabled="!op.configurable">应用配置</button></footer></div></Modal></template>
