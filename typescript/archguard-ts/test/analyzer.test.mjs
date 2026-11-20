import { test } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, mkdirSync, writeFileSync, readFileSync, existsSync, realpathSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join } from 'node:path';
import { run } from '../dist/main.js';
import { matchesOne, validateSelector } from '../dist/selectors.js';

const HEX = `schemaVersion: 2
language: typescript
roots: ["src/**"]
profiles: [hexagonal]
roles:
  DOMAIN: ["src/orders/domain/**"]
  APPLICATION: ["src/orders/application/**"]
  OUTBOUND_PORT: ["src/orders/port/**"]
  OUTBOUND_ADAPTER: ["src/orders/adapter/**"]
allowEmptySelectors: true
`;

function project(files) {
  const root = realpathSync(mkdtempSync(join(tmpdir(), 'archguard-ts-')));
  for (const [name, contents] of Object.entries(files)) {
    const file = join(root, name);
    mkdirSync(dirname(file), { recursive: true });
    writeFileSync(file, contents);
  }
  return root;
}

async function cli(root, ...args) {
  let stdout = '';
  let stderr = '';
  const code = await run(args, {
    cwd: root,
    stdout: (s) => (stdout += s),
    stderr: (s) => (stderr += s),
    stdin: () => '',
  });
  const reportFile = join(root, 'reports/archguard/archguard.json');
  const report = existsSync(reportFile) ? JSON.parse(readFileSync(reportFile, 'utf8')) : undefined;
  return { code, stdout, stderr, report };
}

const rules = (report) => report.findings.filter((f) => f.severity !== 'INFO').map((f) => `${f.ruleId} ${f.location.symbol} -> ${f.target}`).sort();

test('selectors: ** spans zero or more segments, * exactly one', () => {
  assert.ok(matchesOne('src/orders/**', 'src/orders'));
  assert.ok(matchesOne('src/orders/**', 'src/orders/domain/model'));
  assert.ok(!matchesOne('src/orders/**', 'src/ordersx'));
  assert.ok(matchesOne('**/domain/**', 'packages/a/src/domain'));
  assert.ok(matchesOne('src/*/api', 'src/orders/api'));
  assert.ok(!matchesOne('src/*/api', 'src/orders/v1/api'));
  assert.ok(matchesOne('**', ''));
  for (const bad of ['', '/abs/**', './src/**', 'src//x', 'src/../x', 'src/ord*', 'src\\x'])
    assert.throws(() => validateSelector(bad), /Invalid path selector/, bad);
});

test('hexagonal violation via relative import, exit 1 and agent lines', async () => {
  const root = project({
    'architecture.yml': HEX,
    'src/orders/domain/order.ts': 'export class Order {}\n',
    'src/orders/adapter/sql.ts': "import { Order } from '../domain/order';\nexport class Sql { save(o: Order) {} }\n",
    'src/orders/application/place.ts': "import { Sql } from '../adapter/sql';\nexport const s = new Sql();\n",
  });
  const r = await cli(root, 'check', '--format', 'json,agent');
  assert.equal(r.code, 1, r.stderr);
  assert.deepEqual(rules(r.report), ['HEX-002 src/orders/application/place -> src/orders/adapter/sql']);
  const lines = r.stdout.trim().split('\n').map((l) => JSON.parse(l));
  assert.equal(lines[0].file, 'src/orders/application/place.ts');
  assert.equal(lines[0].line, 1);
  assert.deepEqual(lines.at(-1), { summary: true, status: 'FAILED', new: 1, existing: 0, suppressed: 0 });
  assert.match(r.report.findings[0].evidence, /^Module <src\/orders\/application\/place> imports <src\/orders\/adapter\/sql> \(place\.ts:1\)$/);
});

test('fingerprints ignore line movement but not semantic change', async () => {
  const files = {
    'package.json': '{"name":"orders"}',
    'architecture.yml': HEX,
    'src/orders/adapter/sql.ts': 'export class Sql {}\n',
    'src/orders/application/place.ts': "import { Sql } from '../adapter/sql';\nexport const s = Sql;\n",
  };
  const a = await cli(project(files), 'check');
  assert.equal(a.report.findings[0].location.module, 'orders');
  const b = await cli(project({ ...files, 'src/orders/application/place.ts': "\n\n// moved\nimport { Sql } from '../adapter/sql';\nexport const s = Sql;\n" }), 'check');
  assert.equal(a.report.findings[0].fingerprint, b.report.findings[0].fingerprint);
  assert.notEqual(a.report.findings[0].location.line, b.report.findings[0].location.line);
});

test('require, dynamic import, export-from and import type are dependencies; typeOnlyImports: ignore drops type-only', async () => {
  const files = {
    'src/orders/adapter/a.ts': 'export class A {}\n',
    'src/orders/adapter/b.ts': 'export class B {}\n',
    'src/orders/adapter/c.ts': 'export interface C {}\n',
    'src/orders/adapter/d.ts': 'export const d = 1;\n',
    'src/orders/application/use.ts': [
      "const a = require('../adapter/a');",
      "export async function f() { return import('../adapter/b'); }",
      "import type { C } from '../adapter/c';",
      "export { d } from '../adapter/d';",
      "const dyn = 'x'; export const g = () => import(dyn);",
      '',
    ].join('\n'),
  };
  const counted = await cli(project({ 'architecture.yml': HEX, ...files }), 'check');
  assert.deepEqual(rules(counted.report).map((r) => r.split(' -> ')[1]), [
    'src/orders/adapter/a', 'src/orders/adapter/b', 'src/orders/adapter/c', 'src/orders/adapter/d',
  ]);
  assert.ok(counted.report.diagnostics.includes('Computed dynamic imports not analyzed: 1'));
  const ignored = await cli(project({ 'architecture.yml': HEX + 'typeOnlyImports: ignore\n', ...files }), 'check');
  assert.ok(!rules(ignored.report).some((r) => r.endsWith('src/orders/adapter/c')));
  assert.ok(ignored.report.diagnostics.includes('Type-only imports ignored (typeOnlyImports: ignore): 1'));
});

test('asset imports are not dependencies and never unresolved', async () => {
  const root = project({
    'architecture.yml': HEX,
    'src/orders/domain/order.ts': "import './order.css';\nimport logo from '../assets/logo.svg?url';\nimport data from './seed.json';\nexport class Order {}\n",
  });
  const r = await cli(root, 'check');
  assert.equal(r.code, 0, r.stderr);
  assert.equal(r.report.dependencies, 0);
  assert.ok(r.report.diagnostics.includes('Asset imports (styles, media, data files) not treated as dependencies: 3'));
});

test('unresolved owned imports fail by default and warn when configured', async () => {
  const files = {
    'src/orders/domain/order.ts': 'export class Order {}\n',
    'src/orders/application/use.ts': "import { Missing } from '../domain/missing';\nimport express from 'express';\n",
  };
  const failing = await cli(project({ 'architecture.yml': HEX, ...files }), 'check', '--format', 'json,agent');
  assert.equal(failing.code, 2);
  assert.equal(failing.report.analysisStatus, 'FAILED');
  assert.match(failing.report.error, /Unresolved import of an owned module: '..\/domain\/missing' in src\/orders\/application\/use.ts:1/);
  assert.equal(JSON.parse(failing.stdout.trim()).status, 'ERROR');
  const warning = await cli(project({ 'architecture.yml': HEX + 'unresolvedImports: warn\n', ...files }), 'check');
  assert.equal(warning.code, 0, warning.stderr);
  assert.ok(warning.report.diagnostics.some((d) => d.startsWith("Unresolved import '../domain/missing'")));
});

test('domain importing infrastructure packages is HEX-001; scoped entries match the whole scope', async () => {
  const root = project({
    'architecture.yml': HEX,
    'src/orders/domain/order.ts': "import { Repository } from 'typeorm';\nimport { Injectable } from '@nestjs/common';\nimport { readFile } from 'node:fs/promises';\nimport { z } from 'zod';\nexport class Order {}\n",
  });
  const r = await cli(root, 'check');
  assert.deepEqual(rules(r.report), [
    'HEX-001 src/orders/domain/order -> @nestjs/common',
    'HEX-001 src/orders/domain/order -> node:fs',
    'HEX-001 src/orders/domain/order -> typeorm',
  ]);
});

test('workspace packages: selectors by package name, imports resolved to sources without node_modules', async () => {
  const root = project({
    'package.json': JSON.stringify({ name: 'shop', private: true, workspaces: ['packages/*'] }),
    'packages/orders-domain/package.json': JSON.stringify({ name: '@acme/orders-domain', main: 'dist/index.js' }),
    'packages/orders-domain/src/index.ts': "export * from './order';\n",
    'packages/orders-domain/src/order.ts': "import { Db } from '@acme/orders-infra';\nexport class Order {}\n",
    'packages/orders-infra/package.json': JSON.stringify({ name: '@acme/orders-infra' }),
    'packages/orders-infra/src/index.ts': 'export class Db {}\n',
    'architecture.yml': `schemaVersion: 2
language: typescript
sourceRoots: ["packages"]
roots: ["packages/**"]
profiles: [hexagonal]
roles:
  DOMAIN: ["@acme/orders-domain/**"]
  OUTBOUND_ADAPTER: ["@acme/orders-infra/**"]
`,
  });
  const r = await cli(root, 'check');
  assert.equal(r.code, 1, r.stderr);
  assert.deepEqual(rules(r.report), ['HEX-001 packages/orders-domain/src/order -> packages/orders-infra/src/index']);
  assert.equal(r.report.findings.find((f) => f.ruleId === 'HEX-001').location.module, '@acme/orders-domain');
});

test('tsconfig project references are followed for path aliases', async () => {
  const root = project({
    'tsconfig.json': JSON.stringify({ files: [], references: [{ path: './tsconfig.app.json' }] }),
    'tsconfig.app.json': JSON.stringify({ compilerOptions: { composite: true, moduleResolution: 'Bundler', module: 'ESNext', paths: { '~/*': ['./src/*'] } }, include: ['src'] }),
    'architecture.yml': HEX,
    'src/orders/adapter/sql.ts': 'export class Sql {}\n',
    'src/orders/application/place.ts': "import { Sql } from '~/orders/adapter/sql';\nexport const s = Sql;\n",
  });
  const r = await cli(root, 'check');
  assert.deepEqual(rules(r.report), ['HEX-002 src/orders/application/place -> src/orders/adapter/sql']);
});

test('framework tags: Next.js route handlers and Express routers outside inbound adapters are FW-001', async () => {
  const root = project({
    'architecture.yml': `schemaVersion: 2
language: typescript
roots: ["src/**"]
profiles: [hexagonal]
roles:
  APPLICATION: ["src/app/**", "src/service/**"]
  INBOUND_ADAPTER: ["src/http/**"]
`,
    'src/app/orders/route.ts': 'export async function GET() { return Response.json([]); }\n',
    'src/service/routes.ts': "import { Router } from 'express';\nconst r = Router();\nr.get('/orders', (_q, s) => s.json([]));\nexport default r;\n",
    'src/http/routes.ts': "import express from 'express';\nconst app = express();\napp.post('/orders', (_q, s) => s.json({}));\n",
  });
  const r = await cli(root, 'check');
  assert.deepEqual(rules(r.report), ['FW-001 src/app/orders/route -> src/app/orders/route', 'FW-001 src/service/routes -> src/service/routes']);
  const tags = r.report.findings.filter((f) => f.ruleId === 'MODEL-002').map((f) => `${f.location.symbol} ${f.evidence}`);
  assert.deepEqual(tags, [
    'src/app/orders/route Static framework metadata: [next.endpoint]',
    'src/http/routes Static framework metadata: [express.endpoint]',
    'src/service/routes Static framework metadata: [express.endpoint]',
  ]);
});

test('FW-002 follows arrays, unions and parameters to entities', async () => {
  const root = project({
    'tsconfig.json': JSON.stringify({ compilerOptions: { experimentalDecorators: true, strict: true, moduleResolution: 'Bundler', module: 'ESNext' } }),
    'architecture.yml': 'schemaVersion: 2\nlanguage: typescript\nroots: ["src/**"]\n',
    'src/model/user.ts': "import { Entity } from '@mikro-orm/core';\n@Entity()\nexport class User {}\n",
    'src/model/dto.ts': 'export class UserDto {}\n',
    'src/web/users.ts': [
      "import * as nest from '@nestjs/common';",
      "import { User } from '../model/user';",
      "import { UserDto } from '../model/dto';",
      "@nest.Controller('users')",
      'export class Users {',
      "  @nest.Get() list(): Promise<User[] | null> { return Promise.resolve([]); }",
      '  @nest.Post() create(@nest.Body() body: User): UserDto { return new UserDto(); }',
      '  @nest.Get(":id") one(): UserDto { return new UserDto(); }',
      '  helper(): User { return new User(); }',
      '}',
      '',
    ].join('\n'),
  });
  const r = await cli(root, 'check');
  const fw = r.report.findings.filter((f) => f.ruleId === 'FW-002').map((f) => `${f.location.symbol}:${f.location.line}`);
  assert.deepEqual(fw, ['src/web/users#Users.create:7', 'src/web/users#Users.list:6']);
});

test('policy extends: presets merge, locked rules cannot be changed, preset cannot be analyzed', async () => {
  const preset = 'schemaVersion: 2\nkind: preset\nlanguage: typescript\nprofiles: [hexagonal]\nrules:\n  HEX-002:\n    severity: WARNING\n    locked: true\n';
  const files = {
    'policies/base.yml': preset,
    'src/orders/adapter/sql.ts': 'export class Sql {}\n',
    'src/orders/application/place.ts': "import { Sql } from '../adapter/sql';\nexport const s = Sql;\n",
  };
  const child = 'schemaVersion: 2\nextends: ["./policies/base.yml"]\nlanguage: typescript\nroots: ["src/**"]\nroles:\n  APPLICATION: ["src/orders/application/**"]\n  OUTBOUND_ADAPTER: ["src/orders/adapter/**"]\n';
  const ok = await cli(project({ ...files, 'architecture.yml': child }), 'check');
  assert.equal(ok.code, 0, ok.stderr);
  assert.equal(ok.report.findings.find((f) => f.ruleId === 'HEX-002').severity, 'WARNING');
  const locked = await cli(project({ ...files, 'architecture.yml': child + 'rules:\n  HEX-002:\n    severity: ERROR\n' }), 'validate');
  assert.equal(locked.code, 2);
  assert.match(locked.stderr, /Rule HEX-002 is locked by an extended preset/);
  const direct = await cli(project({ ...files, 'architecture.yml': preset }), 'validate');
  assert.equal(direct.code, 2);
  const java = await cli(project({ ...files, 'architecture.yml': 'schemaVersion: 1\nroots: ["a.."]\n' }), 'validate');
  assert.match(java.stderr, /schemaVersion 1 policies are Java-only/);
  const org = await cli(project({ ...files, 'architecture.yml': 'schemaVersion: 2\nextends: ["org:acme/base@1.0.0"]\nlanguage: typescript\nroots: ["src/**"]\n' }), 'validate');
  assert.match(org.stderr, /Policy preset package not installed: @acme\/archguard-presets/);
});

test('org presets resolve from an installed @<org>/archguard-presets package', async () => {
  const root = project({
    'node_modules/@acme/archguard-presets/package.json': JSON.stringify({ name: '@acme/archguard-presets', version: '1.0.0' }),
    'node_modules/@acme/archguard-presets/presets/base/1.0.0.yml': 'schemaVersion: 2\nkind: preset\nlanguage: typescript\nprofiles: [hexagonal]\nfailOn: WARNING\n',
    'architecture.yml': 'schemaVersion: 2\nextends: ["org:acme/base@1.0.0"]\nlanguage: typescript\nroots: ["src/**"]\n',
    'src/a.ts': 'export const a = 1;\n',
  });
  const r = await cli(root, 'validate');
  assert.equal(r.code, 0, r.stderr);
});

test('validation errors: ambiguous roles, empty selectors, unknown rule IDs, vacuous analysis', async () => {
  const src = { 'src/orders/domain/order.ts': 'export class Order {}\n' };
  const ambiguous = await cli(project({ ...src, 'architecture.yml': 'schemaVersion: 2\nlanguage: typescript\nroots: ["src/**"]\nroles:\n  DOMAIN: ["src/**"]\n  APPLICATION: ["src/orders/**"]\n' }), 'check');
  assert.match(ambiguous.report.error, /Ambiguous role mapping for src\/orders\/domain\/order/);
  const empty = await cli(project({ ...src, 'architecture.yml': 'schemaVersion: 2\nlanguage: typescript\nroots: ["src/**"]\nroles:\n  DOMAIN: ["src/nothing/**"]\n' }), 'check');
  assert.match(empty.report.error, /Empty selector for role DOMAIN/);
  const unknown = await cli(project({ ...src, 'architecture.yml': 'schemaVersion: 2\nlanguage: typescript\nroots: ["src/**"]\nrules:\n  NOPE-1:\n    enabled: true\n' }), 'check');
  assert.match(unknown.report.error, /Unknown rule ID: NOPE-1/);
  const vacuous = await cli(project({ ...src, 'architecture.yml': 'schemaVersion: 2\nlanguage: typescript\nroots: ["lib/**"]\n' }), 'check');
  assert.match(vacuous.report.error, /refusing a vacuous pass/);
  const dup = await cli(project({ ...src, 'architecture.yml': 'schemaVersion: 2\nlanguage: typescript\nlanguage: typescript\nroots: ["src/**"]\n' }), 'check');
  assert.equal(dup.code, 2);
});

test('constraints match external packages and internal paths', async () => {
  const root = project({
    'architecture.yml': `schemaVersion: 2
language: typescript
roots: ["src/**"]
constraints:
  - id: ACME-001
    from: ["src/orders/**"]
    forbidden: ["lodash", "src/legacy/**"]
    severity: WARNING
    rationale: Orders must not use lodash or legacy code
    remediation: Use the standard library and the new modules
failOn: WARNING
`,
    'src/legacy/old.ts': 'export const old = 1;\n',
    'src/orders/a.ts': "import _ from 'lodash/fp';\nimport { old } from '../legacy/old';\nexport const x = [_, old];\n",
  });
  const r = await cli(root, 'check');
  assert.equal(r.code, 1);
  assert.deepEqual(rules(r.report), ['ACME-001 src/orders/a -> lodash', 'ACME-001 src/orders/a -> src/legacy/old']);
});

test('cycles: CYCLE-001 witness and edges', async () => {
  const root = project({
    'architecture.yml': 'schemaVersion: 2\nlanguage: typescript\nroots: ["src/**"]\nprofiles: [clean]\n',
    'src/a/x.ts': "import { y } from '../b/y';\nexport const x = () => y;\n",
    'src/b/y.ts': "import { z } from '../c/z';\nexport const y = () => z;\n",
    'src/c/z.ts': "import { x } from '../a/x';\nexport const z = () => x;\n",
  });
  const r = await cli(root, 'check');
  const cycle = r.report.findings.find((f) => f.ruleId === 'CYCLE-001');
  assert.equal(cycle.message, 'Dependency cycle among packages: [src/a, src/b, src/c]');
  assert.equal(cycle.evidence, 'Strongly connected packages: src/a -> src/b, src/b -> src/c, src/c -> src/a');
  assert.equal(cycle.location.symbol, 'src/a/x');
  assert.equal(cycle.target, 'src/b/y');
});

test('baseline, newOnly, suppressions and changed files', async () => {
  const root = project({
    'architecture.yml': HEX + 'newOnly: true\n',
    'src/orders/adapter/sql.ts': 'export class Sql {}\n',
    'src/orders/application/place.ts': "import { Sql } from '../adapter/sql';\nexport const s = Sql;\n",
  });
  const base = await cli(root, 'baseline');
  assert.equal(base.code, 0, base.stderr);
  const baseline = JSON.parse(readFileSync(join(root, 'architecture-baseline.json'), 'utf8'));
  assert.equal(baseline.fingerprints.length, 1);
  assert.equal((await cli(root, 'baseline')).code, 2, 'refuses to overwrite');
  const gated = await cli(root, 'check', '--baseline', 'architecture-baseline.json');
  assert.equal(gated.code, 0);
  assert.equal(gated.report.findings[0].status, 'EXISTING');

  writeFileSync(join(root, 'src/orders/application/other.ts'), "import { Sql } from '../adapter/sql';\nexport const o = Sql;\n");
  const fresh = await cli(root, 'check', '--baseline', 'architecture-baseline.json');
  assert.equal(fresh.code, 1);
  const newOne = fresh.report.findings.find((f) => f.status === 'NEW');

  writeFileSync(join(root, 'changed.txt'), 'src/orders/application/place.ts\n');
  const scoped = await cli(root, 'check', '--baseline', 'architecture-baseline.json', '--changed-files', 'changed.txt');
  assert.equal(scoped.code, 0);
  assert.ok(scoped.report.diagnostics.includes('Changed-files scope: 1 file(s); 1 finding(s) outside the list not reported'));

  const suppressions = { schemaVersion: 1, entries: [{ fingerprint: newOne.fingerprint, owner: 'team-orders', reason: 'migration', expires: '2999-01-01' }] };
  writeFileSync(join(root, 'suppressions.json'), JSON.stringify(suppressions));
  const suppressed = await cli(root, 'check', '--baseline', 'architecture-baseline.json', '--suppressions', 'suppressions.json');
  assert.equal(suppressed.code, 0);
  assert.equal(suppressed.report.findings.find((f) => f.fingerprint === newOne.fingerprint).status, 'SUPPRESSED');

  suppressions.entries[0].expires = '2000-01-01';
  writeFileSync(join(root, 'suppressions.json'), JSON.stringify(suppressions));
  const expired = await cli(root, 'check', '--suppressions', 'suppressions.json');
  assert.equal(expired.code, 2);
  assert.match(expired.report.error, /Expired suppression/);

  writeFileSync(join(root, 'architecture.yml'), HEX + 'newOnly: true\nfailOn: WARNING\n');
  const changedPolicy = await cli(root, 'check', '--baseline', 'architecture-baseline.json');
  assert.equal(changedPolicy.code, 2);
  assert.match(changedPolicy.report.error, /Baseline schema, engine or policy does not match/);
});

test('CLI usage errors exit 64; reports never leave a stale pass', async () => {
  const root = project({ 'architecture.yml': HEX, 'src/orders/domain/order.ts': 'export class Order {}\n' });
  assert.equal((await cli(root)).code, 64);
  assert.equal((await cli(root, 'check', '--bogus')).code, 64);
  assert.equal((await cli(root, 'check', '--format', 'xml')).code, 64);
  assert.equal((await cli(root, 'check', '--fail-on', 'LOW')).code, 64);
  const ok = await cli(root, 'check', '--format', 'json,sarif,html');
  assert.equal(ok.code, 0, ok.stderr);
  const sarif = JSON.parse(readFileSync(join(root, 'reports/archguard/archguard.sarif'), 'utf8'));
  assert.equal(sarif.runs[0].invocations[0].executionSuccessful, true);
  writeFileSync(join(root, 'architecture.yml'), 'schemaVersion: 2\n');
  const broken = await cli(root, 'check');
  assert.equal(broken.code, 2);
  assert.equal(broken.report.analysisStatus, 'FAILED');
  const failedSarif = JSON.parse(readFileSync(join(root, 'reports/archguard/archguard.sarif'), 'utf8'));
  assert.equal(failedSarif.runs[0].invocations[0].executionSuccessful, false);
  assert.match(readFileSync(join(root, 'reports/archguard/index.html'), 'utf8'), /Analysis failed/);
});

test('test files, declaration files and build output are not analyzed', async () => {
  const root = project({
    'architecture.yml': HEX,
    'src/orders/domain/order.ts': 'export class Order {}\n',
    'src/orders/domain/order.spec.ts': "import { Sql } from '../adapter/sql';\n",
    'src/orders/domain/__tests__/x.ts': "import { Sql } from '../../adapter/sql';\n",
    'src/orders/domain/types.d.ts': "import { Sql } from '../adapter/sql';\n",
    'src/orders/adapter/sql.ts': 'export class Sql {}\n',
    'package.json': '{"name":"p"}',
    'dist/orders/domain/order.js': "require('../adapter/sql');\n",
  });
  const r = await cli(root, 'check');
  assert.equal(r.code, 0, r.stderr);
  assert.equal(r.report.analyzedClasses, 2);
});
