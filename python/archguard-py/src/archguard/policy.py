"""Reads, resolves and validates a Python policy (schemaVersion 2, language python)."""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from jsonschema import Draft202012Validator

from .model import LANGUAGE, ROLES, VERSION
from .selectors import validate_selector
from .spec import catalog

MAX_BYTES = 1_048_576
MAX_DEPTH = 16
PRESET = re.compile(r'^org:([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)@([0-9][A-Za-z0-9.+-]*)$')
IDENTIFIER = re.compile(r'^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$')


class PolicyError(ValueError):
    pass


@dataclass
class Context:
    id: str
    packages: List[str]
    exposedPackages: List[str]


@dataclass
class Constraint:
    id: str
    from_: List[str]
    forbidden: List[str]
    severity: str
    rationale: str
    remediation: str


@dataclass
class Policy:
    roots: List[str]
    extends: List[str] = field(default_factory=list)
    sourceRoots: Optional[List[str]] = None
    profiles: List[str] = field(default_factory=list)
    roles: Dict[str, List[str]] = field(default_factory=dict)
    contexts: List[Context] = field(default_factory=list)
    constraints: List[Constraint] = field(default_factory=list)
    rules: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    typeOnlyImports: str = 'count'
    unresolvedImports: str = 'fail'
    failOn: str = 'ERROR'
    newOnly: bool = False
    requireClassification: bool = False
    allowEmptySelectors: bool = False
    allowEmptyAnalysis: bool = False
    schemaVersion: int = 2
    language: str = LANGUAGE

    def context(self, cid: str) -> Context:
        return next(c for c in self.contexts if c.id == cid)


class _UniqueKeyLoader(yaml.SafeLoader):
    pass


def _construct_mapping(loader: yaml.SafeLoader, node: yaml.MappingNode, deep: bool = False) -> dict:
    loader.flatten_mapping(node)
    out = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in out:
            raise PolicyError(f'Duplicate key {key!r} at line {key_node.start_mark.line + 1}')
        out[key] = loader.construct_object(value_node, deep=deep)
    return out


_UniqueKeyLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _construct_mapping)


def _reject_nulls(value: Any) -> None:
    if value is None:
        raise PolicyError('Explicit null configuration values are not allowed')
    if isinstance(value, list):
        for v in value:
            _reject_nulls(v)
    elif isinstance(value, dict):
        for v in value.values():
            _reject_nulls(v)


def _read_tree(file: Path) -> dict:
    if not file.is_file():
        raise PolicyError(f'Policy not found: {file}')
    if file.stat().st_size > MAX_BYTES:
        raise PolicyError(f'Policy exceeds 1 MiB: {file}')
    try:
        tree = yaml.load(file.read_text(encoding='utf-8'), Loader=_UniqueKeyLoader)  # noqa: S506 - SafeLoader subclass
    except yaml.YAMLError as e:
        raise PolicyError(f'Invalid YAML in {file}: {e}') from None
    _reject_nulls(tree)
    if not isinstance(tree, dict):
        raise PolicyError(f'Policy must be a mapping: {file}')
    return tree


def _preset_file(reference: str) -> Path:
    """org:<org>/<name>@<version> loads presets/<name>/<version>.yml from the installed
    distribution package ``<org>_archguard_presets``."""
    m = PRESET.match(reference)
    if not m:
        raise PolicyError(f'Invalid preset reference: {reference}')
    org, name, version = m.groups()
    package = re.sub(r'[^A-Za-z0-9_]', '_', org) + '_archguard_presets'
    spec = importlib.util.find_spec(package)
    if spec is None or not spec.submodule_search_locations:
        raise PolicyError(
            f'Policy preset package not installed: {package} (for {reference}). Add it to your dev dependencies.'
        )
    for location in spec.submodule_search_locations:
        file = Path(location) / 'presets' / name / f'{version}.yml'
        if file.is_file():
            return file
    raise PolicyError(f'Policy preset not found: presets/{name}/{version}.yml in {package}')


def _parent_file(child: Path, reference: str) -> Path:
    if reference.startswith('org:'):
        return _preset_file(reference)
    if reference.startswith('classpath:'):
        raise PolicyError(f'classpath: references are only supported by the Java analyzer: {reference}')
    if Path(reference).is_absolute():
        return Path(reference)
    if reference.startswith('./') or reference.startswith('../'):
        return (child.parent / reference).resolve()
    raise PolicyError(f'Invalid extends reference: {reference}')


def _by_id(items: list) -> bool:
    return bool(items) and all(isinstance(n, dict) and isinstance(n.get('id'), str) for n in items)


def merge(parent: dict, child: dict) -> dict:
    """Maps merge by key, lists of objects with an id merge by id, everything else is replaced."""
    out = copy.deepcopy(parent)
    for k, value in child.items():
        existing = out.get(k)
        if isinstance(existing, dict) and isinstance(value, dict):
            out[k] = merge(existing, value)
        elif isinstance(existing, list) and isinstance(value, list) and _by_id(existing) and _by_id(value):
            entries: Dict[str, Any] = {}
            for n in existing + value:
                entries[n['id']] = copy.deepcopy(n)
            out[k] = list(entries.values())
        else:
            out[k] = copy.deepcopy(value)
    return out


def _reject_locked_changes(inherited: dict, child: dict, label: str) -> None:
    parent_rules = inherited.get('rules') if isinstance(inherited.get('rules'), dict) else {}
    child_rules = child.get('rules') if isinstance(child.get('rules'), dict) else {}
    for rid, setting in parent_rules.items():
        if not isinstance(setting, dict) or setting.get('locked') is not True:
            continue
        mine = child_rules.get(rid)
        if not isinstance(mine, dict):
            continue
        for key in ('enabled', 'severity', 'locked'):
            if key in mine and mine[key] != setting.get(key):
                raise PolicyError(f"Rule {rid} is locked by an extended preset; {label} cannot change '{key}'")


def _resolve_tree(file: Path, chain: List[Path]) -> dict:
    if file in chain:
        raise PolicyError('Cyclic policy extends: ' + ' -> '.join(str(c) for c in chain + [file]))
    if len(chain) >= MAX_DEPTH:
        raise PolicyError('Policy extends too deep')
    tree = _read_tree(file)
    if 'extends' not in tree:
        return tree
    if not isinstance(tree['extends'], list):
        raise PolicyError('extends must be a list')
    chain.append(file)
    try:
        inherited: dict = {}
        for reference in tree['extends']:
            parent = _resolve_tree(_parent_file(file, str(reference)), chain)
            if parent.get('schemaVersion') != 2 or parent.get('kind') != 'preset':
                raise PolicyError(f'Extended policy must be schemaVersion 2 with kind: preset: {reference}')
            if 'language' in tree and 'language' in parent and tree['language'] != parent['language']:
                raise PolicyError(f'Extended preset language differs: {reference}')
            _reject_locked_changes(inherited, parent, str(reference))
            inherited = merge(inherited, parent)
        _reject_locked_changes(inherited, tree, str(file))
        merged = merge(inherited, tree)
        merged.pop('kind', None)
        if 'kind' in tree:
            merged['kind'] = tree['kind']
        merged['extends'] = tree['extends']
        return merged
    finally:
        chain.pop()


def _schema_error(tree: dict) -> Optional[str]:
    validator = Draft202012Validator(catalog().policy_schema)
    error = next(iter(sorted(validator.iter_errors(tree), key=lambda e: list(e.absolute_path))), None)
    if error is None:
        return None
    where = '/' + '/'.join(str(p) for p in error.absolute_path) if error.absolute_path else '(root)'
    if error.validator == 'additionalProperties':
        extra = sorted(set(error.instance) - set(error.schema.get('properties', {})))
        return f'Unknown policy key at {where}: {extra[0] if extra else "?"}'
    return f'Policy schema violation at {where}: {error.message}'


def read_policy(file: Path) -> Policy:
    tree = _resolve_tree(Path(file).resolve(), [])
    problem = _schema_error(tree)
    if problem:
        raise PolicyError(problem)
    if tree.get('schemaVersion') != 2:
        raise PolicyError('schemaVersion 1 policies are Java-only; use schemaVersion 2 with language: python')
    if tree.get('kind') == 'preset':
        raise PolicyError('A preset policy cannot be analyzed directly; extend it from a project policy')
    if tree.get('language') != LANGUAGE:
        raise PolicyError(f"Policy language '{tree.get('language')}' cannot be analyzed by the Python analyzer")
    p = Policy(
        roots=list(tree['roots']),
        extends=list(tree.get('extends', [])),
        sourceRoots=list(tree['sourceRoots']) if 'sourceRoots' in tree else None,
        profiles=list(tree.get('profiles', [])),
        roles={k: list(v) for k, v in tree.get('roles', {}).items()},
        contexts=[Context(c['id'], list(c['packages']), list(c.get('exposedPackages', []))) for c in tree.get('contexts', [])],
        constraints=[
            Constraint(
                c['id'], list(c['from']), list(c['forbidden']), c.get('severity', 'ERROR'),
                c.get('rationale', ''), c.get('remediation', ''),
            )
            for c in tree.get('constraints', [])
        ],
        rules={k: dict(v) for k, v in tree.get('rules', {}).items()},
        typeOnlyImports=tree.get('typeOnlyImports', 'count'),
        unresolvedImports=tree.get('unresolvedImports', 'fail'),
        failOn=tree.get('failOn', 'ERROR'),
        newOnly=tree.get('newOnly', False),
        requireClassification=tree.get('requireClassification', False),
        allowEmptySelectors=tree.get('allowEmptySelectors', False),
        allowEmptyAnalysis=tree.get('allowEmptyAnalysis', False),
    )
    semantic_validate(p)
    return p


def _identifier(value: str) -> None:
    if not IDENTIFIER.match(value):
        raise PolicyError(f'Invalid identifier: {value}')


def _selectors(items: List[str], label: str) -> None:
    if not items:
        raise PolicyError(f'Empty selector list: {label}')
    for s in items:
        validate_selector(s)


def semantic_validate(p: Policy) -> None:
    known = catalog().profiles
    for profile in p.profiles:
        if profile not in known:
            raise PolicyError(f'Unknown architecture profile: {profile}')
    _selectors(p.roots, 'roots')
    for role, items in p.roles.items():
        if role not in ROLES:
            raise PolicyError(f'{role} cannot be explicitly mapped')
        _selectors(items, f'role {role}')
    seen = set()
    for c in p.contexts:
        _identifier(c.id)
        if c.id in seen:
            raise PolicyError(f'Duplicate context: {c.id}')
        seen.add(c.id)
        _selectors(c.packages, f'context {c.id}')
        for s in c.exposedPackages:
            validate_selector(s)
    seen = set()
    for c in p.constraints:
        _identifier(c.id)
        if c.id in seen:
            raise PolicyError(f'Duplicate constraint: {c.id}')
        seen.add(c.id)
        _selectors(c.from_, f'constraint {c.id}')
        _selectors(c.forbidden, f'constraint {c.id}')
        if not c.rationale.strip() or not c.remediation.strip():
            raise PolicyError('Constraints require rationale and remediation')
    for k in p.rules:
        _identifier(k)
    for r in p.sourceRoots or []:
        if Path(r).is_absolute() or '..' in re.split(r'[\\/]', r):
            raise PolicyError(f'sourceRoots must be project-relative: {r}')


def _canonical(value: Any) -> Any:
    if isinstance(value, list):
        return [_canonical(v) for v in value]
    if isinstance(value, dict):
        return {k: _canonical(value[k]) for k in sorted(value)}
    return value


def policy_hash(p: Policy) -> str:
    """Canonical policy hash bound into baselines (analyzer-specific, spec/FINGERPRINT.md)."""
    tree = asdict(p)
    tree['profiles'] = sorted(set(p.profiles))
    for c in tree['constraints']:
        c['from'] = c.pop('from_')
    text = json.dumps(_canonical(tree), separators=(',', ':'), ensure_ascii=False)
    return hashlib.sha256(f'{VERSION}\n{text}'.encode('utf-8')).hexdigest()
