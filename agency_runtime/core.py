"""Durable work ledger. Grok Bot owns messaging, reasoning and scheduling."""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import sqlite3
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

SPEC = Path(__file__).resolve().parents[1] / 'docs' / 'agentic-agency'
ROLE_BOTS = {'coordinator': 'フウ', 'sales': 'リサーチ担当', 'research': 'リサーチ担当',
             'creator': 'コード担当', 'qa': 'Agency QA', 'delivery': 'Agency Delivery'}
TERMINAL = {'completed', 'cancelled'}


class AgencyError(ValueError):
    pass


def now():
    return datetime.now(timezone.utc).isoformat()


def dump(value):
    return json.dumps(value, ensure_ascii=False, indent=2)


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + '.' + uuid.uuid4().hex + '.tmp')
    try:
        temp.write_text(dump(value), encoding='utf-8')
        os.replace(temp, path)
    finally:
        if temp.exists():
            temp.unlink()


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def validate(value, name):
    schema = json.loads((SPEC / 'contracts.schema.json').read_text(encoding='utf-8'))
    Draft202012Validator({'$schema': schema['$schema'], '$ref': '#/$defs/' + name,
                         '$defs': schema['$defs']}, format_checker=FormatChecker()).validate(value)


@contextmanager
def workspace_lock(root):
    root.mkdir(parents=True, exist_ok=True)
    with (root / '.lock').open('a+b') as lock:
        deadline = time.monotonic() + 10
        while True:
            lock.seek(0)
            try:
                if os.name == 'nt':
                    import msvcrt
                    msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except OSError:
                if time.monotonic() > deadline:
                    raise AgencyError('Workspace busy; retry without creating another assignment')
                time.sleep(.05)
        try:
            yield
        finally:
            lock.seek(0)
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)


class Ledger:
    def __init__(self, root):
        self.root = Path(root).resolve()

    @contextmanager
    def transaction(self):
        with workspace_lock(self.root):
            db = sqlite3.connect(self.root / 'ledger.sqlite3')
            db.row_factory = sqlite3.Row
            db.execute('PRAGMA busy_timeout=10000')
            db.execute('CREATE TABLE IF NOT EXISTS records(kind TEXT, id TEXT, body TEXT NOT NULL, PRIMARY KEY(kind,id))')
            db.execute('CREATE TABLE IF NOT EXISTS events(sequence INTEGER PRIMARY KEY AUTOINCREMENT, job_id TEXT, body TEXT NOT NULL)')
            db.execute('BEGIN IMMEDIATE')
            try:
                yield db
                db.commit()
                self.export(db)
            except BaseException:
                db.rollback()
                raise
            finally:
                db.close()

    @staticmethod
    def get(db, kind, ident):
        row = db.execute('SELECT body FROM records WHERE kind=? AND id=?', (kind, ident)).fetchone()
        if row is None:
            raise AgencyError(f'{kind} not found: {ident}')
        return json.loads(row['body'])

    @staticmethod
    def all(db, kind):
        return [json.loads(r['body']) for r in db.execute('SELECT body FROM records WHERE kind=? ORDER BY id', (kind,))]

    @staticmethod
    def put(db, kind, ident, value):
        db.execute('INSERT INTO records VALUES(?,?,?) ON CONFLICT(kind,id) DO UPDATE SET body=excluded.body', (kind, ident, dump(value)))

    def event(self, db, job, typ, payload):
        db.execute('INSERT INTO events(job_id,body) VALUES(?,?)', (job, dump({'type': typ, 'at': now(), 'payload': payload})))

    def save_job(self, db, job):
        job['version'] += 1
        job['updatedAt'] = now()
        self.put(db, 'job', job['jobId'], job)

    def export(self, db):
        """Rebuild inspectable files from the committed ledger after restart too."""
        for config in self.all(db, 'config'):
            write_json(self.root / 'config' / (config['id'] + '.json'), config['value'])
        jobs = self.all(db, 'job')
        for job in jobs:
            directory = self.root / 'jobs' / job['jobId']
            write_json(directory / 'state.json', job)
            write_json(directory / 'brief.json', job['brief'])
            if job.get('plan'):
                write_json(directory / 'plan.json', job['plan'])
            rows = db.execute('SELECT sequence,body FROM events WHERE job_id=? ORDER BY sequence', (job['jobId'],))
            lines = [json.dumps({'sequence': r['sequence'], **json.loads(r['body'])}, ensure_ascii=False) for r in rows]
            (directory / 'events.jsonl').write_text('\n'.join(lines) + '\n', encoding='utf-8')
        for item in self.all(db, 'assignment'):
            write_json(Path(item['assignmentFile']), item)
            for kind, filename in [('artifact', 'artifacts.json'), ('source', 'sources.json')]:
                refs = [v for v in self.all(db, kind) if v['assignmentId'] == item['assignmentId']]
                write_json(Path(item['outputDir']) / filename, refs)
        for result in self.all(db, 'result'):
            assignment = self.get(db, 'assignment', result['assignmentId'])
            write_json(Path(assignment['outputDir']) / 'result.json', result['result'])
        write_json(self.root / 'opportunities' / 'index.json', self.all(db, 'opportunity'))
        board = ['# Agentic Agency / Work board', '', '| Job | Title | Mode | Status | Stage |', '|---|---|---|---|---|']
        for job in jobs:
            title = job['brief']['title'].replace('|', '/').replace('\n', ' ')
            board.append(f"| {job['jobId']} | {title} | {job['mode']} | {job['status']} | {job['stage']} |")
        (self.root / 'board.md').write_text('\n'.join(board) + '\n', encoding='utf-8')

    def init(self):
        if not (self.root / 'ledger.sqlite3').exists() and any((self.root / name).exists() for name in ['jobs', 'config']):
            raise AgencyError('Existing unmanaged workspace detected. Choose a fresh --root; preserve previous Bot work.')
        with self.transaction() as db:
            defaults = {
                'company-policy': json.loads((SPEC / 'company-policy.example.json').read_text(encoding='utf-8')),
                'bot-registry': {'roles': ROLE_BOTS},
                'connections': {'connections': []},
                'capabilities': {c['id']: {'readiness': 'unverified', 'evidence': None} for c in json.loads((SPEC / 'capabilities.json').read_text(encoding='utf-8'))['capabilities']},
            }
            for key, value in defaults.items():
                if db.execute('SELECT 1 FROM records WHERE kind="config" AND id=?', (key,)).fetchone() is None:
                    self.put(db, 'config', key, {'id': key, 'value': value})
        return {'root': str(self.root), 'board': str(self.root / 'board.md')}

    def configure_capability(self, ident, readiness, evidence):
        if readiness not in {'ready', 'unverified', 'needs_connection', 'unavailable'}:
            raise AgencyError('Invalid readiness')
        if readiness == 'ready' and not evidence.strip():
            raise AgencyError('A successful check must be recorded before enabling')
        with self.transaction() as db:
            config = self.get(db, 'config', 'capabilities')
            if ident not in config['value']:
                raise AgencyError('Unknown capability')
            config['value'][ident] = {'readiness': readiness, 'evidence': evidence, 'checkedAt': now()}
            self.put(db, 'config', config['id'], config)
        return config['value'][ident]

    def register_bot(self, role, name):
        if role not in ROLE_BOTS or not name.strip():
            raise AgencyError('Known role and existing Bot name required')
        with self.transaction() as db:
            config = self.get(db, 'config', 'bot-registry')
            config['value']['roles'][role] = name
            self.put(db, 'config', config['id'], config)
        return config['value']

    def opportunity(self, key, title, url, evidence):
        from urllib.parse import urlparse
        if not all(v.strip() for v in (key, title, evidence)) or urlparse(url).scheme not in {'http', 'https'} or not urlparse(url).hostname:
            raise AgencyError('Opportunity needs a stable key, title, source URL and inspected evidence')
        with self.transaction() as db:
            item = {'id': key, 'title': title, 'url': url, 'evidence': evidence,
                    'updatedAt': now(), 'status': 'candidate', 'verification': 'recorded_by_bot'}
            self.put(db, 'opportunity', key, item)
        return item

    def import_input(self, ident, source_path):
        source = Path(source_path).resolve()
        if not source.is_file() or source.stat().st_size > 100 * 1024 * 1024:
            raise AgencyError('Input must be a file under 100MB')
        with self.transaction() as db:
            job = self.get(db, 'job', ident)
            if job['status'] != 'draft':
                raise AgencyError('Import inputs before installing a plan')
            content_hash = sha(source)
            same = [a for a in self.all(db, 'artifact') if a['jobId'] == ident and a['assignmentId'] is None and a['sha256'] == content_hash and a['name'] == source.name]
            if same:
                return same[0]
            aid = str(uuid.uuid4())
            dest = self.root / 'jobs' / ident / 'inputs' / aid / source.name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, dest)
            if sha(dest) != content_hash:
                raise AgencyError('Input changed during copy')
            item = {'id': aid, 'jobId': ident, 'assignmentId': None, 'name': source.name,
                    'path': str(dest), 'relativePath': str(dest.relative_to(self.root)),
                    'sha256': content_hash, 'version': 1, 'mode': job['mode'], 'createdAt': now()}
            self.put(db, 'artifact', aid, item)
            job['brief']['inputArtifactIds'].append(aid)
            self.save_job(db, job)
        return item

    def create(self, brief, mode, request_key):
        validate(brief, 'JobBrief')
        if mode not in {'sample', 'live'} or not request_key.strip():
            raise AgencyError('mode and request key required')
        payload_hash = hashlib.sha256(dump({'brief': brief, 'mode': mode}).encode()).hexdigest()
        with self.transaction() as db:
            existing = db.execute('SELECT body FROM records WHERE kind="request" AND id=?', (request_key,)).fetchone()
            if existing:
                request = json.loads(existing['body'])
                if request['hash'] != payload_hash:
                    raise AgencyError('Request key already used for different input')
                return self.get(db, 'job', request['jobId'])
            if brief['inputArtifactIds']:
                raise AgencyError('Initial version accepts local inputs via input-import, not unknown artifact IDs')
            ident = str(uuid.uuid4())
            job = {'jobId': ident, 'mode': mode, 'brief': brief, 'status': 'draft', 'stage': 'scope',
                   'version': 1, 'createdAt': now(), 'updatedAt': now(), 'activeAssignmentId': None,
                   'completedAssignmentIds': [], 'plan': None, 'steps': {}, 'blockers': [], 'revisions': 0}
            self.put(db, 'job', ident, job)
            self.put(db, 'request', request_key, {'jobId': ident, 'hash': payload_hash})
            self.event(db, ident, 'JOB_CREATED', {'mode': mode})
        return job

    def set_plan(self, ident, plan):
        validate(plan, 'Plan')
        if plan['jobId'] != ident:
            raise AgencyError('Plan belongs to another job')
        ids = [s['id'] for s in plan['steps']]
        if len(set(ids)) != len(ids) or not ids:
            raise AgencyError('A plan needs unique steps; collect missing input before installing it')
        nodes = {s['id']: s for s in plan['steps']}
        done = set()
        while len(done) < len(ids):
            ready = {i for i, s in nodes.items() if i not in done and set(s['dependsOn']) <= done}
            if not ready:
                raise AgencyError('Plan has missing dependencies or a cycle')
            done |= ready
        if any(q['blocking'] for q in plan['questions']):
            raise AgencyError('Answer blocking questions before installing the plan')
        if not any(s['role'] == 'qa' for s in plan['steps']):
            raise AgencyError('Plan must include QA')
        qa_ids = {s['id'] for s in plan['steps'] if s['role'] == 'qa'}
        for step in plan['steps']:
            if step['role'] == 'delivery' and not qa_ids.intersection(step['dependsOn']):
                raise AgencyError('Delivery must depend on QA')
        with self.transaction() as db:
            job = self.get(db, 'job', ident)
            if job['status'] != 'draft':
                raise AgencyError('Plan is immutable after work begins')
            caps = self.get(db, 'config', 'capabilities')['value']
            if any(s['capabilityId'] not in caps for s in plan['steps']):
                raise AgencyError('Unknown capability')
            for step in plan['steps']:
                for aid in step['inputArtifactIds']:
                    item = self.get(db, 'artifact', aid)
                    if item['jobId'] != ident:
                        raise AgencyError('Cross-job input rejected')
                    self.check_artifact(item)
            # Every production step must precede a QA gate, never bypass it.
            def ancestors(i):
                result = set(nodes[i]['dependsOn'])
                for dep in list(result):
                    result |= ancestors(dep)
                return result
            reviewed = set().union(*(ancestors(i) for i in qa_ids))
            if any(s['role'] in {'creator', 'research', 'sales'} and s['id'] not in reviewed for s in plan['steps']):
                raise AgencyError('Every production step must feed a QA step')
            job.update(plan=plan, status='queued', steps={i: {'status': 'pending', 'attempt': 0} for i in ids})
            self.save_job(db, job)
            self.event(db, ident, 'PLAN_INSTALLED', {'steps': ids})
        return job

    def next_assignment(self, ident):
        with self.transaction() as db:
            job = self.get(db, 'job', ident)
            if job['status'] in TERMINAL | {'paused', 'draft', 'blocked', 'ready_for_review', 'waiting_input', 'waiting_approval'}:
                raise AgencyError('Job cannot dispatch in state ' + job['status'])
            if job['activeAssignmentId']:
                return self.get(db, 'assignment', job['activeAssignmentId'])
            if any(j['activeAssignmentId'] for j in self.all(db, 'job') if j['jobId'] != ident):
                raise AgencyError('Another job already has an active assignment')
            nodes = job['plan']['steps']
            candidates = [s for s in nodes if job['steps'][s['id']]['status'] == 'pending' and
                          all(job['steps'][d]['status'] == 'succeeded' for d in s['dependsOn'])]
            if not candidates:
                raise AgencyError('No dispatchable step')
            step = candidates[0]
            cap = self.get(db, 'config', 'capabilities')['value'][step['capabilityId']]
            if cap['readiness'] != 'ready':
                job.update(status='waiting_connection', blockers=[f"{step['capabilityId']}: {cap['readiness']}"])
                self.save_job(db, job)
                return {'status': job['status'], 'blockers': job['blockers']}
            history = [a for a in self.all(db, 'assignment') if a['jobId'] == ident]
            if len(history) >= 20:
                job.update(status='blocked', blockers=['Maximum 20 assignments reached'])
                self.save_job(db, job)
                return {'status': 'blocked', 'blockers': job['blockers']}
            progress = job['steps'][step['id']]
            progress['attempt'] += 1
            progress['status'] = 'running'
            assignment_id = f"{ident}_{step['id']}_attempt_{progress['attempt']}"
            directory = self.root / 'jobs' / ident
            output = directory / 'steps' / step['id'] / f"attempt-{progress['attempt']}"
            output.mkdir(parents=True, exist_ok=True)
            assignment = {'type': 'ASSIGN', 'jobId': ident, 'assignmentId': assignment_id,
                          'stepId': step['id'], 'attempt': progress['attempt'], 'ownerBot': self.get(db, 'config', 'bot-registry')['value']['roles'][step['role']],
                          'mode': job['mode'], 'step': step, 'briefFile': str(directory / 'brief.json'),
                          'assignmentFile': str(directory / 'assignments' / (assignment_id + '.json')),
                          'outputDir': str(output), 'returnTo': self.get(db, 'config', 'bot-registry')['value']['roles']['coordinator']}
            dependency_artifacts = self.current_artifacts(db, job)
            upstream = set(step['dependsOn'])
            while True:
                expanded = upstream | {d for s in nodes if s['id'] in upstream for d in s['dependsOn']}
                if expanded == upstream:
                    break
                upstream = expanded
            upstream_assignments = {a['assignmentId'] for a in self.all(db, 'assignment') if a['jobId'] == ident and a['stepId'] in upstream and a['attempt'] == job['steps'][a['stepId']]['attempt']}
            assignment['inputArtifacts'] = [a for a in self.all(db, 'artifact') if a['id'] in step['inputArtifactIds'] or a['id'] in job['brief']['inputArtifactIds'] or (a['assignmentId'] in upstream_assignments and a in dependency_artifacts)]
            for item in assignment['inputArtifacts']:
                self.check_artifact(item)
            assignment['requiredCheckIds'] = ['criterion_' + str(i + 1) for i in range(len(step['acceptanceCriteria']))]
            if step['role'] == 'qa':
                assignment['requiredCheckIds'] += ['job_criterion_' + str(i + 1) for i in range(len(job['brief']['acceptanceCriteria']))]
            self.put(db, 'assignment', assignment_id, assignment)
            job.update(status='running', stage=step['role'], activeAssignmentId=assignment_id, blockers=[])
            self.save_job(db, job)
            self.event(db, ident, 'ASSIGN', {'assignmentId': assignment_id, 'ownerBot': assignment['ownerBot']})
        return assignment

    def active(self, db, assignment_id):
        assignment = self.get(db, 'assignment', assignment_id)
        job = self.get(db, 'job', assignment['jobId'])
        if job['activeAssignmentId'] != assignment_id or job['status'] in TERMINAL:
            raise AgencyError('Stale or cancelled assignment')
        return assignment, job

    def artifact(self, assignment_id, source_path, name=None):
        source = Path(source_path).resolve()
        if not source.is_file() or source.stat().st_size > 100 * 1024 * 1024:
            raise AgencyError('Artifact must be a file under 100MB')
        name = name or source.name
        if name in {'.', '..'} or Path(name).name != name or '/' in name or '\\' in name:
            raise AgencyError('Artifact name must be a basename')
        content_hash = sha(source)
        with self.transaction() as db:
            assignment, job = self.active(db, assignment_id)
            artifacts = self.all(db, 'artifact')
            same = [a for a in artifacts if a['assignmentId'] == assignment_id and a['name'] == name]
            if same:
                if same[0]['sha256'] != content_hash:
                    raise AgencyError('Artifact already registered; create a new attempt for changes')
                return same[0]
            aid = str(uuid.uuid4())
            dest = Path(assignment['outputDir']) / 'files' / aid / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, dest)
            if sha(dest) != content_hash:
                raise AgencyError('Artifact changed during copy')
            artifact = {'id': aid, 'jobId': job['jobId'], 'assignmentId': assignment_id, 'name': name,
                        'path': str(dest), 'relativePath': str(dest.relative_to(self.root)), 'sha256': content_hash,
                        'version': assignment['attempt'], 'mode': job['mode'], 'createdAt': now()}
            self.put(db, 'artifact', aid, artifact)
        return artifact

    def source(self, assignment_id, url, title, excerpt):
        from urllib.parse import urlparse
        if urlparse(url).scheme not in {'http', 'https'} or not urlparse(url).hostname:
            raise AgencyError('Source URL must be HTTP(S)')
        if not title.strip() or not excerpt.strip():
            raise AgencyError('Record the title and inspected passage, not just a URL')
        with self.transaction() as db:
            _, job = self.active(db, assignment_id)
            same = [s for s in self.all(db, 'source') if s['assignmentId'] == assignment_id and s['url'] == url]
            if same:
                return same[0]
            source = {'id': str(uuid.uuid4()), 'jobId': job['jobId'], 'assignmentId': assignment_id,
                      'url': url, 'title': title, 'excerpt': excerpt, 'retrievedAt': now(), 'mode': job['mode'],
                      'verification': 'recorded_by_bot_not_independently_verified'}
            self.put(db, 'source', source['id'], source)
        return source

    def check_artifact(self, artifact):
        path = Path(artifact['path']).resolve()
        if not path.is_relative_to(self.root) or not path.is_file() or sha(path) != artifact['sha256']:
            raise AgencyError('Missing or changed artifact: ' + artifact['name'])

    def finish(self, assignment_id, result):
        validate(result, 'StepResult')
        with self.transaction() as db:
            prior = db.execute('SELECT body FROM records WHERE kind="result" AND id=?', (assignment_id,)).fetchone()
            if prior:
                saved = json.loads(prior['body'])
                if saved['result'] != result:
                    raise AgencyError('Different result for completed assignment')
                return self.get(db, 'job', saved['jobId'])
            assignment, job = self.active(db, assignment_id)
            if result['stepId'] != assignment['stepId']:
                raise AgencyError('Wrong result step')
            for kind, field in [('artifact', 'artifactIds'), ('source', 'sourceIds')]:
                for ref in result[field]:
                    record = self.get(db, kind, ref)
                    if record['jobId'] != job['jobId']:
                        raise AgencyError('Cross-job reference rejected')
                    if kind == 'artifact':
                        self.check_artifact(record)
                        if record['assignmentId'] not in {assignment_id, None} and record['id'] not in {a['id'] for a in assignment['inputArtifacts']}:
                            raise AgencyError('Stale artifact reference rejected')
            for check in result['checks']:
                if check.get('artifactId') and check['artifactId'] not in result['artifactIds']:
                    raise AgencyError('Check artifact must be included in result')
            if result['outcome'] == 'succeeded':
                checks = {c['id']: c for c in result['checks']}
                if len(checks) != len(result['checks']) or any(c['status'] != 'PASS' for c in result['checks']):
                    raise AgencyError('Success requires unique, passing checks')
                if not set(assignment['requiredCheckIds']) <= checks.keys():
                    raise AgencyError('Success must cover every acceptance criterion')
                role = assignment['step']['role']
                if role in {'creator', 'research', 'sales', 'delivery'} and not any(self.get(db, 'artifact', i)['assignmentId'] == assignment_id for i in result['artifactIds']):
                    raise AgencyError('Production must return an actual artifact')
                if role == 'qa' and (not result['checks'] or any(c['status'] != 'PASS' for c in result['checks'])):
                    raise AgencyError('QA success requires all checks to pass')
                if role == 'qa':
                    inputs = {a['id'] for a in assignment['inputArtifacts'] if a['assignmentId'] is not None}
                    checked = {c.get('artifactId') for c in result['checks']}
                    if not inputs or not inputs <= checked:
                        raise AgencyError('QA must inspect each current upstream artifact and bind evidence to its ID')
                    for item in assignment['inputArtifacts']:
                        self.check_artifact(item)
            self.put(db, 'result', assignment_id, {'jobId': job['jobId'], 'assignmentId': assignment_id, 'result': result})
            job['activeAssignmentId'] = None
            job['completedAssignmentIds'].append(assignment_id)
            progress = job['steps'][assignment['stepId']]
            if result['outcome'] == 'succeeded':
                progress['status'] = 'succeeded'
                job['status'] = 'ready_for_review' if all(s['status'] == 'succeeded' for s in job['steps'].values()) else 'queued'
                job['blockers'] = []
            else:
                progress['status'] = 'failed'
                job.update(status='blocked', blockers=result['blockers'] or [result['summary']])
            # A pause stops subsequent work even if the active worker finishes.
            prior_job = self.get(db, 'job', job['jobId'])
            if prior_job['status'] == 'paused':
                job['resumeStatus'] = job['status']
                job['status'] = 'paused'
            self.save_job(db, job)
            self.event(db, job['jobId'], 'RESULT', {'assignmentId': assignment_id, 'outcome': result['outcome']})
        return job

    def revise(self, ident, step_id, reason):
        with self.transaction() as db:
            job = self.get(db, 'job', ident)
            if job['activeAssignmentId'] or job['status'] != 'blocked' or job['revisions'] >= 2:
                raise AgencyError('Revision unavailable; stop active work or check the revision limit')
            nodes = {s['id']: s for s in job['plan']['steps']}
            if step_id not in nodes or not reason.strip():
                raise AgencyError('Known step and revision reason required')
            invalidated = {step_id}
            while True:
                expanded = invalidated | {i for i, s in nodes.items() if set(s['dependsOn']) & invalidated}
                if expanded == invalidated:
                    break
                invalidated = expanded
            for i in invalidated:
                job['steps'][i]['status'] = 'pending'
            job.update(status='queued', blockers=[], revisions=job['revisions'] + 1)
            self.save_job(db, job)
            self.event(db, ident, 'REVISE', {'steps': sorted(invalidated), 'reason': reason})
        return job

    def control(self, ident, action):
        with self.transaction() as db:
            job = self.get(db, 'job', ident)
            if job['status'] in TERMINAL:
                raise AgencyError('Job is terminal')
            if action == 'pause':
                if job['status'] != 'paused':
                    job['resumeStatus'] = job['status']
                job['status'] = 'paused'
            elif action == 'resume' and job['status'] in {'paused', 'waiting_connection'}:
                job['status'] = job.pop('resumeStatus', 'queued') if job['status'] == 'paused' else 'queued'
            elif action == 'cancel':
                job.update(status='cancelled', activeAssignmentId=None)
            else:
                raise AgencyError('Invalid control transition')
            self.save_job(db, job)
            self.event(db, ident, action.upper(), {})
        return job

    def show(self, ident=None):
        with self.transaction() as db:
            return self.get(db, 'job', ident) if ident else self.all(db, 'job')

    def accept(self, ident):
        with self.transaction() as db:
            job = self.get(db, 'job', ident)
            if job['status'] != 'ready_for_review':
                raise AgencyError('Job is not ready for review')
            for artifact in self.current_artifacts(db, job):
                self.check_artifact(artifact)
            job['status'] = 'completed'
            self.save_job(db, job)
            self.event(db, ident, 'ACCEPTED_BY_USER', {})
        return job

    def current_artifacts(self, db, job):
        latest = {a['assignmentId'] for a in self.all(db, 'assignment') if a['jobId'] == job['jobId'] and
                  a['attempt'] == job['steps'][a['stepId']]['attempt'] and job['steps'][a['stepId']]['status'] == 'succeeded'}
        return [a for a in self.all(db, 'artifact') if a['assignmentId'] in latest]

    def package(self, assignment_id):
        with self.transaction() as db:
            assignment, job = self.active(db, assignment_id)
            if assignment['step']['role'] != 'delivery':
                raise AgencyError('Package belongs to delivery')
            artifacts = self.current_artifacts(db, job)
            if not artifacts:
                raise AgencyError('No completed artifacts')
            for artifact in artifacts:
                self.check_artifact(artifact)
            directory = Path(assignment['outputDir']) / 'package'
            directory.mkdir(exist_ok=True)
            for artifact in artifacts:
                dest = directory / artifact['id'] / artifact['name']
                dest.parent.mkdir(exist_ok=True)
                shutil.copyfile(artifact['path'], dest)
            write_json(directory / 'manifest.json', artifacts)
            body = ['# ' + job['brief']['title'], '', 'Mode: ' + job['mode'],
                    'Status: delivery prepared; external delivery has not been performed.', '']
            body += [f"- {a['name']} / version {a['version']} / SHA256 {a['sha256']}" for a in artifacts]
            (directory / 'delivery.md').write_text('\n'.join(body), encoding='utf-8')
        return {'directory': str(directory), 'deliveryFile': str(directory / 'delivery.md'), 'manifestFile': str(directory / 'manifest.json')}
