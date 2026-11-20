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
policy_files += sorted(ROOT.glob('docs/pilots/*/architecture.yml'))
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

# Index must list exactly the catalog files (analyzers load the catalog through it)
index = load_yaml(SPEC / 'index.yml')
for key, found in (('profiles', profiles), ('rules', rules), ('infrastructure', infrastructure)):
    if sorted(index.get(key, [])) != sorted(found):
        fail(f'spec/index.yml {key} {sorted(index.get(key, []))} differs from files {sorted(found)}')
if not re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+', str(index.get('specVersion', ''))):
    fail('spec/index.yml specVersion must be MAJOR.MINOR.PATCH')

# Placeholders used in templates must be documented
for rule in rules.values():
    used = set()
    for field in ('message', 'remediation', 'evidence'):
        used |= set(re.findall(r'\{([A-Za-z]+)\}', rule.get(field, '')))
    undocumented = used - set(rule.get('placeholders', {}))
    if undocumented:
        fail(f'{rule["id"]}: undocumented placeholders {sorted(undocumented)}')

# The editor schema shipped in docs/ must be the spec policy schema
if (ROOT / 'docs/architecture.schema.json').read_text(encoding='utf-8') != (
    SPEC / 'schemas/policy.schema.json'
).read_text(encoding='utf-8'):
    fail('docs/architecture.schema.json must be a copy of spec/schemas/policy.schema.json')

# Generated skill reference must match the catalog
sys.path.insert(0, str(ROOT / 'scripts'))
import gen_skill_reference  # noqa: E402

if gen_skill_reference.TARGET.is_file() and gen_skill_reference.TARGET.read_text(
    encoding='utf-8'
) != gen_skill_reference.generate():
    fail('skills/archguard/reference/rules.md is stale; run python3 scripts/gen_skill_reference.py')
elif not gen_skill_reference.TARGET.is_file():
    fail('skills/archguard/reference/rules.md is missing; run python3 scripts/gen_skill_reference.py')

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
