#!/usr/bin/env python3
"""Real Maven process tests. Run after mvn clean install. No third-party Python modules."""
import argparse, atexit, hashlib, json, os, shutil, subprocess, time, uuid
from pathlib import Path
import xml.etree.ElementTree as ET
ROOT = Path(__file__).resolve().parents[1]
p = argparse.ArgumentParser()
p.add_argument('--maven', default='mvn')
p.add_argument('--settings')
p.add_argument('--skip-frameworks', action='store_true')
p.add_argument('--offline', action='store_true')
a = p.parse_args()
work = ROOT / '.validation' / ('integration-' + uuid.uuid4().hex[:12])
work.mkdir(parents=True, exist_ok=True)
(work.parent / 'latest-integration.txt').write_text(work.name)
lock = work / 'run.lock'
try:
    descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
except FileExistsError:
    raise SystemExit('Another integration suite owns this workspace. If it was killed, remove .validation/integration.lock after confirming it has stopped.')
with os.fdopen(descriptor, 'w') as handle: handle.write(str(os.getpid()))
atexit.register(lambda: lock.unlink(missing_ok=True))
base = [a.maven, '-B', '-ntp'] + (['-s', str(Path(a.settings).resolve())] if a.settings else []) + (['-o'] if a.offline else [])
goal = 'io.archguard:archguard-maven-plugin:0.1.0:'
results = []
def fixture(name, copy_name=None):
    dest = work / (copy_name or name)
    if dest.exists(): shutil.rmtree(dest)
    shutil.copytree(ROOT / 'examples' / name, dest, ignore=shutil.ignore_patterns('target'))
    return dest
def record(name, directory, args, success=True, text=None):
    started = time.monotonic()
    process = subprocess.run(base + args, cwd=directory, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=900)
    (work / (name + '.log')).write_text(process.stdout)
    ok = (process.returncode == 0) == success and (text is None or text in process.stdout)
    results.append({'name': name, 'passed': ok, 'exitCode': process.returncode, 'seconds': round(time.monotonic()-started, 2)})
    (work / 'results.json').write_text(json.dumps(results, indent=2))
    print(('PASS ' if ok else 'FAIL ') + name, flush=True)
    if not ok: raise AssertionError(name + '\n' + process.stdout[-8000:])
def report(directory): return json.loads((directory / 'target/archguard/archguard.json').read_text())
def source_hash(directory):
    h=hashlib.sha256()
    for file in sorted(directory.rglob('*.java')):
        if 'target' not in file.parts: h.update(file.read_bytes())
    return h.hexdigest()
clean=fixture('clean')
before=source_hash(clean)
record('clean-lifecycle',clean,['clean','verify'])
assert report(clean)['analyzedClasses']==4
assert not report(clean)['findings']
assert source_hash(clean)==before
record('direct-goal',clean,[goal+'check'])
record('offline-goal',clean,['-o',goal+'check'])
bad=fixture('violating')
before=source_hash(bad)
record('violation-fails-build',bad,['clean','verify'],False,'Architecture policy violated')
assert any(f['ruleId']=='HEX-002' for f in report(bad)['findings'])
assert source_hash(bad)==before
assert (bad/'target/archguard/index.html').is_file()
record('analyze-does-not-gate',bad,[goal+'analyze'])
record('baseline-create',bad,[goal+'baseline'])
record('baseline-overwrite-guard',bad,[goal+'baseline'],False,'Baseline already exists')
# Set the new-only gate and regenerate explicitly because policy hash changed.
config=bad/'architecture.yml'
config.write_text(config.read_text().replace('newOnly: false','newOnly: true'))
record('baseline-explicit-update',bad,[goal+'baseline','-Darchguard.overwriteBaseline=true'])
record('baseline-new-only-pass',bad,[goal+'check','-Darchguard.baseline='+str(bad/'architecture-baseline.json')])
assert all(f['status']=='EXISTING' for f in report(bad)['findings'])
new=bad/'src/main/java/example/orders/application/AnotherService.java'
new.write_text('package example.orders.application; public class AnotherService { public example.orders.adapter.SqlOrderStore store; }')
record('new-violation-not-baselined',bad,['compile',goal+'check','-Darchguard.baseline='+str(bad/'architecture-baseline.json')],False,'Architecture policy violated')
record('baseline-still-does-not-mutate',bad,[goal+'check','-Darchguard.baseline='+str(bad/'architecture-baseline.json')],False,'Architecture policy violated')
invalid=fixture('clean','invalid-policy')
(invalid/'architecture.yml').write_text('schemaVersion: 1\nroots: ["example.."]\nunknownKey: true\n')
record('invalid-policy-fails',invalid,['compile',goal+'check'],False,'Architecture analysis failed')
assert report(invalid)['analysisStatus']=='FAILED'
missing=fixture('clean','missing-output')
record('missing-output-fails',missing,[goal+'check'],False,'Missing compiled output')
reactor=fixture('reactor')
record('reactor-parallel',reactor,['-T','2','clean','compile',goal+'check-reactor'])
assert report(reactor)['analyzedClasses']==2
record('reactor-partial-rejected',reactor,['-pl','domain',goal+'check-reactor'],False,'Partial reactor')
record('reactor-partial-acknowledged',reactor,['-pl','domain',goal+'check-reactor','-Darchguard.allowPartialReactor=true'],False,'Empty selector')
# An acknowledged partial build must also have a policy compatible with that scope.
partial=reactor/'partial.yml'
partial.write_text((reactor/'architecture.yml').read_text()+'\nallowEmptySelectors: true\n')
record('reactor-partial-scoped',reactor,['-pl','domain',goal+'check-reactor','-Darchguard.allowPartialReactor=true','-Darchguard.config='+str(partial)])
custom=fixture('custom-rule')
record('custom-rule-pack-build',custom,['clean','install'])
consumer=fixture('clean','custom-consumer')
pom=consumer/'pom.xml'
ns = 'http://maven.apache.org/POM/4.0.0'
ET.register_namespace('', ns)
tree = ET.parse(pom)
plugin = next(node for node in tree.findall('.//{' + ns + '}plugin') if node.findtext('{' + ns + '}artifactId') == 'archguard-maven-plugin')
dependencies = ET.SubElement(plugin, '{' + ns + '}dependencies')
dependency = ET.SubElement(dependencies, '{' + ns + '}dependency')
for key, value in [('groupId', 'example'), ('artifactId', 'company-rules'), ('version', '1.0')]:
    ET.SubElement(dependency, '{' + ns + '}' + key).text = value
tree.write(pom, encoding='unicode', xml_declaration=True)
(consumer/'src/main/java/example/orders/application/Shutdown.java').write_text('package example.orders.application; public class Shutdown { public void stop(){ System.exit(1); } }')
record('custom-rule-spi-loaded',consumer,['clean','verify'],False,'COMPANY-001')
assert any(f['ruleId']=='COMPANY-001' for f in report(consumer)['findings'])
if not a.skip_frameworks:
    for framework in ['spring-boot','quarkus','spring-boot-legacy','quarkus-legacy','micronaut']:
        app=fixture(framework)
        record(framework+'-package-check',app,['clean','verify'])
        assert any(f['ruleId']=='MODEL-002' for f in report(app)['findings'])
        assert not any(f['severity']=='ERROR' for f in report(app)['findings'])
        record(framework+'-offline-check',app,['-o',goal+'check'])
print(str(len(results))+' Maven integration scenarios passed. Logs: '+str(work),flush=True)
