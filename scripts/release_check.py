#!/usr/bin/env python3
"""Check that every analyzer and integration declares the same ArchGuard version.

Usage: python3 scripts/release_check.py [expected-version]   (for example 0.2.0, or a tag v0.2.0)
"""
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
POM = '{http://maven.apache.org/POM/4.0.0}'


def pom_version(path):
    project = ET.parse(path).getroot()
    version = project.find(f'{POM}version')
    if version is None:
        version = project.find(f'{POM}parent/{POM}version')
    return version.text.strip()


def search(path, pattern):
    match = re.search(pattern, (ROOT / path).read_text(encoding='utf-8'), re.MULTILINE)
    return match.group(1) if match else '<missing>'


def declared():
    versions = {'pom.xml': pom_version(ROOT / 'pom.xml')}
    for module in sorted(ROOT.glob('archguard-*/pom.xml')):
        versions[str(module.relative_to(ROOT))] = pom_version(module)
    lock = json.loads((ROOT / 'typescript/archguard-ts/package-lock.json').read_text(encoding='utf-8'))
    versions.update({
        'ArchitectureEngine.VERSION': search('archguard-core/src/main/java/io/archguard/engine/ArchitectureEngine.java',
                                             r'String VERSION = "([^"]+)"'),
        'typescript package.json': json.loads((ROOT / 'typescript/archguard-ts/package.json').read_text())['version'],
        'typescript package-lock.json': lock['version'],
        'typescript model.ts VERSION': search('typescript/archguard-ts/src/model.ts', r"VERSION = '([^']+)'"),
        'python pyproject.toml': search('python/archguard-py/pyproject.toml', r'^version = "([^"]+)"'),
        'python model.py VERSION': search('python/archguard-py/src/archguard/model.py', r"^VERSION = '([^']+)'"),
        'action.yml archguard-version': search('action/action.yml', r'archguard-version:\n(?:.*\n)*?\s+default: "([^"]+)"'),
        'action/run.sh default': search('action/run.sh', r'INPUT_ARCHGUARD_VERSION:-([^}]+)\}'),
        'skill check.sh default': search('skills/archguard/scripts/check.sh', r'ARCHGUARD_VERSION:-([^}]+)\}'),
        'scripts/conformance.py': search('scripts/conformance.py', r"^VERSION = '([^']+)'"),
    })
    return versions


def main():
    expected = sys.argv[1].lstrip('v') if len(sys.argv) > 1 else None
    versions = declared()
    reference = expected or versions['pom.xml']
    wrong = {k: v for k, v in versions.items() if v != reference}
    if wrong:
        print(f'Version mismatch (expected {reference}):')
        for name, version in wrong.items():
            print(f'  {name}: {version}')
        sys.exit(1)
    print(f'All {len(versions)} version declarations are {reference}.')


if __name__ == '__main__':
    main()
