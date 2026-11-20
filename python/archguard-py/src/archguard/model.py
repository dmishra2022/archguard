from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Dict, List, Optional

VERSION = '0.1.0'
LANGUAGE = 'python'
SEVERITIES = ('INFO', 'WARNING', 'ERROR')
ROLES = (
    'DOMAIN',
    'APPLICATION',
    'INBOUND_PORT',
    'OUTBOUND_PORT',
    'INBOUND_ADAPTER',
    'OUTBOUND_ADAPTER',
    'COMPOSITION_ROOT',
)
UNCLASSIFIED = 'UNCLASSIFIED'


class AnalysisError(Exception):
    """Analysis could not be completed; always exit code 2, never a pass."""


def at_least(severity: str, minimum: str) -> bool:
    return SEVERITIES.index(severity) >= SEVERITIES.index(minimum)


@dataclass(frozen=True)
class Location:
    module: str
    path: str
    symbol: str
    line: int

    def to_json(self) -> dict:
        return {'module': self.module, 'path': self.path, 'symbol': self.symbol, 'line': self.line}


@dataclass
class Unit:
    name: str
    package: str
    role: str
    context: str
    tags: List[str]
    location: Location

    @property
    def containers(self) -> List[str]:
        return [self.name]


@dataclass
class Dependency:
    origin: str
    target: str
    evidence: str
    location: Location
    kind: str = 'IMPORT'
    external_module: Optional[str] = None

    @property
    def target_containers(self) -> List[str]:
        return [self.target]


@dataclass
class Model:
    units: Dict[str, Unit]
    dependencies: List[Dependency]
    diagnostics: List[str]


@dataclass
class Finding:
    fingerprint: str
    rule_id: str
    severity: str
    message: str
    evidence: str
    location: Location
    target: str
    remediation: str
    status: str = 'NEW'

    def to_json(self) -> dict:
        return {
            'fingerprint': self.fingerprint,
            'ruleId': self.rule_id,
            'severity': self.severity,
            'message': self.message,
            'evidence': self.evidence,
            'location': self.location.to_json(),
            'target': self.target,
            'remediation': self.remediation,
            'status': self.status,
        }


@dataclass
class AnalysisResult:
    engine_version: str
    policy_hash: str
    analyzed: int
    dependencies: int
    findings: List[Finding]
    diagnostics: List[str]
    spec_version: str
    language: str = LANGUAGE
    schema_version: str = '1'

    def fails(self, minimum: str, new_only: bool) -> bool:
        return any(
            f.status != 'SUPPRESSED'
            and (not new_only or f.status == 'NEW')
            and at_least(f.severity, minimum)
            for f in self.findings
        )

    def with_findings(self, findings: List[Finding], diagnostics: List[str]) -> 'AnalysisResult':
        return replace(self, findings=findings, diagnostics=diagnostics)

    def to_json(self) -> dict:
        return {
            'schemaVersion': self.schema_version,
            'engineVersion': self.engine_version,
            'policyHash': self.policy_hash,
            'analyzedClasses': self.analyzed,
            'dependencies': self.dependencies,
            'findings': [f.to_json() for f in self.findings],
            'diagnostics': list(self.diagnostics),
            'specVersion': self.spec_version,
            'language': self.language,
        }
