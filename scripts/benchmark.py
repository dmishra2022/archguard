#!/usr/bin/env python3
"""Generate and compile a synthetic repository, then measure the real Maven analysis goal."""
import argparse,json,shutil,subprocess,time
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--maven',default='mvn');p.add_argument('--settings');p.add_argument('--classes',type=int,default=2000);a=p.parse_args()
if a.classes<2: p.error('--classes must be >= 2')
root=Path(__file__).resolve().parents[1];work=root/'.validation/benchmark';work.mkdir(parents=True,exist_ok=True)
src=work/'src/main/java/benchmark/domain'
if src.exists():shutil.rmtree(src)
src.mkdir(parents=True)
for i in range(a.classes):
    reference=(' public N'+str(i+1)+' next;') if i+1<a.classes else ''
    (src/('N'+str(i)+'.java')).write_text('package benchmark.domain; public class N'+str(i)+' {'+reference+' public int value(){return '+str(i)+';} }')
(work/'pom.xml').write_text('<project xmlns="http://maven.apache.org/POM/4.0.0"><modelVersion>4.0.0</modelVersion><groupId>benchmark</groupId><artifactId>scale</artifactId><version>1.0</version><properties><maven.compiler.release>17</maven.compiler.release></properties><build><plugins><plugin><groupId>org.apache.maven.plugins</groupId><artifactId>maven-compiler-plugin</artifactId><version>3.13.0</version></plugin></plugins></build></project>')
(work/'architecture.yml').write_text('schemaVersion: 1\nroots: ["benchmark.."]\nprofiles: [hexagonal]\nroles:\n  DOMAIN: ["benchmark.domain.."]\nrequireClassification: true\n')
cmd=[a.maven,'-B','-ntp']+(['-s',str(Path(a.settings).resolve())]if a.settings else [])
def run(name,args):
    t=time.monotonic();proc=subprocess.run(args,cwd=work,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=900);(work/(name+'.log')).write_text(proc.stdout)
    if proc.returncode:raise RuntimeError(proc.stdout[-4000:])
    return round(time.monotonic()-t,3)
compile_seconds=run('compile',cmd+['clean','compile'])
analysis=cmd+['-o','io.archguard:archguard-maven-plugin:0.1.0:check']
rss=work/'rss.txt'
if Path('/usr/bin/time').exists():analysis=['/usr/bin/time','-f','%M','-o',str(rss)]+analysis
seconds=run('analysis',analysis)
report=json.loads((work/'target/archguard/archguard.json').read_text())
assert report['analyzedClasses']==a.classes and not report['findings']
result={'classes':a.classes,'dependencies':report['dependencies'],'compileSeconds':compile_seconds,'analysisProcessSeconds':seconds,'maxRssKiB':int(rss.read_text().strip())if rss.exists() else None,'note':'Synthetic sparse graph; includes Maven JVM startup; not an SLA or dense-graph benchmark.'}
(work/'result.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
