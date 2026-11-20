#!/usr/bin/env python3
"""Check that an organisation preset resolves the same way in the Java, TypeScript and Python analyzers.

The preset under presets/acme is packaged as each ecosystem publishes it (a jar, an npm tarball and a
wheel) and installed the way a project would consume it. For every language the check asserts:
- `extends: ["org:acme/base@1.0.0"]` resolves, and its settings take effect: the preset's
  `requireClassification: true` makes an unclassified unit fail `check` (MODEL-001), while the same
  project without the preset passes;
- a project cannot override a locked rule (exit 2);
- a missing preset package or version is an analysis error (exit 2).
The policy hash covers the `extends` references themselves, so it is not compared across reference forms.

Usage: python3 scripts/preset_check.py [--language java|typescript|python ...]
Needs the built analyzers (archguard-cli jar, typescript/archguard-ts/dist) plus Maven, npm and pip.
"""
import argparse
import glob
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PRESET_DIR = ROOT / 'presets' / 'acme'
PRESET_FILE = PRESET_DIR / 'presets' / 'base' / '1.0.0.yml'
HASH = re.compile(r'policyHash ([0-9a-f]{64})')
ROOTS = {'java': 'com.acme.orders.**', 'python': 'orders.**', 'typescript': 'src/**'}
SOURCES = {
    'java': {'src/com/acme/orders/Order.java': 'package com.acme.orders;\npublic class Order {}\n'},
    'python': {'orders/__init__.py': '', 'orders/order.py': 'class Order:\n    pass\n'},
    'typescript': {'src/orders/order.ts': 'export class Order {}\n'},
}


def run(command, **kwargs):
    return subprocess.run(command, capture_output=True, text=True, **kwargs)


def policy(language, extends=None, extra=''):
    parent = f'extends: ["{extends}"]\n' if extends else ''
    return (f'schemaVersion: 2\nlanguage: {language}\n{parent}'
            f'roots: ["{ROOTS[language]}"]\nprofiles: [hexagonal]\n{extra}')


class Analyzer:
    """Packages the preset for one language, writes a one-unit project and runs the analyzer on it."""

    def __init__(self, language, work):
        self.language, self.work = language, work
        self.project = work / f'project-{language}'
        self.project.mkdir()
        for name, text in SOURCES[language].items():
            (self.project / name).parent.mkdir(parents=True, exist_ok=True)
            (self.project / name).write_text(text)
        self.check_args = []
        getattr(self, f'_install_{language}')()

    def _install_java(self):
        jars = [j for j in glob.glob(str(ROOT / 'archguard-cli' / 'target' / 'archguard-cli-*.jar')) if 'original' not in j]
        if not jars:
            raise SystemExit('archguard-cli jar missing; run mvn -pl archguard-cli -am package -DskipTests')
        build = self.work / 'preset-src'
        shutil.copytree(PRESET_DIR, build, ignore=shutil.ignore_patterns('target', 'build', '*.egg-info', 'node_modules'))
        built = run(['mvn', '-B', '-q', '-ntp', '-f', str(build / 'pom.xml'), 'package'])
        if built.returncode:
            raise SystemExit('Preset jar build failed:\n' + built.stdout + built.stderr)
        compiled = run(['javac', '-d', str(self.project / 'classes'), str(self.project / 'src/com/acme/orders/Order.java')])
        if compiled.returncode:
            raise SystemExit('javac failed:\n' + compiled.stderr)
        (self.project / 'archguard.classpath').write_text('module=com.acme:orders\nclasses=classes\nsource=src\n')
        self.cli = ['java', '-jar', jars[0]]
        self.shared = ['--extension', str(build / 'target' / 'archguard-presets-1.0.0.jar')]
        self.check_args = ['--project', str(self.project), '--classpath-file', str(self.project / 'archguard.classpath')]

    def _install_typescript(self):
        cli = ROOT / 'typescript' / 'archguard-ts' / 'dist' / 'cli.js'
        if not cli.is_file():
            raise SystemExit(f'{cli} missing; run npm ci && npm run build in typescript/archguard-ts')
        packed = run(['npm', 'pack', '--silent', '--pack-destination', str(self.work), str(PRESET_DIR)])
        if packed.returncode:
            raise SystemExit('npm pack failed:\n' + packed.stderr)
        tarball = self.work / packed.stdout.strip().splitlines()[-1]
        (self.project / 'package.json').write_text('{"name": "orders", "private": true}\n')
        installed = run(['npm', 'install', '--silent', '--no-audit', '--no-fund', str(tarball)], cwd=self.project)
        if installed.returncode:
            raise SystemExit('npm install of the preset failed:\n' + installed.stderr)
        self.cli = ['node', str(cli)]
        self.shared = ['--project', str(self.project)]

    def _install_python(self):
        site = self.work / 'site'
        installed = run([sys.executable, '-m', 'pip', 'install', '-q', '--disable-pip-version-check', '--no-deps',
                         '--target', str(site), str(PRESET_DIR)])
        if installed.returncode:
            raise SystemExit('pip install of the preset failed:\n' + installed.stdout + installed.stderr)
        for leftover in PRESET_DIR.glob('*.egg-info'):
            shutil.rmtree(leftover)
        shutil.rmtree(PRESET_DIR / 'build', ignore_errors=True)
        self.env = dict(os.environ, PYTHONPATH=os.pathsep.join([str(site), str(ROOT / 'python' / 'archguard-py' / 'src')]))
        self.cli = [sys.executable, '-m', 'archguard']
        self.shared = ['--project', str(self.project)]

    def run(self, command, text, name):
        file = self.project / name
        file.write_text(text)
        extra = self.check_args + ['--out', str(self.work / 'reports' / name), '--format', 'json'] if command == 'check' else []
        result = run(self.cli + [command] + self.shared + extra + ['--config', str(file)], env=getattr(self, 'env', None))
        return result.returncode, (result.stdout + result.stderr).strip()

    def validate(self, text, name):
        code, out = self.run('validate', text, name)
        match = HASH.search(out)
        return code, match.group(1) if match else None, out


def check(language, work):
    analyzer = Analyzer(language, work)
    problems = []

    code, org_hash, out = analyzer.validate(policy(language, 'org:acme/base@1.0.0'), 'org.yml')
    if code != 0:
        problems.append(f'org preset did not resolve (exit {code}): {out}')
    code, out = analyzer.run('check', policy(language, 'org:acme/base@1.0.0'), 'org-check.yml')
    report = work / 'reports' / 'org-check.yml' / 'archguard.json'
    if code != 1 or 'MODEL-001' not in (report.read_text() if report.is_file() else ''):
        problems.append(f'preset requireClassification did not make the unclassified unit fail (exit {code}): {out[-400:]}')
    code, out = analyzer.run('check', policy(language), 'no-preset.yml')
    if code != 0:
        problems.append(f'the same project without the preset should pass (exit {code}): {out[-400:]}')

    code, _, out = analyzer.validate(policy(language, 'org:acme/base@1.0.0', 'rules:\n  FW-002:\n    severity: WARNING\n'), 'locked.yml')
    if code != 2 or 'locked' not in out:
        problems.append(f'overriding a locked rule was not rejected (exit {code}): {out}')

    code, _, out = analyzer.validate(policy(language, 'org:nobody/base@1.0.0'), 'missing-package.yml')
    if code != 2:
        problems.append(f'missing preset package was not an error (exit {code}): {out}')
    code, _, out = analyzer.validate(policy(language, 'org:acme/base@9.9.9'), 'missing-version.yml')
    if code != 2:
        problems.append(f'missing preset version was not an error (exit {code}): {out}')
    return org_hash, problems


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--language', action='append', choices=sorted(ROOTS))
    languages = parser.parse_args().language or ['java', 'typescript', 'python']
    failures = 0
    with tempfile.TemporaryDirectory() as tmp:
        for language in languages:
            work = Path(tmp) / language
            work.mkdir()
            digest, problems = check(language, work)
            if problems:
                failures += 1
                print(f'FAIL {language}:\n  ' + '\n  '.join(problems))
            else:
                print(f'ok   {language}: org:acme/base@1.0.0 resolved and applied (policy {digest[:12]}), '
                      'locked rule enforced, missing presets rejected')
    sys.exit(1 if failures else 0)


if __name__ == '__main__':
    main()
