export const root = new URL('.', import.meta.url);
export const $ = id => document.getElementById(id);
export function clearError(){ $('error').classList.add('hidden'); $('error').textContent=''; }
export function showError(message){ $('error').textContent=message; $('error').classList.remove('hidden'); }
export function progress(message){ $('progress').textContent=message; $('progress').classList.toggle('hidden',!message); }
export function cell(value){ const td=document.createElement('td');td.textContent=value??'—';return td; }
export function badge(text,kind=''){ const span=document.createElement('span');span.className='status '+kind;span.textContent=text;return span; }
export function download(base64,filename,type){
  const bytes=Uint8Array.from(atob(base64),c=>c.charCodeAt(0));
  const url=URL.createObjectURL(new Blob([bytes],{type}));
  const link=document.createElement('a');link.href=url;link.download=filename;document.body.append(link);link.click();link.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);
}
export function wireDownloads(getResult,stem){
  const types={xlsx:'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',csv:'text/csv;charset=utf-8',excluded_csv:'text/csv;charset=utf-8',json:'application/json'};
  document.querySelectorAll('[data-download]').forEach(button=>button.addEventListener('click',()=>{
    const result=getResult();const kind=button.dataset.download;if(!result?.files[kind])return;
    download(result.files[kind],stem+(kind==='excluded_csv'?'_excluded.csv':'.'+kind),types[kind]);
  }));
}
export function enableDownloads(enabled){document.querySelectorAll('[data-download]').forEach(button=>button.disabled=!enabled);}
export class Engine {
  constructor(onState){this.onState=onState;this.pending=new Map();this.id=0;this.start();}
  status(message,state){$('engine-status').textContent=message;$('engine-status').dataset.state=state;this.onState?.(state);}
  start(){
    this.worker?.terminate();clearTimeout(this.initTimer);this.ready=false;
    for(const pending of this.pending.values()){clearTimeout(pending.timer);pending.reject(new Error('実行環境を再読み込みしました。もう一度実行してください。'));}this.pending.clear();
    $('retry').classList.add('hidden');this.status('実行環境を準備中…初回は少し時間がかかります','loading');
    this.worker=new Worker(new URL('tools-worker.js',root));
    this.initTimer=setTimeout(()=>this.fail('実行環境の読み込みがタイムアウトしました。再読み込みしてください。'),90000);
    this.worker.onerror=()=>this.fail('実行環境を読み込めませんでした。通信を確認して再読み込みしてください。');
    this.worker.onmessage=({data})=>{
      if(data.status==='ready'){clearTimeout(this.initTimer);this.ready=true;this.status('実行準備完了 · 入力データはこの端末内で処理します','ready');return;}
      if(data.id===undefined&&data.error){this.fail('実行環境を読み込めませんでした。再読み込みしてください。');return;}
      const pending=this.pending.get(data.id);if(!pending)return;clearTimeout(pending.timer);this.pending.delete(data.id);
      if(data.error){const match=data.error.match(/ValueError: ([^\n]+)/);pending.reject(new Error(match?match[1]:'処理できませんでした。入力内容を確認してください。'));}
      else pending.resolve(data.result);
    };
    this.worker.postMessage({action:'init'});
  }
  fail(message){this.ready=false;clearTimeout(this.initTimer);this.worker?.terminate();this.status(message,'failed');$('retry').classList.remove('hidden');for(const p of this.pending.values()){clearTimeout(p.timer);p.reject(new Error(message));}this.pending.clear();}
  request(payload){
    if(!this.ready)return Promise.reject(new Error('実行環境の準備が完了するまでお待ちください。'));
    const id=++this.id;
    return new Promise((resolve,reject)=>{const timer=setTimeout(()=>this.fail('処理がタイムアウトしました。再読み込みして入力件数を減らしてください。'),60000);this.pending.set(id,{resolve,reject,timer});this.worker.postMessage({id,payload});});
  }
}
