#!/usr/bin/env python3
"""Validate the ArchGuard spec: schemas, profiles, rules, infrastructure lists and example policies.

Requires PyYAML and jsonschema. Exits non-zero with a list of problems on failure.
"""
import json
import re
import sys
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parent.parent
SPEC = ROOT / 'spec'
problems = []


def fail(message):
    problems.append(message)


def load_yaml(path):
    with open(path, encoding='utf-8') as handle:
        return yaml.safe_load(handle)


def validator(name):
    schema = json.loads((SPEC / 'schemas' / name).read_text(encoding='utf-8'))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def validate(v, document, label):
    for error in sorted(v.iter_errors(document), key=lambda e: list(e.path)):
        fail(f'{label}: {"/".join(map(str, error.path)) or "<root>"}: {error.message}')


schemas = {p.name: validator(p.name) for p in sorted((SPEC / 'schemas').glob('*.json'))}

# Rule catalog
rules = {}
for path in sorted((SPEC / 'rules').glob('*.yml')):
    rule = load_yaml(path)
    validate(schemas['rule.schema.json'], rule, str(path.relative_to(ROOT)))
    if rule.get('id') != path.stem:
        fail(f'{path.name}: id {rule.get("id")} does not match file name')
    for language in rule.get('languages', []):
        if language not in rule.get('examples', {}):
            fail(f'{path.name}: missing {language} example')
    rules[rule['id']] = rule

# Profiles
profiles = {}
for path in sorted((SPEC / 'profiles').glob('*.yml')):
    profile = load_yaml(path)
    validate(schemas['profile.schema.json'], profile, str(path.relative_to(ROOT)))
    if profile.get('id') != path.stem:
        fail(f'{path.name}: id {profile.get("id")} does not match file name')
    profiles[profile['id']] = profile
for profile in profiles.values():
    for include in profile.get('includes', []):
        if include not in profiles:
            fail(f'profile {profile["id"]}: unknown include {include}')
    for rule_id in profile.get('activates', []) + [r['rule'] for r in profile.get('roleRules', [])]:
        if rule_id not in rules:
            fail(f'profile {profile["id"]}: unknown rule {rule_id}')
    for role_rule in profile.get('roleRules', []):
        if rules.get(role_rule['rule'], {}).get('activation') != 'profile':
            fail(f'profile {profile["id"]}: roleRule {role_rule["rule"]} must have activation profile')


def includes_cycle(name, seen=()):
    if name in seen:
        return True
    return any(includes_cycle(i, seen + (name,)) for i in profiles.get(name, {}).get('includes', []))


for name in profiles:
    if includes_cycle(name):
        fail(f'profile {name}: include cycle')
for rule in rules.values():
    if rule['activation'] == 'profile' and not any(
        rule['id'] in p.get('activates', []) for p in profiles.values()
    ):
        fail(f'rule {rule["id"]}: activation profile but no profile activates it')

# Infrastructure lists
infrastructure_schema = Draft202012Validator(
    {
        'type': 'object',
        'additionalProperties': False,
        'properties': {
            'language': {'enum': ['java', 'python', 'typescript']},
            'description': {'type': 'string'},
            'matching': {'enum': ['prefix', 'module']},
            'entries': {'type': 'array', 'items': {'type': 'string', 'minLength': 1}, 'minItems': 1, 'uniqueItems': True},
        },
        'required': ['language', 'description', 'matching', 'entries'],
    }
)
infrastructure = {}
for path in sorted((SPEC / 'infrastructure').glob('*.yml')):
    document = load_yaml(path)
    validate(infrastructure_schema, document, str(path.relative_to(ROOT)))
    if document.get('language') != path.stem:
        fail(f'{path.name}: language does not match file name')
    infrastructure[path.stem] = document
for language in ('java', 'python', 'typescript'):
    if language not in infrastructure:
        fail(f'missing infrastructure list for {language}')

# Policies: every example and template must validate
policy_files = sorted(ROOT.glob('examples/*/architecture.yml'))
policy_files += sorted(ROOT.glob('spec/conformance/*/*/architecture.yml'))
policy_files += sorted(ROOT.glob('skills/archguard/templates/*.yml'))
for path in policy_files:
    if 'invalid' in path.parts[-3:-1] or 'invalid-policy' in str(path):
        continue
    validate(schemas['policy.schema.json'], load_yaml(path), str(path.relative_to(ROOT)))

# Negative policy cases the schema must reject
negative = {
    'unknown key': {'schemaVersion': 1, 'roots': ['a..'], 'unknownKey': True},
    'v1 with extends': {'schemaVersion': 1, 'roots': ['a..'], 'extends': ['./x.yml']},
    'v1 unknown profile': {'schemaVersion': 1, 'roots': ['a..'], 'profiles': ['layered']},
    'v2 without language': {'schemaVersion': 2, 'roots': ['a.**']},
    'unknown role': {'schemaVersion': 2, 'language': 'java', 'roots': ['a.**'], 'roles': {'SERVICE': ['a.**']}},
    'constraint without remediation': {
        'schemaVersion': 2, 'language': 'python', 'roots': ['a.**'],
        'constraints': [{'id': 'X-1', 'from': ['a.**'], 'forbidden': ['b'], 'rationale': 'r'}],
    },
}
for label, document in negative.items():
    if schemas['policy.schema.json'].is_valid(document):
        fail(f'policy schema accepted invalid case: {label}')
positive = {
    'v2 preset without roots': {'schemaVersion': 2, 'kind': 'preset', 'profiles': ['hexagonal'], 'rules': {'HEX-001': {'locked': True}}},
    'v2 python project': {
        'schemaVersion': 2, 'language': 'python', 'extends': ['org:acme/base@1.0.0'], 'roots': ['orders.**'],
        'sourceRoots': ['src'], 'profiles': ['layered'], 'typeOnlyImports': 'ignore', 'unresolvedImports': 'fail',
    },
}
for label, document in positive.items():
    validate(schemas['policy.schema.json'], document, f'positive case {label}')

# Java parity: catalog text and lists must match the current Java engine
engine = ROOT / 'archguard-core/src/main/java/io/archguard/engine'
java = (engine / 'BuiltinRules.java').read_text(encoding='utf-8')
joined = re.sub(r'"\s*\+\s*"', '', java + (engine / 'ModelImporter.java').read_text(encoding='utf-8'))
ids_block = re.search(r'IDS\s*=\s*Set\.of\(([^;]*)\);', java, re.S)
java_ids = set(re.findall(r'"([A-Z]+-[0-9]{3})"', ids_block.group(1))) if ids_block else set()
catalog_java = {r['id'] for r in rules.values() if 'java' in r['languages'] and not r['id'].startswith('LAYER-')}
if java_ids != catalog_java:
    fail(f'Java built-in IDs {sorted(java_ids)} differ from catalog {sorted(catalog_java)}')
infra_block = re.search(r'isInfrastructure\(String n\)\s*\{\s*return List\.of\(([^)]*)\)', java, re.S)
java_infra = re.findall(r'"([^"]+)"', infra_block.group(1)) if infra_block else []
if java_infra != infrastructure.get('java', {}).get('entries'):
    fail(f'Java infrastructure list differs from spec/infrastructure/java.yml: {java_infra}')
for rule_id in sorted(java_ids):
    rule = rules[rule_id]
    for field in ('message', 'remediation', 'evidence'):
        text = rule.get(field)
        if not text:
            continue
        for piece in re.split(r'\{[A-Za-z]+\}', text):
            piece = piece.strip()
            if rule_id in ('DDD-002', 'CYCLE-001') and field in ('message', 'evidence'):
                piece = piece.replace('bounded contexts', '').replace('packages', '').strip(' :')
            if piece and piece not in joined:
                fail(f'{rule_id}.{field}: text not found in the Java engine: {piece!r}')

if problems:
    print('Spec check FAILED:')
    for p in problems:
        print('  - ' + p)
    sys.exit(1)
print(
    f'Spec check passed: {len(schemas)} schemas, {len(rules)} rules, {len(profiles)} profiles, '
    f'{len(infrastructure)} infrastructure lists, {len(policy_files)} policies, '
    f'{len(negative)} negative and {len(positive)} positive schema cases.'
)
