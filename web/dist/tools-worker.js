/* Shared local Python runtime for the invoice and sales-list tools. */
let runtime;
let queue = Promise.resolve();
async function initialize() {
  if (!runtime) runtime = (async () => {
    importScripts('https://cdn.jsdelivr.net/pyodide/v0.27.7/full/pyodide.js');
    const py = await loadPyodide({indexURL:'https://cdn.jsdelivr.net/pyodide/v0.27.7/full/'});
    await py.loadPackage('micropip');
    py.globals.set('wheel_base',new URL('./wheels/',self.location.href).href);
    await py.runPythonAsync('import micropip\nawait micropip.install([wheel_base + "et_xmlfile-2.0.0-py3-none-any.whl", wheel_base + "openpyxl-3.1.5-py2.py3-none-any.whl"])');
    for(const name of ['invoice_core.py','leads_core.py','work_bridge.py']){
      const response=await fetch(new URL('./python/'+name,self.location.href));
      if(!response.ok)throw new Error('処理プログラムを読み込めませんでした。');
      py.FS.writeFile('/home/pyodide/'+name,await response.text());
    }
    py.runPython('import json\nfrom work_bridge import run_work');
    postMessage({status:'ready'});
    return py;
  })();
  return runtime;
}
self.onmessage=({data})=>{
  queue=queue.then(async()=>{
    try{
      const py=await initialize();
      if(data.action==='init')return;
      py.globals.set('work_json',JSON.stringify(data.payload));
      try{postMessage({id:data.id,result:JSON.parse(py.runPython('run_work(json.loads(work_json))'))});}
      finally{py.globals.delete('work_json');}
    }catch(error){postMessage({id:data.id,error:String(error.message||error)});}
  });
};
