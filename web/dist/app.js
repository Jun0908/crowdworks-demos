'use strict';
const $ = (id) => document.getElementById(id);
const escapeHtml = (value) => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
let result = null, sampleResult = null, sampleCsv = '', csvText = '', sourceName = 'sample';
let currentTab = 'targets', page = 1, worker, ready = false, busy = false, dirty = false, requestId = 0, timer;
const pageSize = 10;
const sourceControls = ['month', 'lookahead', 'convention', 'csv-file', 'reset'];
function updateButtons() {
  $('run').disabled = !ready || busy || !csvText;
  for (const id of sourceControls) $(id).disabled = busy;
  for (const kind of ['csv','xlsx','zip']) $('download-' + kind).disabled = !result || busy || dirty;
}
function setStatus(message, state = 'ready') {
  $('runtime-status').replaceChildren();
  const dot = document.createElement('i'); dot.className = 'status-dot ' + (state === 'loading' ? 'pending' : state === 'failed' ? 'failed' : '');
  $('runtime-status').append(dot, document.createTextNode(message));
}
function showError(message) { $('error').textContent = message; $('error').classList.remove('hidden'); }
function clearError() { $('error').classList.add('hidden'); $('error').textContent = ''; }
function markDirty() { dirty = true; $('dirty').classList.remove('hidden'); $('result-state').textContent = '変更前の条件による結果'; clearError(); updateButtons(); }
function startEngine() {
  if (worker) worker.terminate();
  ready = false; busy = false; clearTimeout(timer); updateButtons();
  $('retry').classList.add('hidden');
  setStatus('計算エンジンの読み込み中…初回のみ少し時間がかかります', 'loading');
  const fail = () => {
    ready = false; busy = false; clearTimeout(timer); worker.terminate();
    setStatus('計算エンジンを読み込めませんでした。通信環境を確認して再読み込みしてください。', 'failed');
    $('retry').classList.remove('hidden'); updateButtons();
  };
  try {
    worker = new Worker('./worker.js');
    timer = setTimeout(fail, 90000);
    worker.onerror = fail;
    worker.onmessage = ({data}) => {
      if (data.status === 'ready') {
        clearTimeout(timer); ready = true; setStatus('計算の準備ができました · この端末内で処理します'); updateButtons(); return;
      }
      if (data.status === 'loading') return;
      if (data.error) {
        if (data.id === undefined) { fail(); return; }
        clearTimeout(timer); busy = false;
        const match = data.error.match(/(?:ValueError|Error): ([^\n]+)/g);
        showError(match ? match[match.length - 1].replace(/^\w+Error: /,'').replace(/^Error: /,'') : '処理できませんでした。CSVの形式と対象月を確認してください。');
        setStatus('入力を確認して、もう一度抽出してください。'); updateButtons(); return;
      }
      if (data.id === requestId && data.result) {
        clearTimeout(timer); busy = false; result = data.result; dirty = false; page = 1;
        $('dirty').classList.add('hidden');
        $('result-state').textContent = 'ブラウザで再計算済み';
        setStatus(`抽出完了 · ${result.records.length}名の対象者を抽出しました`);
        renderResult();
      }
    };
    worker.postMessage({action:'init'});
  } catch { fail(); }
}
function displayName(r) { return r['エリアマネージャー'] || '（AM未設定・要確認）'; }
function renderResult() {
  $('period-heading').textContent = result.period + 'の抽出結果';
  $('count-total').textContent = result.records.length;
  $('count-three').textContent = result.three_count;
  $('count-missed').textContent = result.missed_ids.length;
  $('count-issues').textContent = result.issues.length;
  $('count-source').textContent = `入力${result.input_count}名から抽出`;
  for (const [id, count] of Object.entries({targets:result.records.length, missed:result.missed_ids.length, issues:result.issues.length, excluded:result.excluded.length})) $('tab-'+id).textContent = count;
  $('message-count').textContent = result.message_count;
  $('deadline').textContent = result.deadline;
  const selectedAm = $('am-filter').value;
  const allAMs = [...new Set([...result.records,...result.issues,...result.excluded].map(displayName))].sort((a,b)=>a.localeCompare(b,'ja'));
  $('am-filter').replaceChildren(new Option('すべてのAM',''), ...allAMs.map(name=>new Option(name,name)));
  if (allAMs.includes(selectedAm)) $('am-filter').value = selectedAm;
  const rows = [
    {label:'起算日から計算',found:result.three_count,missed:0,falsePos:0},
    ...result.comparison.map((r,i)=>({label:['終了日列を参照','四半期末と仮定','開始月のみ'][i],found:r['抽出数(3ヶ月)']-r['誤抽出'],missed:r['漏れ'],falsePos:r['誤抽出']}))
  ];
  $('comparison-bars').innerHTML = rows.map(r=>`<div class="bar-row" title="${escapeHtml(`${r.label}：正しい対象${r.found}名、漏れ${r.missed}名、誤抽出${r.falsePos}名`)}"><span>${escapeHtml(r.label)}</span><div class="bar-track"><div class="bar-fill" style="width:${result.three_count ? r.found/result.three_count*100 : 0}%"></div></div><strong>${r.found}<span style="font-size:9px;color:#93a08f"> / ${result.three_count}名</span></strong></div>`).join('');
  renderTable(); updateButtons();
}
function visibleRecords() {
  if (!result) return [];
  const ids = new Set(result.missed_ids);
  const source = currentTab === 'issues' ? result.issues : currentTab === 'excluded' ? result.excluded : currentTab === 'missed' ? result.records.filter(r=>ids.has(r['職員ID'])) : result.records;
  const query = $('search').value.trim().toLocaleLowerCase();
  const am = $('am-filter').value;
  return source.filter(r=>(!query || `${r['氏名']} ${r['職員ID']}`.toLocaleLowerCase().includes(query)) && (!am || displayName(r) === am)).slice().sort((a,b)=>String(a['現契約終了日(計算)'] || '').localeCompare(String(b['現契約終了日(計算)'] || '')));
}
function renderTable() {
  const records = visibleRecords();
  const totalPages = Math.max(1,Math.ceil(records.length/pageSize));
  page = Math.max(1,Math.min(page,totalPages));
  $('table-count').textContent = records.length;
  const isIssues = currentTab === 'issues';
  const headings = isIssues ? ['職員名 / ID','エリア','担当AM','区分','確認内容'] : ['職員名 / ID','担当AM','契約期間','契約満了日','確認事項'];
  $('table-head').innerHTML = '<tr>' + headings.map(h=>`<th scope="col">${h}</th>`).join('') + '</tr>';
  const shown = records.slice((page-1)*pageSize,page*pageSize);
  $('table-body').innerHTML = shown.length ? shown.map(r=>{
    const name = `<td class="name">${escapeHtml(r['氏名'])}<span class="id">${escapeHtml(r['職員ID'])}</span></td>`;
    if (isIssues) return `<tr>${name}<td>${escapeHtml(r['エリア'])}</td><td>${escapeHtml(displayName(r))}</td><td><span class="badge ${r['区分']==='エラー'?'red':'amber'}">${escapeHtml(r['区分'])}</span></td><td class="flag-cell">${escapeHtml(r['内容'])}</td></tr>`;
    const flags = r['フラグ'];
    return `<tr>${name}<td>${escapeHtml(displayName(r))}</td><td><span class="badge ${r['契約期間(月)']===3?'green':''}">${r['契約期間(月)']}ヶ月</span></td><td class="date">${escapeHtml(r['現契約終了日(計算)'])}</td><td class="flag-cell">${flags?escapeHtml(flags):'<span class="ok">—</span>'}</td></tr>`;
  }).join('') : '<tr><td colspan="5" class="empty">該当するデータはありません。検索条件や抽出する期間を変更してください。</td></tr>';
  $('page-info').textContent = records.length ? `${records.length}件中 ${(page-1)*pageSize+1}–${Math.min(page*pageSize,records.length)}件を表示` : '0件';
  $('page-number').textContent = `${page} / ${totalPages}`;
  $('prev-page').disabled = page <= 1; $('next-page').disabled = page >= totalPages;
  $('table-note').textContent = isIssues ? '入力データの確認事項' : '満了日が早い順に表示';
}
function download(kind) {
  if (!result || dirty || busy) return;
  const mime = {csv:'text/csv;charset=utf-8',xlsx:'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',zip:'application/zip'}[kind];
  const bytes = Uint8Array.from(atob(result.files[kind]),c=>c.charCodeAt(0));
  const url = URL.createObjectURL(new Blob([bytes],{type:mime}));
  const anchor = document.createElement('a'); anchor.href = url;
  anchor.download = `${kind==='zip'?'AM別確認依頼文':'更新対象者'}_${result.month}${result.lookahead?'_+'+result.lookahead:''}.${kind}`;
  document.body.appendChild(anchor); anchor.click(); anchor.remove(); setTimeout(()=>URL.revokeObjectURL(url),5000);
}
$('run-form').addEventListener('submit', e=>{
  e.preventDefault(); if (!ready || busy || !csvText) return;
  const month = $('month').value;
  if (!/^\d{4}-\d{2}$/.test(month)) { showError('対象月を指定してください。'); return; }
  busy = true; clearError(); updateButtons();
  setStatus('契約周期を計算し、出力ファイルを作成しています…','loading');
  const id = ++requestId;
  timer = setTimeout(()=>{
    worker.terminate(); ready=false; busy=false; $('retry').classList.remove('hidden');
    showError('処理に時間がかかっています。再読み込み後、行数を減らしてお試しください。');
    setStatus('処理を停止しました。再読み込みしてください。','failed'); updateButtons();
  },60000);
  worker.postMessage({id,payload:{csv_text:csvText,month,lookahead:Number($('lookahead').value),convention:$('convention').value}});
});
for (const id of ['month','lookahead','convention']) $(id).addEventListener('change',markDirty);
$('search').addEventListener('input',()=>{page=1;renderTable();});
$('am-filter').addEventListener('change',()=>{page=1;renderTable();});
$('prev-page').addEventListener('click',()=>{page--;renderTable();});
$('next-page').addEventListener('click',()=>{page++;renderTable();});
const tabs = [...document.querySelectorAll('[data-tab]')];
function switchTab(tab) { currentTab=tab.dataset.tab;page=1;tabs.forEach(b=>b.setAttribute('aria-selected',String(b===tab)));renderTable(); }
tabs.forEach((tab,index)=>{
  tab.addEventListener('click',()=>switchTab(tab));
  tab.addEventListener('keydown',event=>{if(['ArrowRight','ArrowLeft'].includes(event.key)){event.preventDefault();const next=tabs[(index+(event.key==='ArrowRight'?1:-1)+tabs.length)%tabs.length];next.focus();switchTab(next);}});
});
for(const kind of ['csv','xlsx','zip']) $('download-'+kind).addEventListener('click',()=>download(kind));
for(const id of ['help-nav','help-top','help-footer']) $(id).addEventListener('click',()=>$('help-dialog').showModal());
$('close-help').addEventListener('click',()=>$('help-dialog').close());
$('help-dialog').addEventListener('click',event=>{if(event.target===$('help-dialog')){const rect=$('help-dialog').getBoundingClientRect();if(event.clientX<rect.left||event.clientX>rect.right||event.clientY<rect.top||event.clientY>rect.bottom)$('help-dialog').close();}});
$('retry').addEventListener('click',()=>{clearError();startEngine();});
$('csv-file').addEventListener('change',async event=>{
  const file = event.target.files[0]; if(!file)return;
  if(file.size>2*1024*1024){showError('CSVは2MB以下にしてください。');event.target.value='';return;}
  try {
    const buffer=await file.arrayBuffer();let text;
    try{text=new TextDecoder('utf-8',{fatal:true}).decode(buffer);}catch{text=new TextDecoder('shift_jis',{fatal:true}).decode(buffer);}
    csvText=text;sourceName=file.name;
    $('source-label').textContent=file.name+' を読み込みました';
    $('source-description').textContent='この端末内で処理します。「更新対象を抽出」で結果を更新してください。';
    markDirty();
  }catch{showError('CSVを読み込めませんでした。UTF-8またはShift-JISで保存してください。');}
});
function resetSample(){
  if(!sampleResult||busy)return;
  csvText=sampleCsv;sourceName='sample';result=sampleResult;currentTab='targets';page=1;dirty=false;
  $('month').value='2026-11';$('lookahead').value='0';$('convention').value='civil';$('search').value='';$('am-filter').value='';$('csv-file').value='';
  $('source-label').textContent='架空の職員データ250名を読み込み済み';
  $('source-description').textContent='まずはそのまま抽出。条件を変えて結果の違いも確認できます。';
  $('result-state').textContent='保存済みサンプル結果';$('dirty').classList.add('hidden');clearError();
  tabs.forEach(tab=>tab.setAttribute('aria-selected',String(tab.dataset.tab==='targets')));
  renderResult();
}
$('reset').addEventListener('click',resetSample);
async function loadSample(){
  try{
    const responses=await Promise.all([fetch('./sample.csv'),fetch('./sample-result.json')]);
    if(responses.some(r=>!r.ok))throw new Error();
    [sampleCsv,sampleResult]=await Promise.all([responses[0].text(),responses[1].json()]);resetSample();
  }catch{showError('サンプルの読み込みに失敗しました。ページを再読み込みしてください。');}
}
loadSample();startEngine();
