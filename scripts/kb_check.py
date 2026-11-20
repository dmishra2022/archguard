#!/usr/bin/env python3
"""Check (or refresh) the graphify code graph in docs/kb against the current sources.

Usage:
  python3 scripts/kb_check.py            # exit 1 when docs/kb/graphify-out/graph.json is stale
  python3 scripts/kb_check.py --update   # regenerate graph.json, GRAPH_REPORT.md and graph.html

The graph is built from the files git tracks or would track (untracked, ignored output such as
node_modules or reports never leaks in), with the graphify version recorded in the committed graph,
so the result is identical on every machine. `built_at_commit` is ignored by the comparison.
"""
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KB = ROOT / 'docs' / 'kb'
GRAPH = KB / 'graphify-out' / 'graph.json'
COMMITTED = ('graph.json', 'GRAPH_REPORT.md', 'graph.html', '.graphify_analysis.json')


def graphify(*args, cwd=None):
    result = subprocess.run(['graphify', *args], cwd=cwd, capture_output=True, text=True)
    if result.returncode:
        sys.exit(f'graphify {" ".join(args)} failed:\n{result.stdout}{result.stderr}')


def installed_version():
    try:
        out = subprocess.run(['graphify', '--version'], capture_output=True, text=True).stdout
    except FileNotFoundError:
        sys.exit('graphify is not installed: uv tool install graphifyy (or pipx install graphifyy)')
    return out.strip().split()[-1].lstrip('v') if out.strip() else ''


def export_sources(target):
    files = subprocess.run(['git', 'ls-files', '--cached', '--others', '--exclude-standard', '-z'],
                           cwd=ROOT, capture_output=True, check=True).stdout.decode().split('\0')
    output = GRAPH.parent.relative_to(ROOT).as_posix() + '/'
    for name in filter(None, files):
        if name.startswith(output):
            continue
        source = ROOT / name
        if source.is_file():
            (target / name).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target / name)
    shutil.copy2(ROOT / '.graphifyignore', target / '.graphifyignore')


def build(work):
    sources = work / 'src'
    sources.mkdir()
    export_sources(sources)
    graphify('extract', '.', '--code-only', '--out', 'docs/kb', cwd=sources)
    graphify('cluster-only', 'docs/kb', '--no-label', cwd=sources)
    return sources / 'docs' / 'kb' / 'graphify-out'


def comparable(path):
    """The graph's structure: nodes and links in a stable order, without the build commit and the
    derived community numbering, which can vary with file-system walk order."""
    graph = json.loads(path.read_text(encoding='utf-8'))
    graph.pop('built_at_commit', None)
    for node in graph.get('nodes', []):
        node.pop('community', None)
    key = lambda item: json.dumps(item, sort_keys=True)
    for name in ('nodes', 'links', 'hyperedges'):
        if isinstance(graph.get(name), list):
            graph[name] = sorted(graph[name], key=key)
    return graph


def main():
    update = '--update' in sys.argv[1:]
    committed = json.loads(GRAPH.read_text(encoding='utf-8')) if GRAPH.is_file() else {}
    wanted = committed.get('graph', {}).get('graphify_version', '')
    have = installed_version()
    if wanted and have and wanted != have and not update:
        sys.exit(f'The graph was built with graphify {wanted} but {have} is installed; '
                 f'install graphifyy=={wanted} or refresh with --update.')
    with tempfile.TemporaryDirectory() as tmp:
        fresh = build(Path(tmp))
        if update:
            for name in COMMITTED:
                if (fresh / name).is_file():
                    shutil.copy2(fresh / name, KB / 'graphify-out' / name)
            graph = comparable(GRAPH)
            print(f'Refreshed docs/kb/graphify-out: {len(graph["nodes"])} nodes, {len(graph["links"])} links '
                  f'(graphify {have}). Update docs/kb/ARCHGUARD_KB.md if a responsibility or contract changed.')
            return
        if comparable(fresh / 'graph.json') != comparable(GRAPH):
            new, old = comparable(fresh / 'graph.json'), comparable(GRAPH)
            ids = lambda g: {n['id'] for n in g['nodes']}
            sys.exit(f'docs/kb/graphify-out/graph.json is stale: {len(ids(new) - ids(old))} nodes added, '
                     f'{len(ids(old) - ids(new))} removed. Run: python3 scripts/kb_check.py --update')
    print('docs/kb/graphify-out/graph.json is up to date.')


if __name__ == '__main__':
    main()
