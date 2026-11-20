import { existsSync, readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { parse } from 'yaml';
import { LANGUAGE, ROLES, Role, Severity } from './model.js';

export interface RoleRule {
  rule: string;
  from: Set<Role>;
  forbiddenRoles: Set<Role>;
  forbidInfrastructure: boolean;
  crossRoleOnly: boolean;
}

export function forbids(r: RoleRule, origin: Role, target: Role, infrastructure: boolean): boolean {
  if (!r.from.has(origin)) return false;
  const role = r.forbiddenRoles.has(target) && !(r.crossRoleOnly && origin === target);
  return role || (r.forbidInfrastructure && infrastructure);
}

export interface Profile {
  id: string;
  title: string;
  includes: string[];
  activates: Set<string>;
  roleRules: RoleRule[];
}

export interface RuleSpec {
  id: string;
  title: string;
  category: string;
  defaultSeverity: Severity;
  activation: string;
  message: string;
  evidence: string | null;
  remediation: string;
  languages: Set<string>;
}

export function fill(template: string | null, values: Record<string, string>): string {
  if (template == null) return '';
  let out = template;
  for (const [k, v] of Object.entries(values)) out = out.split(`{${k}}`).join(v);
  return out;
}

export interface Catalog {
  specVersion: string;
  profiles: Map<string, Profile>;
  rules: Map<string, RuleSpec>;
  infrastructure: string[];
  roleRules: RoleRule[];
  policySchema: object;
  ruleIds: Set<string>;
  rule(id: string): RuleSpec;
  expand(selected: Iterable<string>): Set<string>;
  activatedBy(ruleId: string, selected: Iterable<string>): boolean;
}

/** The bundled copy (published package) wins; the repository copy is used during development. */
export function specDirectory(): string {
  if (process.env.ARCHGUARD_SPEC_DIR) return process.env.ARCHGUARD_SPEC_DIR;
  const pkg = join(dirname(fileURLToPath(import.meta.url)), '..');
  for (const candidate of [join(pkg, 'spec'), join(pkg, '..', '..', 'spec')])
    if (existsSync(join(candidate, 'index.yml'))) return candidate;
  throw new Error('ArchGuard spec catalog not found next to the package');
}

function yaml(dir: string, name: string): any {
  return parse(readFileSync(join(dir, name), 'utf8'));
}

function roles(values: unknown): Set<Role> {
  const out = new Set<Role>();
  for (const v of (values as string[]) ?? []) {
    if (v !== 'UNCLASSIFIED' && !(ROLES as readonly string[]).includes(v))
      throw new Error(`Unknown role in spec: ${v}`);
    out.add(v as Role);
  }
  return out;
}

let cached: Catalog | undefined;

export function catalog(): Catalog {
  if (cached) return cached;
  const dir = specDirectory();
  const index = yaml(dir, 'index.yml');
  const profiles = new Map<string, Profile>();
  const roleRules: RoleRule[] = [];
  for (const id of [...index.profiles].sort()) {
    const p = yaml(dir, `profiles/${id}.yml`);
    const rr: RoleRule[] = (p.roleRules ?? []).map((r: any) => ({
      rule: r.rule,
      from: roles(r.from),
      forbiddenRoles: roles(r.forbiddenRoles),
      forbidInfrastructure: r.forbidInfrastructure === true,
      crossRoleOnly: r.crossRoleOnly === true,
    }));
    roleRules.push(...rr);
    profiles.set(id, {
      id: p.id,
      title: p.title,
      includes: p.includes ?? [],
      activates: new Set(p.activates ?? []),
      roleRules: rr,
    });
  }
  const rules = new Map<string, RuleSpec>();
  for (const id of [...index.rules].sort()) {
    const r = yaml(dir, `rules/${id}.yml`);
    rules.set(id, {
      id: r.id,
      title: r.title,
      category: r.category,
      defaultSeverity: r.defaultSeverity,
      activation: r.activation,
      message: r.message,
      evidence: r.evidence ?? null,
      remediation: String(r.remediation ?? '').trim(),
      languages: new Set(r.languages ?? []),
    });
  }
  const infrastructure: string[] = yaml(dir, `infrastructure/${LANGUAGE}.yml`).entries ?? [];
  const policySchema = JSON.parse(readFileSync(join(dir, 'schemas/policy.schema.json'), 'utf8'));
  const ruleIds = new Set([...rules.values()].filter((r) => r.languages.has(LANGUAGE)).map((r) => r.id));
  const expand = (selected: Iterable<string>): Set<string> => {
    const out = new Set<string>();
    const work = [...selected];
    while (work.length) {
      const id = work.pop()!;
      const p = profiles.get(id);
      if (!p) throw new Error(`Unknown architecture profile: ${id}`);
      if (!out.has(id)) {
        out.add(id);
        work.push(...p.includes);
      }
    }
    return out;
  };
  cached = {
    specVersion: String(index.specVersion),
    profiles,
    rules,
    infrastructure,
    roleRules,
    policySchema,
    ruleIds,
    rule(id) {
      const r = rules.get(id);
      if (!r) throw new Error(`Unknown catalog rule: ${id}`);
      return r;
    },
    expand,
    activatedBy(ruleId, selected) {
      for (const id of expand(selected)) if (profiles.get(id)!.activates.has(ruleId)) return true;
      return false;
    },
  };
  return cached;
}
