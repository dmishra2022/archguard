import { createHash } from 'node:crypto';
import { existsSync, readFileSync, statSync } from 'node:fs';
import { dirname, isAbsolute, join, resolve } from 'node:path';
import { createRequire } from 'node:module';
import { parseDocument } from 'yaml';
import { LANGUAGE, ROLES, Role, Severity, VERSION } from './model.js';
import { catalog } from './spec.js';
import { validateSelector } from './selectors.js';

export interface Context {
  id: string;
  packages: string[];
  exposedPackages: string[];
}

export interface Constraint {
  id: string;
  from: string[];
  forbidden: string[];
  severity: Severity;
  rationale: string;
  remediation: string;
}

export interface RuleSetting {
  enabled?: boolean;
  severity?: Severity;
  locked?: boolean;
}

export interface Policy {
  schemaVersion: 2;
  language: string;
  extends: string[];
  roots: string[];
  sourceRoots: string[] | null;
  profiles: string[];
  roles: Partial<Record<Exclude<Role, 'UNCLASSIFIED'>, string[]>>;
  contexts: Context[];
  constraints: Constraint[];
  rules: Record<string, RuleSetting>;
  typeOnlyImports: 'count' | 'ignore';
  unresolvedImports: 'fail' | 'warn';
  failOn: Severity;
  newOnly: boolean;
  requireClassification: boolean;
  allowEmptySelectors: boolean;
  allowEmptyAnalysis: boolean;
}

const MAX_BYTES = 1_048_576;
const MAX_DEPTH = 16;
const PRESET = /^org:([A-Za-z0-9_.-]+)\/([A-Za-z0-9_.-]+)@([0-9][A-Za-z0-9.+-]*)$/;

type Tree = Record<string, unknown>;

function isObject(v: unknown): v is Tree {
  return typeof v === 'object' && v !== null && !Array.isArray(v);
}

function rejectNulls(v: unknown): void {
  if (v === null || v === undefined)
    throw new Error('Explicit null configuration values are not allowed');
  if (Array.isArray(v)) v.forEach(rejectNulls);
  else if (isObject(v)) Object.values(v).forEach(rejectNulls);
}

function readTree(file: string): Tree {
  if (!existsSync(file)) throw new Error(`Policy not found: ${file}`);
  if (statSync(file).size > MAX_BYTES) throw new Error(`Policy exceeds 1 MiB: ${file}`);
  const doc = parseDocument(readFileSync(file, 'utf8'), { uniqueKeys: true, prettyErrors: false });
  if (doc.errors.length) throw new Error(`Invalid YAML in ${file}: ${doc.errors[0].message}`);
  const tree = doc.toJS({ maxAliasCount: 100 });
  rejectNulls(tree);
  if (!isObject(tree)) throw new Error(`Policy must be a mapping: ${file}`);
  return tree;
}

/**
 * Resolves an org preset from installed npm packages: org:<org>/<name>@<version> loads
 * presets/<name>/<version>.yml from the package @<org>/archguard-presets.
 */
function presetFile(reference: string, projectRoot: string): string {
  const m = PRESET.exec(reference);
  if (!m) throw new Error(`Invalid preset reference: ${reference}`);
  const [, org, name, version] = m;
  const pkg = `@${org}/archguard-presets`;
  let root: string;
  try {
    const require = createRequire(join(projectRoot, 'package.json'));
    root = dirname(require.resolve(`${pkg}/package.json`));
  } catch {
    throw new Error(
      `Policy preset package not installed: ${pkg} (for ${reference}). Add it as a devDependency.`,
    );
  }
  const file = join(root, 'presets', name, `${version}.yml`);
  if (!existsSync(file)) throw new Error(`Policy preset not found: ${file}`);
  return file;
}

function parentFile(child: string, reference: string, projectRoot: string): string {
  if (reference.startsWith('org:')) return presetFile(reference, projectRoot);
  if (reference.startsWith('classpath:'))
    throw new Error(`classpath: references are only supported by the Java analyzer: ${reference}`);
  if (isAbsolute(reference)) return reference;
  if (reference.startsWith('./') || reference.startsWith('../'))
    return resolve(dirname(child), reference);
  throw new Error(`Invalid extends reference: ${reference}`);
}

function byId(a: unknown[]): boolean {
  return a.length > 0 && a.every((n) => isObject(n) && typeof n.id === 'string');
}

/** Maps merge by key, lists of objects with an id merge by id, everything else is replaced. */
export function merge(parent: Tree, child: Tree): Tree {
  const out: Tree = structuredClone(parent);
  for (const [k, value] of Object.entries(child)) {
    const existing = out[k];
    if (isObject(existing) && isObject(value)) out[k] = merge(existing, value);
    else if (Array.isArray(existing) && Array.isArray(value) && byId(existing) && byId(value)) {
      const entries = new Map<string, unknown>();
      for (const n of existing) entries.set((n as Tree).id as string, structuredClone(n));
      for (const n of value) entries.set((n as Tree).id as string, structuredClone(n));
      out[k] = [...entries.values()];
    } else out[k] = structuredClone(value);
  }
  return out;
}

function rejectLockedChanges(inherited: Tree, child: Tree, label: string): void {
  const parentRules = isObject(inherited.rules) ? inherited.rules : {};
  const childRules = isObject(child.rules) ? child.rules : {};
  for (const [id, setting] of Object.entries(parentRules)) {
    if (!isObject(setting) || setting.locked !== true) continue;
    const mine = childRules[id];
    if (!isObject(mine)) continue;
    for (const key of ['enabled', 'severity', 'locked'])
      if (key in mine && mine[key] !== setting[key])
        throw new Error(`Rule ${id} is locked by an extended preset; ${label} cannot change '${key}'`);
  }
}

function resolveTree(file: string, projectRoot: string, chain: string[]): Tree {
  if (chain.includes(file))
    throw new Error(`Cyclic policy extends: ${chain.join(' -> ')} -> ${file}`);
  if (chain.length >= MAX_DEPTH) throw new Error('Policy extends too deep');
  const tree = readTree(file);
  if (!('extends' in tree)) return tree;
  if (!Array.isArray(tree.extends)) throw new Error('extends must be a list');
  chain.push(file);
  try {
    let inherited: Tree = {};
    for (const reference of tree.extends as string[]) {
      const parent = resolveTree(parentFile(file, String(reference), projectRoot), projectRoot, chain);
      if (parent.schemaVersion !== 2 || parent.kind !== 'preset')
        throw new Error(`Extended policy must be schemaVersion 2 with kind: preset: ${reference}`);
      if ('language' in tree && 'language' in parent && tree.language !== parent.language)
        throw new Error(`Extended preset language differs: ${reference}`);
      rejectLockedChanges(inherited, parent, String(reference));
      inherited = merge(inherited, parent);
    }
    rejectLockedChanges(inherited, tree, file);
    const merged = merge(inherited, tree);
    delete merged.kind;
    if ('kind' in tree) merged.kind = tree.kind;
    merged.extends = tree.extends;
    return merged;
  } finally {
    chain.pop();
  }
}

let validator: ((data: unknown) => boolean) & { errors?: any[] | null } | undefined;

async function schemaValidator() {
  if (validator) return validator;
  const { default: Ajv2020 } = (await import('ajv/dist/2020.js')) as any;
  const ajv = new Ajv2020({ allErrors: false, strict: false });
  validator = ajv.compile(catalog().policySchema);
  return validator!;
}

function schemaError(errors: any[] | null | undefined): string {
  const e = errors?.[0];
  if (!e) return 'Policy does not match the schema';
  const where = e.instancePath || '(root)';
  if (e.keyword === 'additionalProperties')
    return `Unknown policy key at ${where}: ${e.params.additionalProperty}`;
  return `Policy schema violation at ${where}: ${e.message}`;
}

function id(value: string): void {
  if (!/^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$/.test(value))
    throw new Error(`Invalid identifier: ${value}`);
}

function selectors(list: string[] | undefined, label: string): void {
  if (!list || list.length === 0) throw new Error(`Empty selector list: ${label}`);
  list.forEach(validateSelector);
}

/** Reads, resolves and validates a TypeScript policy (schemaVersion 2, language typescript). */
export async function readPolicy(file: string, projectRoot: string): Promise<Policy> {
  const tree = resolveTree(resolve(file), projectRoot, []);
  const validate = await schemaValidator();
  if (!validate(tree)) throw new Error(schemaError(validate.errors));
  if (tree.schemaVersion !== 2)
    throw new Error(
      'schemaVersion 1 policies are Java-only; use schemaVersion 2 with language: typescript',
    );
  if (tree.kind === 'preset')
    throw new Error('A preset policy cannot be analyzed directly; extend it from a project policy');
  if (tree.language !== LANGUAGE)
    throw new Error(
      `Policy language '${tree.language}' cannot be analyzed by the TypeScript analyzer`,
    );
  const t = tree as any;
  const p: Policy = {
    schemaVersion: 2,
    language: LANGUAGE,
    extends: t.extends ?? [],
    roots: t.roots,
    sourceRoots: t.sourceRoots ?? null,
    profiles: t.profiles ?? [],
    roles: t.roles ?? {},
    contexts: (t.contexts ?? []).map((c: any) => ({
      id: c.id,
      packages: c.packages,
      exposedPackages: c.exposedPackages ?? [],
    })),
    constraints: (t.constraints ?? []).map((c: any) => ({
      id: c.id,
      from: c.from,
      forbidden: c.forbidden,
      severity: c.severity ?? 'ERROR',
      rationale: c.rationale,
      remediation: c.remediation,
    })),
    rules: t.rules ?? {},
    typeOnlyImports: t.typeOnlyImports ?? 'count',
    unresolvedImports: t.unresolvedImports ?? 'fail',
    failOn: t.failOn ?? 'ERROR',
    newOnly: t.newOnly ?? false,
    requireClassification: t.requireClassification ?? false,
    allowEmptySelectors: t.allowEmptySelectors ?? false,
    allowEmptyAnalysis: t.allowEmptyAnalysis ?? false,
  };
  semanticValidate(p);
  return p;
}

export function semanticValidate(p: Policy): void {
  const known = catalog().profiles;
  for (const profile of p.profiles)
    if (!known.has(profile)) throw new Error(`Unknown architecture profile: ${profile}`);
  selectors(p.roots, 'roots');
  for (const [role, list] of Object.entries(p.roles)) {
    if (!(ROLES as readonly string[]).includes(role))
      throw new Error(`${role} cannot be explicitly mapped`);
    selectors(list, `role ${role}`);
  }
  const contexts = new Set<string>();
  for (const c of p.contexts) {
    id(c.id);
    if (contexts.has(c.id)) throw new Error(`Duplicate context: ${c.id}`);
    contexts.add(c.id);
    selectors(c.packages, `context ${c.id}`);
    c.exposedPackages.forEach(validateSelector);
  }
  const constraints = new Set<string>();
  for (const c of p.constraints) {
    id(c.id);
    if (constraints.has(c.id)) throw new Error(`Duplicate constraint: ${c.id}`);
    constraints.add(c.id);
    selectors(c.from, `constraint ${c.id}`);
    selectors(c.forbidden, `constraint ${c.id}`);
    if (!c.rationale?.trim() || !c.remediation?.trim())
      throw new Error('Constraints require rationale and remediation');
  }
  for (const k of Object.keys(p.rules)) id(k);
  if (p.sourceRoots)
    for (const r of p.sourceRoots)
      if (isAbsolute(r) || r.split(/[\\/]/).includes('..'))
        throw new Error(`sourceRoots must be project-relative: ${r}`);
}

function canonical(v: unknown): unknown {
  if (Array.isArray(v)) return v.map(canonical);
  if (isObject(v)) {
    const out: Tree = {};
    for (const k of Object.keys(v).sort()) out[k] = canonical(v[k]);
    return out;
  }
  return v;
}

/** Canonical policy hash bound into baselines (analyzer-specific, spec/FINGERPRINT.md). */
export function policyHash(p: Policy): string {
  const tree = { ...p, profiles: [...new Set(p.profiles)].sort() };
  return createHash('sha256')
    .update(`${VERSION}\n${JSON.stringify(canonical(tree))}`, 'utf8')
    .digest('hex');
}
