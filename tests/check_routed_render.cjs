// Isolated renderer contract: no browser, network, or running page access.
const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
class Element {
  constructor(tag, text='') { this.tag=tag; this.text=String(text); this.children=[]; this.hidden=false; }
  append(...items) { this.children.push(...items); }
  replaceChildren(...items) { this.children=items; }
  addEventListener(event, handler) { this[event]=handler; }
}
const controls = new Map();
const control = id => { if(!controls.has(id)) controls.set(id,new Element('div')); return controls.get(id); };
const node = (tag,cls='',text='') => new Element(tag,text);
const table = (headers,rows) => { const el=node('table'); el.append(...headers,...rows.flat()); return el; };
const text = element => element instanceof Element ? element.text+' '+element.children.map(text).join(' ') : String(element);
const context = vm.createContext({$:control,node,table,fields:pairs=>table([],pairs),badge:v=>node('span','',v),
  number:v=>v==null?'Unavailable':Number(v).toFixed(4),modelProbability:v=>v==null?'—':`${100*v}%`,applyEvidence:()=>{},
  analysis:{status:'partial',overall:'Positive',review_score:null,routed_analysis:{selected_method:'independent_neural',
    route_status:'reanalyzed',overall:'Negative',review_index:-.6,model_id:'test-only',
    categories:[{category:'Service',label:'Negative',model_direction_index:-.6,sentences:1}],
    records:[{category:'Service',context:'We waited two hours.',label:'Negative',probabilities:{Negative:.9},model_direction_index:-.6,start:0,end:20}],
    decisions:[{context:'We waited two hours.',category:'Service',label:'Negative',accepted:true,in_scope:true,reason:'accepted',
      probabilities:{Absent:.05,Negative:.9,'Neutral/Mixed':.02,Positive:.03}}],warnings:[]}},
  batch:{routed_summary:{routed_reviews:2,neural_results:1,abstained_reviews:1,retained_hybrid:1,model_errors:0,
    categories:[{category:'Service',positive:0,negative:1,mixed_uncertain:0,mean_model_index:-.6,index_reviews:1,row_ids:['one']}]},rows:[]}});
vm.runInContext(fs.readFileSync('hotel_compiler/web_assets/routed.js','utf8'),context);
vm.runInContext('renderRoutedResult();renderRoutedDashboard();',context);
assert.equal(control('routed-result').hidden,false);
assert(text(control('routed-result')).includes('Selected result: neural category & sentiment analysis'));
assert(text(control('routed-result')).includes('We waited two hours.'));
assert(text(control('routed-result')).includes('Staff feedback is pooled under Service'));
assert(text(control('routed-dashboard')).includes('Independent review reanalysis'));
assert(text(control('routed-dashboard')).includes('0 model errors'));
vm.runInContext('analysis.routed_analysis.categories=[];analysis.routed_analysis.review_index=null;renderRoutedResult();',context);
assert(text(control('routed-result')).includes('No in-scope category passed'));
assert(text(control('routed-result')).includes('Unavailable'));
vm.runInContext('analysis={};batch={};renderRoutedResult();renderRoutedDashboard();',context);
assert.equal(control('routed-result').hidden,true);
assert.equal(control('routed-dashboard').hidden,true);
console.log('PASS: isolated independent-result, score, evidence, abstention and dashboard render contracts.');
