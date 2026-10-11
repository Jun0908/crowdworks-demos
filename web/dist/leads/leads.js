import { $,root,Engine,clearError,showError,progress,cell,badge,wireDownloads,enableDownloads } from '../tools-ui.js';
let sample=null,data=null,result=null,busy=false,isSample=true,tab='targets';
function buttons(){ $('run').disabled=busy||!engine?.ready||!data;enableDownloads(!!result&&!busy); }
let engine;
engine=new Engine(()=>buttons());
function invalidate(){if(busy)return;result=null;enableDownloads(false);$('result-state').textContent='入力・条件を変更しました。再実行してください。';clearError();}
function lock(value){busy=value;$('settings').classList.toggle('running',value);document.querySelectorAll('#settings input,#settings button:not(#retry),#settings textarea').forEach(el=>el.disabled=value);buttons();}
function renderTable(){
  const excluded=tab==='excluded';$('level').disabled=excluded;
  const headers=excluded?['除外理由','店名','住所','電話']:['エリア','店名','住所','電話','炭火判定','判定根拠'];
  const head=document.createElement('tr');headers.forEach(name=>{const th=document.createElement('th');th.textContent=name;head.append(th);});$('table-head').replaceChildren(head);$('table-body').replaceChildren();
  const all=result?(excluded?result.excluded:result.records):[];
  const query=$('search').value.trim().toLowerCase();
  const rows=all.filter(r=>(!query||(r['店名']+' '+r['住所']).toLowerCase().includes(query))&&(excluded||!$('level').value||r['炭火判定']===$('level').value));
  const frag=document.createDocumentFragment();
  for(const r of rows){const tr=document.createElement('tr');for(const name of headers){const td=cell(r[name]);if(name==='炭火判定'){td.replaceChildren(badge(r[name],r[name]==='確定'?'good':r[name]==='可能性'?'warn':''));}if(name==='除外理由'){td.replaceChildren(badge(r[name],'bad'));}if(name==='判定根拠')td.className='reason';tr.append(td);}frag.append(tr);}
  $('table-body').append(frag);$('empty').classList.toggle('hidden',rows.length>0);$('empty').textContent=result?'条件に一致する店舗はありません。':'条件を選び、「候補リストを作成」を押してください。';$('table-count').textContent=result?`${rows.length} / ${all.length} 件を表示`:'未実行';
}
function render(){const s=result.summary;$('count-input').textContent=s.raw_results;$('count-target').textContent=s.final_rows;$('count-duplicate').textContent=s.raw_results-s.after_name_phone_address_dedupe;$('count-excluded').textContent=result.excluded.length;for(const [id,key] of [['flow-input','raw_results'],['flow-id','after_place_id_dedupe'],['flow-name','after_name_phone_address_dedupe'],['flow-final','final_rows']])$(id).textContent=s[key];$('judgement-summary').textContent=`炭火判定：確定 ${s.judgement['確定']}件 / 可能性 ${s.judgement['可能性']}件 / 不明 ${s.judgement['不明']}件。外部APIへのリクエストは0件です。`;$('result-state').textContent='ブラウザで処理済み';renderTable();}
$('run').addEventListener('click',async()=>{clearError();result=null;lock(true);progress('重複排除・対象外の除外・炭火判定・Excelの作成を実行中…');try{result=await engine.request({tool:'leads',data,areas:[...document.querySelectorAll('#areas input:checked')].map(i=>i.value),use_reviews:$('use-reviews').checked,sample:isSample});render();}catch(e){showError(e.message);$('result-state').textContent='処理を完了できませんでした。';renderTable();}finally{progress('');lock(false);}});
document.querySelectorAll('#areas input,#use-reviews').forEach(el=>el.addEventListener('change',invalidate));
$('search').addEventListener('input',renderTable);$('level').addEventListener('change',renderTable);
for(const [id,value] of [['tab-target','targets'],['tab-excluded','excluded']])$(id).addEventListener('click',()=>{tab=value;for(const [other,val] of [['tab-target','targets'],['tab-excluded','excluded']])$(other).setAttribute('aria-selected',String(val===tab));renderTable();});
function reset(){if(!sample||busy)return;data=structuredClone(sample);isSample=true;$('source-name').textContent='架空の検索結果26件';$('json-text').value=JSON.stringify(data,null,2);$('json-file').value='';document.querySelectorAll('#areas input').forEach(el=>el.checked=true);$('use-reviews').checked=true;invalidate();buttons();}
$('reset').addEventListener('click',reset);
function useJson(text,name){if(new TextEncoder().encode(text).length>2*1024*1024)throw new Error('JSONは2MB以下にしてください。');let parsed;try{parsed=JSON.parse(text);}catch{throw new Error('JSONの形式が不正です。カンマや引用符を確認してください。');}if(!Array.isArray(parsed)&&!(parsed&&Array.isArray(parsed.places)))throw new Error('places配列を持つJSON、または店舗の配列を指定してください。');data=parsed;isSample=false;invalidate();$('source-name').textContent=name;$('json-text').value=text;buttons();}
$('apply-json').addEventListener('click',()=>{try{useJson($('json-text').value,'編集した検索結果JSON');}catch(e){showError(e.message);}});
$('json-file').addEventListener('change',async e=>{const file=e.target.files[0];if(!file)return;try{if(file.size>2*1024*1024)throw new Error('JSONは2MB以下にしてください。');useJson(await file.text(),file.name);}catch(error){showError(error.message);}});
$('retry').addEventListener('click',()=>engine.start());wireDownloads(()=>result,'sales_leads');renderTable();
try{const response=await fetch(new URL('data/leads.json',root));if(!response.ok)throw new Error();sample=await response.json();reset();}catch{showError('サンプルを読み込めませんでした。ページを再読み込みしてください。');}
