"""Shared-computer CLI called by native Grok Bots; stdout is structured JSON."""
import argparse
import json
import os
import sys
import zipfile
from pathlib import Path

from jsonschema import ValidationError

from .core import AgencyError, Ledger, SPEC, dump


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', default=os.environ.get('AGENCY_ROOT', '/workspace/agentic-agency'))
    commands = p.add_subparsers(dest='command', required=True)
    commands.add_parser('init')
    s = commands.add_parser('create'); s.add_argument('--brief', required=True); s.add_argument('--mode', choices=['sample', 'live'], required=True); s.add_argument('--request-key', required=True)
    s = commands.add_parser('plan'); s.add_argument('job'); s.add_argument('--file', required=True)
    for name in ['next', 'accept', 'pause', 'resume', 'cancel']:
        commands.add_parser(name).add_argument('job')
    s = commands.add_parser('show'); s.add_argument('job', nargs='?')
    s = commands.add_parser('input-import'); s.add_argument('job'); s.add_argument('--file', required=True)
    s = commands.add_parser('artifact'); s.add_argument('assignment'); s.add_argument('--file', required=True); s.add_argument('--name')
    s = commands.add_parser('source'); s.add_argument('assignment'); s.add_argument('--url', required=True); s.add_argument('--title', required=True); s.add_argument('--excerpt-file', required=True)
    s = commands.add_parser('finish'); s.add_argument('assignment'); s.add_argument('--result', required=True)
    s = commands.add_parser('revise'); s.add_argument('job'); s.add_argument('--step', required=True); s.add_argument('--reason', required=True)
    s = commands.add_parser('capability'); s.add_argument('id'); s.add_argument('--readiness', required=True, choices=['ready', 'unverified', 'needs_connection', 'unavailable']); s.add_argument('--evidence', default='')
    s = commands.add_parser('bot'); s.add_argument('role'); s.add_argument('--name', required=True)
    s = commands.add_parser('opportunity'); s.add_argument('--key', required=True); s.add_argument('--title', required=True); s.add_argument('--url', required=True); s.add_argument('--evidence-file', required=True)
    s = commands.add_parser('run'); s.add_argument('assignment'); s.add_argument('--payload', required=True)
    s = commands.add_parser('package'); s.add_argument('assignment')
    s = commands.add_parser('inspect'); s.add_argument('assignment')
    s = commands.add_parser('bootstrap'); s.add_argument('--kit-out', required=True)
    return p


def execute(args):
    ledger = Ledger(args.root)
    c = args.command
    if c == 'init': return ledger.init()
    if c == 'create': return ledger.create(read(args.brief), args.mode, args.request_key)
    if c == 'plan': return ledger.set_plan(args.job, read(args.file))
    if c == 'next': return ledger.next_assignment(args.job)
    if c == 'show': return ledger.show(args.job)
    if c == 'input-import': return ledger.import_input(args.job, args.file)
    if c == 'artifact': return ledger.artifact(args.assignment, args.file, args.name)
    if c == 'source': return ledger.source(args.assignment, args.url, args.title, Path(args.excerpt_file).read_text(encoding='utf-8-sig'))
    if c == 'finish': return ledger.finish(args.assignment, read(args.result))
    if c == 'revise': return ledger.revise(args.job, args.step, args.reason)
    if c in {'pause', 'resume', 'cancel'}: return ledger.control(args.job, c)
    if c == 'accept': return ledger.accept(args.job)
    if c == 'capability': return ledger.configure_capability(args.id, args.readiness, args.evidence)
    if c == 'bot': return ledger.register_bot(args.role, args.name)
    if c == 'opportunity': return ledger.opportunity(args.key, args.title, args.url, Path(args.evidence_file).read_text(encoding='utf-8-sig'))
    if c == 'run':
        from .adapters import run_assignment
        return run_assignment(ledger, args.assignment, read(args.payload))
    if c == 'package':
        package = ledger.package(args.assignment)
        path = Path(package['directory']).parent / 'delivery.zip'
        with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as archive:
            for file in sorted(Path(package['directory']).rglob('*')):
                if file.is_file(): archive.write(file, file.relative_to(package['directory']))
        return {**package, 'artifact': ledger.artifact(args.assignment, path)}
    if c == 'inspect':
        with ledger.transaction() as db:
            assignment, job = ledger.active(db, args.assignment)
            items = assignment['inputArtifacts'] + [a for a in ledger.all(db, 'artifact') if a['assignmentId'] == args.assignment]
            for item in items: ledger.check_artifact(item)
            return {'assignment': assignment, 'artifacts': items, 'job': job,
                    'checks': [{'artifactId': a['id'], 'sha256': a['sha256'], 'status': 'PASS'} for a in items],
                    'note': 'Integrity only. Bot must inspect content against each criterion.'}
    if c == 'bootstrap':
        import shutil
        directory = Path(args.kit_out).resolve()
        source = SPEC / 'grok-kit'
        directory.mkdir(parents=True, exist_ok=True)
        for file in source.rglob('*'):
            if file.is_file():
                dest = directory / file.relative_to(source)
                dest.parent.mkdir(parents=True, exist_ok=True)
                if dest.exists() and dest.read_bytes() != file.read_bytes():
                    raise AgencyError('Kit file already changed: ' + str(dest))
                shutil.copyfile(file, dest)
        return {**ledger.init(), 'kit': str(directory), 'nativeBotRegistration': 'required in Grok Bot'}
    raise AgencyError('Unknown command')


def main():
    try:
        result = execute(parser().parse_args())
        print(dump({'ok': True, 'data': result}))
    except (AgencyError, ValidationError, ValueError, OSError) as error:
        print(dump({'ok': False, 'error': str(error)}), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
