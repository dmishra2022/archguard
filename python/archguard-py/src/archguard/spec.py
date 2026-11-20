"""The bundled spec catalog: profiles, rules and infrastructure lists (loaded once)."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Dict, FrozenSet, Iterable, List, Optional, Set

import yaml

from .model import LANGUAGE, ROLES, UNCLASSIFIED


@dataclass(frozen=True)
class RoleRule:
    rule: str
    origin_roles: FrozenSet[str]
    forbidden_roles: FrozenSet[str]
    forbid_infrastructure: bool
    cross_role_only: bool

    def forbids(self, origin: str, target: str, infrastructure: bool) -> bool:
        if origin not in self.origin_roles:
            return False
        role = target in self.forbidden_roles and not (self.cross_role_only and origin == target)
        return role or (self.forbid_infrastructure and infrastructure)


@dataclass(frozen=True)
class Profile:
    id: str
    includes: List[str]
    activates: FrozenSet[str]
    role_rules: List[RoleRule]


@dataclass(frozen=True)
class RuleSpec:
    id: str
    title: str
    category: str
    default_severity: str
    activation: str
    message: str
    evidence: Optional[str]
    remediation: str
    languages: FrozenSet[str]


def fill(template: Optional[str], values: Dict[str, str]) -> str:
    if template is None:
        return ''
    out = template
    for key, value in values.items():
        out = out.replace('{' + key + '}', value)
    return out


def spec_directory() -> Path:
    override = os.environ.get('ARCHGUARD_SPEC_DIR')
    if override:
        return Path(override)
    here = Path(__file__).resolve().parent
    for candidate in (here / 'spec', here.parent.parent.parent.parent / 'spec'):
        if (candidate / 'index.yml').is_file():
            return candidate
    raise RuntimeError('ArchGuard spec catalog not found next to the package')


def _roles(values: Iterable[str]) -> FrozenSet[str]:
    out = set()
    for v in values or []:
        if v != UNCLASSIFIED and v not in ROLES:
            raise RuntimeError(f'Unknown role in spec: {v}')
        out.add(v)
    return frozenset(out)


class Catalog:
    def __init__(self, directory: Path):
        def load(name: str):
            return yaml.safe_load((directory / name).read_text(encoding='utf-8'))

        index = load('index.yml')
        self.spec_version = str(index['specVersion'])
        self.profiles: Dict[str, Profile] = {}
        self.role_rules: List[RoleRule] = []
        for pid in sorted(index['profiles']):
            p = load(f'profiles/{pid}.yml')
            rules = [
                RoleRule(
                    r['rule'],
                    _roles(r.get('from')),
                    _roles(r.get('forbiddenRoles')),
                    r.get('forbidInfrastructure') is True,
                    r.get('crossRoleOnly') is True,
                )
                for r in p.get('roleRules') or []
            ]
            self.role_rules.extend(rules)
            self.profiles[pid] = Profile(p['id'], list(p.get('includes') or []), frozenset(p.get('activates') or []), rules)
        self.rules: Dict[str, RuleSpec] = {}
        for rid in sorted(index['rules']):
            r = load(f'rules/{rid}.yml')
            self.rules[rid] = RuleSpec(
                r['id'],
                r['title'],
                r['category'],
                r['defaultSeverity'],
                r['activation'],
                r['message'],
                r.get('evidence'),
                str(r.get('remediation') or '').strip(),
                frozenset(r.get('languages') or []),
            )
        self.infrastructure: List[str] = list(load(f'infrastructure/{LANGUAGE}.yml').get('entries') or [])
        self.policy_schema = json.loads((directory / 'schemas/policy.schema.json').read_text(encoding='utf-8'))
        self.rule_ids: Set[str] = {r.id for r in self.rules.values() if LANGUAGE in r.languages}

    def rule(self, rid: str) -> RuleSpec:
        if rid not in self.rules:
            raise RuntimeError(f'Unknown catalog rule: {rid}')
        return self.rules[rid]

    def expand(self, selected: Iterable[str]) -> Set[str]:
        out: Set[str] = set()
        work = list(selected)
        while work:
            pid = work.pop()
            if pid not in self.profiles:
                raise ValueError(f'Unknown architecture profile: {pid}')
            if pid not in out:
                out.add(pid)
                work.extend(self.profiles[pid].includes)
        return out

    def activated_by(self, rule_id: str, selected: Iterable[str]) -> bool:
        return any(rule_id in self.profiles[p].activates for p in self.expand(selected))


@lru_cache(maxsize=1)
def catalog() -> Catalog:
    return Catalog(spec_directory())
