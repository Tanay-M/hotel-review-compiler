// Exercise upload and demo flows without the removed column mapping controls.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const {File} = require('node:buffer');
const root = path.resolve(__dirname, '..');
const controls = new Map();
function control(id) {
  assert(!['text-column', 'id-column'].includes(id), `Removed control accessed: ${id}`);
  if (!controls.has(id)) controls.set(id, {value: id === 'analysis-method' ? 'hybrid' : '',
    listeners: {}, addEventListener(event, handler) {this.listeners[event] = handler;},
    setAttribute() {}, scrollIntoView() {}, classList: {add() {}, remove() {}}});
  return controls.get(id);
}
const demos = [12,100,500].map(size => ({dataset: {demo: String(size)},
  addEventListener(event, handler) {this.handler = handler;}}));
const uploads = [];
const context = vm.createContext({$, document: {querySelectorAll: s => s === '[data-demo]' ? demos : []},
  File, URLSearchParams, AbortController, setTimeout, clearTimeout,
  fetch: async (url, options) => {
    if (options?.method === 'POST') {
      uploads.push({url, file: options.body});
      return {ok:true, json: async () => ({batch_id:'test'})};
    }
    const file = url === '/reviews_100.csv' ? 'examples/hotel_reviews_100.csv'
      : url === '/api/real-demo.csv' ? 'output/datasets/booking_cleaned/booking_italy_cleaned_demo_500.csv'
      : 'hotel_compiler/web_assets/demo.csv';
    return {ok:true, blob: async () => new Blob([fs.readFileSync(path.join(root,file))])};
  }});
function $(id) {return control(id);}
vm.runInContext(fs.readFileSync(path.join(root,'hotel_compiler/web_assets/dashboard.js'),'utf8'),context);
vm.runInContext('resetResults = () => {}; clearFilters = () => {}; renderDashboard = () => {};',context);

(async () => {
  const manifest = JSON.parse(fs.readFileSync(path.join(root,'dataset/manifest.json'),'utf8'));
  for (const entry of manifest.files.filter(r => r.ui_uploadable)) {
    context.uploadFile = new File([fs.readFileSync(path.join(root,'dataset',entry.file))],entry.file);
    await vm.runInContext('selectFile(uploadFile); uploadCSV();',context);
    const query = new URL(uploads.at(-1).url,'http://localhost').searchParams;
    assert.equal(query.get('text_column'), entry.columns[1]);
    assert.equal(query.get('id_column'), entry.columns[0]);
    assert.equal(query.get('method'),'hybrid');
    assert.equal(control('upload-error').textContent,'');
  }
  for (const button of demos) {
    const before=uploads.length;await button.handler();assert.equal(uploads.length,before+1);
  }
  const before=uploads.length;
  await control('real-booking-demo').listeners.click();assert.equal(uploads.length,before+1);
  const html=fs.readFileSync(path.join(root,'hotel_compiler/web_assets/index.html'),'utf8');
  assert(!html.includes('id="text-column"') && !html.includes('id="id-column"'));
  console.log(`PASS: ${manifest.files.filter(r=>r.ui_uploadable).length} folder uploads, 3 synthetic buttons and real Booking button; no removed-control access.`);
})().catch(error => {console.error(error);process.exitCode=1;});
