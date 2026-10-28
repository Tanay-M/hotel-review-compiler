// Artifact Tool authors the two-column CSVs; Python prepares source-mapped inputs.
import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { Workbook } from '@oai/artifact-tool';

const root=path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const data=JSON.parse(await fs.readFile(path.join(root,'tmp/booking-clean-builder/inputs.json'),'utf8'));
const out=path.join(root,'output/datasets/booking_cleaned');
await fs.mkdir(out,{recursive:true});
const quote=value => /[",\r\n]/.test(String(value)) ? `"${String(value).replaceAll('"','""')}"` : String(value);
const csv=matrix => '\ufeff'+matrix.map(row=>row.map(quote).join(',')).join('\r\n')+'\r\n';

async function exportReviews(name,records,preview=false){
  const wb=Workbook.create();const sh=wb.worksheets.add('Reviews');
  const values=[['sr.no','review'],...records.map((r,i)=>[i+1,r.review])];
  // Treat reviews as literal text, including any formula-leading source strings.
  sh.getRange(`A1:B${values.length}`).values=values.map(row=>row.map(v=>typeof v==='string'&&v.startsWith('=')?"'"+v:v));
  wb.recalculate();
  const restored=sh.getRange(`A1:B${values.length}`).values;
  for(let i=0;i<values.length;i++){
    if(restored[i][0]!==values[i][0])throw Error('Serial ID changed.');
    if(values[i][1].startsWith('='))restored[i][1]=restored[i][1].slice(1);
    if(restored[i][1]!==values[i][1])throw Error('Review wording changed.');
  }
  await fs.writeFile(path.join(out,name),csv(restored));
  if(preview){
    sh.getRange('A1:B6').format.font.name='Arial';
    sh.getRange('A1:A6').format.columnWidth=9;
    sh.getRange('B1:B6').format.columnWidth=95;
    sh.getRange('B1:B6').format.wrapText=true;
    sh.getRange('A2:B6').format.rowHeight=92;
    sh.getRange('A1:B1').format.fill='#E7EEF5';
    wb.recalculate();
    console.log((await wb.inspect({kind:'table',range:'Reviews!A1:B4',include:'values',tableMaxRows:4,tableMaxCols:2,maxChars:1000})).ndjson);
    const image=await wb.render({sheetName:'Reviews',range:'A1:B6',scale:1.5,format:'png'});
    await fs.writeFile(path.join(root,'tmp/booking-clean-builder/preview.png'),new Uint8Array(await image.arrayBuffer()));
  }
}
await exportReviews('booking_italy_cleaned_demo_500.csv',data.sample,true);
await exportReviews('booking_italy_cleaned_all.csv',data.records);
for(let start=0;start<data.records.length;start+=1000){
  await exportReviews(`booking_italy_cleaned_part_${String(start/1000+1).padStart(2,'0')}.csv`,data.records.slice(start,start+1000));
}
const mapping=records=>[['sr.no','source_row','original_sha256','cleaned_sha256'],...records.map((r,i)=>[i+1,r.source_row,r.original_sha256,r.cleaned_sha256])];
await fs.writeFile(path.join(out,'demo_source_map.csv'),csv(mapping(data.sample)));
await fs.writeFile(path.join(out,'all_source_map.csv'),csv(mapping(data.records)));
const fields=['source_row','status','duplicate_of_source_row','original_sha256','cleaned_sha256'];
await fs.writeFile(path.join(out,'cleaning_audit.csv'),csv([fields,...data.audit.map(r=>fields.map(k=>r[k]))]));
await fs.writeFile(path.join(out,'cleaning_manifest.json'),JSON.stringify(data.manifest,null,2)+'\n');
console.log(`Exported ${data.sample.length} demo reviews and ${data.records.length} unique cleaned source reviews.`);
