/* Pinned Python runtime. Only program files and packages are fetched. */
let ready;
let queue = Promise.resolve();
function initialize() {
  if (!ready) ready = (async () => {
    postMessage({status: 'loading', message: '計算エンジンを準備しています…'});
    importScripts('https://cdn.jsdelivr.net/pyodide/v0.27.7/full/pyodide.js');
    const py = await loadPyodide({indexURL: 'https://cdn.jsdelivr.net/pyodide/v0.27.7/full/'});
    await py.loadPackage(['python-dateutil', 'micropip']);
    py.globals.set('wheel_base', new URL('./wheels/', self.location.href).href);
    await py.runPythonAsync('import micropip\nawait micropip.install([wheel_base + "et_xmlfile-2.0.0-py3-none-any.whl", wheel_base + "openpyxl-3.1.5-py2.py3-none-any.whl"])');
    for (const name of ['renewal.py', 'extract_renewals.py', 'browser_bridge.py']) {
      const response = await fetch('./python/' + name);
      if (!response.ok) throw new Error('計算プログラムを読み込めませんでした。');
      py.FS.writeFile('/home/pyodide/' + name, await response.text());
    }
    py.runPython('import json\nfrom browser_bridge import run_request');
    postMessage({status: 'ready'});
    return py;
  })();
  return ready;
}
self.onmessage = (event) => {
  const {id, payload, action} = event.data;
  queue = queue.then(async () => {
    try {
      const py = await initialize();
      if (action === 'init') return;
      py.globals.set('request_json', JSON.stringify(payload));
      const result = py.runPython('run_request(json.loads(request_json))', {globals: py.globals});
      py.globals.delete('request_json');
      postMessage({id, result: JSON.parse(result)});
    } catch (error) {
      postMessage({id, error: String(error.message || error)});
    }
  });
};
