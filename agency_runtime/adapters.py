"""Run the three existing processing engines without API keys or network calls."""
import base64
import importlib
import json
import sys
from pathlib import Path

from .core import AgencyError, write_json

ENGINES = Path(__file__).resolve().parents[1] / 'web' / 'dist' / 'python'


def process(tool, payload, output):
    if tool not in {'contract_extract', 'leads_clean', 'invoice_extract'}:
        raise AgencyError('No local adapter for ' + tool)
    sys.path.insert(0, str(ENGINES))
    if tool == 'contract_extract':
        result = json.loads(importlib.import_module('browser_bridge').run_request(payload))
        prefix = 'renewals'
    else:
        bridge = importlib.import_module('work_bridge')
        result = bridge.leads(payload) if tool == 'leads_clean' else bridge.invoices(payload, method='Supplied extracted text / OCR execution not verified')
        prefix = 'leads' if tool == 'leads_clean' else 'invoices'
    directory = Path(output).resolve()
    directory.mkdir(parents=True, exist_ok=True)
    files = []
    for extension, data in result.pop('files').items():
        filename = ('excluded.csv' if extension == 'excluded_csv' else prefix + '.' + extension)
        path = directory / filename
        path.write_bytes(base64.b64decode(data, validate=True))
        files.append(str(path))
    result['adapter'] = tool
    result['externalRequests'] = 0
    result['provenance'] = 'Supplied input; no search, PDF extraction or OCR performed by this adapter'
    result = json.loads(json.dumps(result, ensure_ascii=False, default=str))
    summary = directory / 'processing.json'
    write_json(summary, result)
    files.append(str(summary))
    return {'files': files, 'summary': result}


def run_assignment(ledger, assignment_id, payload):
    with ledger.transaction() as db:
        assignment, _ = ledger.active(db, assignment_id)
        if assignment['step']['role'] not in {'creator', 'research', 'sales'}:
            raise AgencyError('Processing adapter requires a production assignment')
        for artifact in assignment['inputArtifacts']:
            ledger.check_artifact(artifact)
    result = process(assignment['step']['capabilityId'], payload,
                     Path(assignment['outputDir']) / 'generated')
    artifacts = [ledger.artifact(assignment_id, path) for path in result['files']]
    # Review/finish is a separate Bot action. Processing is not proof of quality.
    return {'assignmentId': assignment_id, 'artifacts': artifacts, 'summary': result['summary']}
