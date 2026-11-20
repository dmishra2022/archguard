#!/usr/bin/env python3
"""Run the ArchGuard conformance suite (spec/conformance) against one analyzer.

Usage: python3 scripts/conformance.py --language java [--engine maven|cli] [--case NAME ...]

Each case is copied to a temporary directory; nothing is written into spec/.
Requires jsonschema. The Java engine requires `mvn install` of this repository first.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parent.parent
CONFORMANCE = ROOT / 'spec' / 'conformance'
FINDINGS_SCHEMA = Draft202012Validator(
    json.loads((ROOT / 'spec/schemas/findings.schema.json').read_text(encoding='utf-8'))
)
VERSION = '0.1.0'

POM = """<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
  <modelVersion>4.0.0</modelVersion>
  <groupId>conformance</groupId>
  <artifactId>{artifact}</artifactId>
  <version>1.0</version>
  <properties>
    <maven.compiler.release>17</maven.compiler.release>
    <project.build.sourceEncoding>UTF-8</project.build.sourceEncoding>
  </properties>
  <dependencies>{dependencies}
  </dependencies>
  <build>
    <plugins>
      <plugin>
        <groupId>org.apache.maven.plugins</groupId>
        <artifactId>maven-compiler-plugin</artifactId>
        <version>3.13.0</version>
      </plugin>
      <plugin>
        <groupId>io.archguard</groupId>
        <artifactId>archguard-maven-plugin</artifactId>
        <version>{version}</version>
        <executions>
          <execution>
            <goals><goal>check</goal></goals>
          </execution>
        </executions>
      </plugin>
    </plugins>
  </build>
</project>
"""


def java_dependencies(expected):
    xml = ''
    for coordinate in expected.get('java', {}).get('dependencies', []):
        group, artifact, version = coordinate.split(':')
        xml += (
            f'\n    <dependency><groupId>{group}</groupId><artifactId>{artifact}</artifactId>'
            f'<version>{version}</version></dependency>'
        )
    return xml


def run_java_maven(case, expected, work):
    (work / 'pom.xml').write_text(
        POM.format(artifact=case, dependencies=java_dependencies(expected), version=VERSION),
        encoding='utf-8',
    )
    process = subprocess.run(
        ['mvn', '-B', '-ntp', 'verify'], cwd=work, text=True, capture_output=True, env=os.environ
    )
    output = process.stdout + process.stderr
    if process.returncode == 0:
        code = 0
    elif 'Architecture analysis failed (not a policy pass)' in output:
        code = 2
    elif 'Architecture policy violated' in output:
        code = 1
    else:
        raise RuntimeError('Maven failed outside ArchGuard:\n' + output[-4000:])
    return code, work / 'target' / 'archguard' / 'archguard.json', output


CLI_JAR = ROOT / 'archguard-cli' / 'target' / f'archguard-cli-{VERSION}.jar'
AGENT_SCHEMA = Draft202012Validator(
    json.loads((ROOT / 'spec/schemas/agent-finding.schema.json').read_text(encoding='utf-8'))
)


def maven_artifact(coordinate):
    group, artifact, version = coordinate.split(':')
    jar = (
        Path.home() / '.m2' / 'repository' / Path(*group.split('.')) / artifact / version
        / f'{artifact}-{version}.jar'
    )
    if not jar.is_file():
        subprocess.run(
            ['mvn', '-B', '-q', '-ntp', 'dependency:get', f'-Dartifact={coordinate}'],
            check=True, capture_output=True,
        )
    return jar


def run_java_cli(case, expected, work):
    """Compile with javac and run the shaded CLI jar; the exit code is used as-is."""
    if not CLI_JAR.is_file():
        raise RuntimeError(f'{CLI_JAR} missing; run mvn install first')
    deps = [str(maven_artifact(c)) for c in expected.get('java', {}).get('dependencies', [])]
    sources = sorted(str(p) for p in (work / 'src/main/java').rglob('*.java'))
    classes = work / 'target' / 'classes'
    javac = ['javac', '-g', '--release', '17', '-d', str(classes)]
    if deps:
        javac += ['-cp', os.pathsep.join(deps)]
    subprocess.run(javac + sources, check=True, capture_output=True, text=True)
    command = [
        'java', '-jar', str(CLI_JAR), 'check', '--project', str(work),
        '--classes', str(classes), '--source-root', str(work / 'src/main/java'),
        '--format', 'json,sarif,html,agent',
    ]
    if deps:
        command += ['--classpath', os.pathsep.join(deps)]
    process = subprocess.run(command, cwd=work, text=True, capture_output=True)
    check_agent_output(process)
    return process.returncode, work / 'target' / 'archguard' / 'archguard.json', process.stderr


TS_CLI = ROOT / 'typescript' / 'archguard-ts' / 'dist' / 'cli.js'


def check_agent_output(process):
    lines = [json.loads(line) for line in process.stdout.splitlines() if line.strip()]
    for line in lines:
        errors = [e.message for e in AGENT_SCHEMA.iter_errors(line)]
        if errors:
            raise RuntimeError(f'agent line violates schema: {line}: {errors}')
    want = {0: 'PASSED', 1: 'FAILED', 2: 'ERROR'}.get(process.returncode)
    if not lines or lines[-1].get('summary') is not True or lines[-1]['status'] != want:
        raise RuntimeError(f'agent summary does not match exit code {process.returncode}')


def run_typescript_cli(case, expected, work):
    """Run the built @archguard/cli on the case sources; the exit code is used as-is."""
    if not TS_CLI.is_file():
        raise RuntimeError(f'{TS_CLI} missing; run npm ci && npm run build in typescript/archguard-ts')
    command = [
        'node', str(TS_CLI), 'check', '--project', str(work),
        '--format', 'json,sarif,html,agent',
    ]
    process = subprocess.run(command, cwd=work, text=True, capture_output=True)
    check_agent_output(process)
    return process.returncode, work / 'reports' / 'archguard' / 'archguard.json', process.stderr


ENGINES = {
    ('java', 'maven'): run_java_maven,
    ('java', 'cli'): run_java_cli,
    ('typescript', 'cli'): run_typescript_cli,
}


def origin(finding):
    """The origin unit: location.symbol minus the member part (Java `(`, Python/TypeScript `#`)."""
    symbol = finding['location']['symbol']
    if '#' in symbol:
        return symbol.split('#')[0]
    if '(' in symbol:
        return symbol.split('(')[0].rsplit('.', 1)[0]
    return symbol


def tuples(report):
    return {
        (f['ruleId'], f['severity'], origin(f), f['target'])
        for f in report['findings']
        if f['severity'] != 'INFO'
    }


def expected_tuples(expected, language):
    return {
        (f['rule'], f['severity'], f['origin'][language], f['target'][language])
        for f in expected['findings']
    }


def check_case(case_dir, language, engine):
    expected = json.loads((case_dir / 'expected.json').read_text(encoding='utf-8'))
    source = case_dir / language
    if not source.is_dir():
        return None, f'no {language} variant'
    with tempfile.TemporaryDirectory(prefix=f'archguard-conf-{case_dir.name}-') as tmp:
        work = Path(tmp) / case_dir.name
        shutil.copytree(source, work)
        code, report_path, output = ENGINES[(language, engine)](case_dir.name, expected, work)
        errors = []
        if code != expected['exitCode']:
            errors.append(f'exit code {code}, expected {expected["exitCode"]}')
        if not report_path.is_file():
            errors.append('archguard.json missing')
            return False, '; '.join(errors)
        report = json.loads(report_path.read_text(encoding='utf-8'))
        schema_errors = [e.message for e in FINDINGS_SCHEMA.iter_errors(report)]
        if schema_errors:
            errors.append('report violates findings schema: ' + '; '.join(schema_errors[:3]))
        if expected['status'] == 'ERROR':
            if report.get('analysisStatus') != 'FAILED':
                errors.append('expected a failure report (analysisStatus FAILED)')
        else:
            if report.get('analysisStatus') == 'FAILED':
                errors.append('unexpected failure report: ' + report.get('error', ''))
            else:
                actual = tuples(report)
                wanted = expected_tuples(expected, language)
                if actual != wanted:
                    errors.append(
                        f'findings differ\n      missing:    {sorted(wanted - actual)}'
                        f'\n      unexpected: {sorted(actual - wanted)}'
                    )
        return not errors, '; '.join(errors)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--language', required=True, choices=['java', 'python', 'typescript'])
    parser.add_argument('--engine', default=None)
    parser.add_argument('--case', action='append')
    args = parser.parse_args()
    engine = args.engine or {'java': 'maven', 'python': 'cli', 'typescript': 'cli'}[args.language]
    if (args.language, engine) not in ENGINES:
        parser.error(f'engine {engine} is not available for {args.language}')
    cases = sorted(p for p in CONFORMANCE.iterdir() if (p / 'expected.json').is_file())
    if args.case:
        cases = [c for c in cases if c.name in args.case]
    failed = skipped = passed = 0
    for case_dir in cases:
        ok, detail = check_case(case_dir, args.language, engine)
        if ok is None:
            skipped += 1
            print(f'SKIP {case_dir.name}: {detail}')
        elif ok:
            passed += 1
            print(f'PASS {case_dir.name}')
        else:
            failed += 1
            print(f'FAIL {case_dir.name}: {detail}')
    print(f'{args.language}/{engine}: {passed} passed, {failed} failed, {skipped} skipped')
    if failed or passed == 0:
        sys.exit(1)


if __name__ == '__main__':
    main()
