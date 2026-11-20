"""Report writers: json, sarif, html, agent (JSONL) and console (spec/CLI.md, SARIF_MAPPING.md)."""
from __future__ import annotations

import html as _html
import json
import os
import secrets
from pathlib import Path
from typing import Iterable
from urllib.parse import quote

from .model import AnalysisResult

FORMATS = frozenset({'json', 'sarif', 'html', 'agent', 'console'})
AGENT_FILE = 'archguard.agent.jsonl'


def atomic(file: Path, contents: str) -> None:
    file.parent.mkdir(parents=True, exist_ok=True)
    temporary = file.parent / f'.archguard-{secrets.token_hex(6)}.tmp'
    try:
        temporary.write_text(contents, encoding='utf-8')
        os.replace(temporary, file)
    finally:
        if temporary.exists():
            temporary.unlink()


def _pretty(value) -> str:
    return json.dumps(value, indent=2, ensure_ascii=False) + '\n'


def write_reports(directory: Path, result: AnalysisResult, formats: Iterable[str], gate_failed: bool) -> None:
    formats = set(formats)
    directory.mkdir(parents=True, exist_ok=True)
    if 'json' in formats:
        atomic(directory / 'archguard.json', _pretty(result.to_json()))
    if 'sarif' in formats:
        atomic(directory / 'archguard.sarif', _pretty(sarif(result)))
    if 'html' in formats:
        atomic(directory / 'index.html', html(result))
    if 'agent' in formats:
        atomic(directory / AGENT_FILE, agent(result, gate_failed))


def _spec_version() -> str:
    try:
        from .spec import catalog
        return catalog().spec_version
    except Exception:  # noqa: BLE001 - failure reports must be written even without a catalog
        return 'unknown'


def write_failure(directory: Path, message: str, formats: Iterable[str]) -> None:
    """Overwrites the report set with explicit failure outputs so a stale pass is never left behind."""
    atomic(directory / 'archguard.json', _pretty(
        {'schemaVersion': '1', 'specVersion': _spec_version(), 'analysisStatus': 'FAILED', 'error': message}))
    atomic(directory / 'archguard.sarif', _pretty({
        'version': '2.1.0',
        'runs': [{
            'tool': {'driver': {'name': 'ArchGuard'}},
            'invocations': [{
                'executionSuccessful': False,
                'toolExecutionNotifications': [{'level': 'error', 'message': {'text': message}}],
            }],
        }],
    }))
    atomic(directory / 'index.html',
           '<!doctype html><html lang="en"><meta charset="utf-8"><title>ArchGuard analysis failed</title>'
           '<h1>Analysis failed</h1><p>No compliance result is available. See archguard.json and the build log '
           'for the error.</p></html>')
    if 'agent' in set(formats):
        atomic(directory / AGENT_FILE, agent_error(message))


def _line(value) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(',', ':')) + '\n'


def agent(r: AnalysisResult, gate_failed: bool) -> str:
    """One JSON object per non-INFO finding, then a summary line."""
    counts = {'NEW': 0, 'EXISTING': 0, 'SUPPRESSED': 0}
    out = ''
    for f in r.findings:
        if f.severity == 'INFO':
            continue
        counts[f.status] += 1
        out += _line({
            'rule': f.rule_id, 'severity': f.severity, 'status': f.status, 'file': f.location.path,
            'line': f.location.line, 'symbol': f.location.symbol, 'target': f.target,
            'message': f.message, 'fix': f.remediation, 'fingerprint': f.fingerprint,
        })
    return out + _line({
        'summary': True, 'status': 'FAILED' if gate_failed else 'PASSED',
        'new': counts['NEW'], 'existing': counts['EXISTING'], 'suppressed': counts['SUPPRESSED'],
    })


def agent_error(message: str) -> str:
    return _line({'summary': True, 'status': 'ERROR', 'error': message})


def summary(r: AnalysisResult) -> str:
    counts = {'NEW': 0, 'EXISTING': 0, 'SUPPRESSED': 0}
    info = 0
    for f in r.findings:
        if f.severity == 'INFO':
            info += 1
        else:
            counts[f.status] += 1
    out = (f'ArchGuard {r.engine_version}: {r.analyzed} modules, {r.dependencies} dependencies, '
           f"{len(r.findings)} findings ({counts['NEW']} new, {counts['EXISTING']} existing, "
           f"{counts['SUPPRESSED']} suppressed, {info} info)")
    for d in r.diagnostics:
        if d.startswith('Unclassified application') and not d.split(': ', 1)[-1].startswith('0 '):
            out += f"; unclassified {d.split(': ', 1)[-1]}"
    return out


def console_report(r: AnalysisResult) -> str:
    out = summary(r) + '\n'
    for f in r.findings:
        if f.severity == 'INFO':
            continue
        out += (f'{f.severity} {f.rule_id} [{f.status}] {f.location.symbol}:{f.location.line} \u2014 {f.message}\n'
                f'  {f.remediation}\n')
    return out


def sarif(r: AnalysisResult) -> dict:
    from .spec import catalog

    specs = catalog().rules
    rules = {}
    results = []
    for f in r.findings:
        if f.rule_id not in rules:
            rules[f.rule_id] = {
                'id': f.rule_id,
                'shortDescription': {'text': specs[f.rule_id].title if f.rule_id in specs else f.rule_id},
                'help': {'text': f.remediation},
            }
        kind = 'function' if '#' in f.location.symbol else 'module'
        location: dict = {'logicalLocations': [{'fullyQualifiedName': f.location.symbol, 'kind': kind}]}
        if f.location.path:
            physical: dict = {'artifactLocation': {'uri': quote(f.location.path), 'uriBaseId': '%SRCROOT%'}}
            if f.location.line > 0:
                physical['region'] = {'startLine': f.location.line}
            location['physicalLocation'] = physical
        entry = {
            'ruleId': f.rule_id,
            'level': {'ERROR': 'error', 'WARNING': 'warning'}.get(f.severity, 'note'),
            'message': {'text': f'{f.message}\nEvidence: {f.evidence}\nSuggested correction: {f.remediation}'},
            'partialFingerprints': {'archguard/v1': f.fingerprint},
            'baselineState': 'unchanged' if f.status == 'EXISTING' else 'new',
            'locations': [location],
            'properties': {'module': f.location.module, 'target': f.target, 'status': f.status},
        }
        if f.status == 'SUPPRESSED':
            entry['suppressions'] = [{
                'kind': 'external', 'status': 'accepted',
                'justification': 'Reviewed suppression; see report diagnostics for owner, reason and expiry',
            }]
        results.append(entry)
    return {
        'version': '2.1.0',
        '$schema': 'https://json.schemastore.org/sarif-2.1.0.json',
        'runs': [{
            'tool': {'driver': {'name': 'ArchGuard', 'version': r.engine_version,
                                'rules': [rules[k] for k in sorted(rules)]}},
            'results': results,
            'invocations': [{'executionSuccessful': True}],
            'properties': {'policyHash': r.policy_hash, 'diagnostics': r.diagnostics, 'specVersion': r.spec_version},
        }],
    }


def _e(s) -> str:
    return _html.escape(str(s), quote=True).replace('&#x27;', '&#39;')


def html(r: AnalysisResult) -> str:
    out = (
        '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, '
        'initial-scale=1"><meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src '
        '\'unsafe-inline\'"><title>ArchGuard architecture report</title><style>body{font:16px system-ui;'
        'max-width:1100px;margin:40px auto;padding:0 24px;background:#f5f7fb;color:#19243a}article{background:white;'
        'border:1px solid #dce3ee;border-left:5px solid #375dd3;padding:20px;margin:18px 0;border-radius:8px}code,pre'
        '{white-space:pre-wrap;overflow-wrap:anywhere}small{color:#526078}h1{letter-spacing:-1px}.ERROR{border-left-'
        'color:#be3030}.WARNING{border-left-color:#b8860b}summary{cursor:pointer}</style><body><h1>ArchGuard</h1>'
    )
    out += (f'<p>Engine {_e(r.engine_version)} \u00b7 {r.analyzed} modules \u00b7 {r.dependencies} static dependencies '
            f'\u00b7 {len(r.findings)} findings</p><p>Analysis completed. Gate outcome depends on configured severity '
            f'and baseline policy.</p>')
    out += '<details><summary>Scope and diagnostics</summary><ul>'
    for d in r.diagnostics:
        out += f'<li>{_e(d)}</li>'
    out += f'</ul><small>Policy: {_e(r.policy_hash)}</small></details>'
    for f in r.findings:
        where = f'{f.location.module} / {f.location.path}:{f.location.line} \u2014 {f.location.symbol}'
        out += (f'<article class="{f.severity}"><small>{_e(f.rule_id)} \u00b7 {f.severity} \u00b7 {_e(f.status)}</small>'
                f'<h2>{_e(f.message)}</h2><p><code>{_e(where)}</code></p><p><strong>Evidence</strong></p>'
                f'<pre>{_e(f.evidence)}</pre><p><strong>Suggested correction</strong></p><p>{_e(f.remediation)}</p>'
                f'<small>Fingerprint: {_e(f.fingerprint)}</small></article>')
    return out + '</body></html>'
