"""Baselines and reviewed suppressions (spec/schemas/baseline.schema.json, suppressions.schema.json)."""
from __future__ import annotations

import datetime as _dt
import json
import re
from pathlib import Path
from typing import Dict, Optional

from .model import AnalysisError, AnalysisResult
from .reports import atomic

FINGERPRINT = re.compile(r'^[a-f0-9]{64}$')
DATE = re.compile(r'^\d{4}-\d{2}-\d{2}$')


def _read_json(file: Path, label: str):
    try:
        return json.loads(Path(file).read_text(encoding='utf-8'))
    except (OSError, ValueError) as e:
        raise AnalysisError(f'Cannot read {label} {file}: {e}') from None


def _only_keys(value, keys, label: str) -> None:
    if not isinstance(value, dict):
        raise AnalysisError(f'Invalid {label} schema')
    for k in value:
        if k not in keys:
            raise AnalysisError(f'Invalid {label} schema: unknown field {k}')


def write_baseline(file: Path, result: AnalysisResult) -> None:
    fingerprints = sorted({f.fingerprint for f in result.findings if f.severity != 'INFO'})
    body = {'schemaVersion': 1, 'policyHash': result.policy_hash, 'fingerprints': fingerprints}
    atomic(Path(file), json.dumps(body, indent=2) + '\n')


def _valid_date(s) -> bool:
    if not isinstance(s, str) or not DATE.match(s):
        return False
    try:
        return _dt.date.fromisoformat(s).isoformat() == s
    except ValueError:
        return False


def apply_debt(r: AnalysisResult, baseline: Optional[Path], suppressions: Optional[Path],
               today: Optional[_dt.date] = None) -> AnalysisResult:
    today_text = (today or _dt.datetime.now(_dt.timezone.utc).date()).isoformat()
    accepted = set()
    ignored: Dict[str, dict] = {}
    if baseline:
        b = _read_json(baseline, 'baseline')
        _only_keys(b, ('schemaVersion', 'policyHash', 'fingerprints'), 'baseline')
        if b.get('schemaVersion') != 1 or b.get('policyHash') != r.policy_hash or not isinstance(b.get('fingerprints'), list):
            raise AnalysisError('Baseline schema, engine or policy does not match; review and explicitly regenerate it')
        accepted = set(b['fingerprints'])
    if suppressions:
        data = _read_json(suppressions, 'suppressions')
        _only_keys(data, ('schemaVersion', 'entries'), 'suppression')
        if data.get('schemaVersion') != 1 or not isinstance(data.get('entries'), list):
            raise AnalysisError('Invalid suppression schema')
        for s in data['entries']:
            _only_keys(s, ('fingerprint', 'owner', 'reason', 'expires'), 'suppression')
            if not (
                isinstance(s.get('fingerprint'), str) and FINGERPRINT.match(s['fingerprint'])
                and isinstance(s.get('owner'), str) and s['owner'].strip()
                and isinstance(s.get('reason'), str) and s['reason'].strip()
            ):
                raise AnalysisError('Suppression requires fingerprint, owner and reason')
            if not _valid_date(s.get('expires')):
                raise AnalysisError('Invalid suppression expiry')
            if s['expires'] < today_text:
                raise AnalysisError(f"Expired suppression: {s['fingerprint']}")
            if s['fingerprint'] in ignored:
                raise AnalysisError(f"Duplicate suppression: {s['fingerprint']}")
            ignored[s['fingerprint']] = s
    findings = []
    for f in r.findings:
        status = 'SUPPRESSED' if f.fingerprint in ignored else 'EXISTING' if f.fingerprint in accepted else 'NEW'
        findings.append(type(f)(**{**f.__dict__, 'status': status}))
    current = {f.fingerprint for f in findings}
    stale = len([a for a in accepted if a not in current])
    diagnostics = list(r.diagnostics) + [f'Baseline entries no longer observed in this scope: {stale} (baseline not modified)']
    for s in ignored.values():
        diagnostics.append(f"Suppression {s['fingerprint']} owner={s['owner']} expires={s['expires']} reason={s['reason']}")
    return r.with_findings(findings, diagnostics)
