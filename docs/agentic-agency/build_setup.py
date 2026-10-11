"""Refresh the single attachment for Grok from maintained source documents."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FILES = ['START-HERE.md', 'README.md', 'architecture.md', 'agent-instructions.md',
         'connections.md', 'implementation-backlog.md', 'contracts.schema.json',
         'capabilities.json', 'company-policy.example.json', 'example-job.json', 'runtime-status.md']


def build():
    body = ['# Agentic Agency / Grok Bot setup package', '',
            'Generated from maintained repo files. Runtime code must be obtained from the repo.',
            'Bot registration and runtime evidence are recorded separately in runtime-status.md.', '']
    paths = [ROOT / name for name in FILES] + [ROOT.parents[1] / 'agency_runtime/README.md']
    paths += sorted((ROOT / 'grok-kit').glob('*/SKILL.md'))
    for path in paths:
        body += ['\n---\n', '# File: ' + path.relative_to(ROOT.parents[1]).as_posix(), '', path.read_text(encoding='utf-8')]
    (ROOT / 'GROK-SETUP.md').write_text('\n'.join(body), encoding='utf-8')


if __name__ == '__main__':
    build()
