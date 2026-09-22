const test = require('node:test');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');

function context() {
  const c = {state: {serviceReady:true,config:{operator:'MatMul'},hardware:new Set(['h200']),methods:new Set(['roofline'])},
    Configuration:{clone:x=>JSON.parse(JSON.stringify(x))}, data:{results:[]}, setTimeout,
    by_id:()=>({textContent:''}), announce:()=>{}, render_workload_heading:()=>{}, update_filters:()=>{}};
  vm.createContext(c);
  vm.runInContext(fs.readFileSync('evaluation-ui.js','utf8'),c);
  c.show_evaluation_pending=()=>{}; c.render_evaluation_controls=()=>{};
  return c;
}

test('stale completion never overwrites current configuration',async()=>{
  const c=context(); let accepted=false; let release;
  c.evaluation_request=async(path)=>path==='/api/evaluations'?{id:'job'}:await new Promise(r=>release=r);
  c.accept_evaluation=()=>{accepted=true};
  const pending=c.run_evaluation(); await new Promise(r=>setImmediate(r));
  c.state.evaluationToken++;
  release({status:'completed',payload:{}}); await pending;
  assert.equal(accepted,false);
});

test('duplicate clicks submit only one job',async()=>{
  const c=context(); let count=0;
  c.evaluation_request=async()=>{count++;throw new Error('offline')};
  await Promise.all([c.run_evaluation(),c.run_evaluation()]);
  assert.equal(count,1);assert.equal(c.state.evaluating,false);
});

test('snapshot opens with captured config while demo restore retains fixtures',()=>{
  const c=context();
  const captured={operator:'MatMul',inputs:[{name:'A',shape:[1024,4096],dtype:'fp16'}]};
  c.data={initial_configuration:captured,results:[{available:true,synthetic:false}],
    demo_results:Array.from({length:25},()=>({available:true,synthetic:true})),
    demo_matrix:{scales:{latency_max:300}},demo_workload:{operator:'MatMul'},
    demo_methods:[{id:'roofline',source:'解析模型'}],methods:[{id:'roofline',source:'解析预测'}],
    evaluation:{hardware_ids:['h200'],method_ids:['roofline']},catalog:{default_config:{},groups:[]}};
  c.by_id=()=>({innerHTML:'',addEventListener:()=>{}});
  vm.runInContext(fs.readFileSync('catalog-ui.js','utf8'),c);
  c.render_workload_heading=()=>{};
  c.initialize_catalog();
  assert.equal(c.state.config.inputs[0].shape[0],1024);
  assert.equal(c.state.baseline.length,25);
  assert.equal(c.state.baselineMatrix.scales.latency_max,300);
  assert.equal(c.state.demoMethods[0].source,'解析模型');
  assert.equal(c.state.chart,'latency');
  assert.equal(c.state.hardware.has('h200'),true);
});

test('partial results arrive while polling continues before final completion',async()=>{
  const c=context();const accepted=[];let release;
  c.evaluation_request=async(path)=>{
    if(path==='/api/evaluations')return {id:'job'};
    if(!accepted.length)return {status:'running',revision:1,payload:{name:'first'}};
    return await new Promise(r=>release=r);
  };
  c.accept_evaluation=(payload,status)=>{accepted.push(payload.name);c.state.evaluating=status==='running'};
  c.setTimeout=resolve=>setImmediate(resolve);
  const pending=c.run_evaluation();
  while(!release)await new Promise(r=>setImmediate(r));
  assert.deepEqual(accepted,['first']);assert.equal(c.state.evaluating,true);
  release({status:'completed',revision:2,payload:{name:'final'}});
  await pending;
  assert.deepEqual(accepted,['first','final']);assert.equal(c.state.evaluating,false);
});
