import { createHash } from 'node:crypto';
import { AnalysisError, ArchitectureModel, Dependency, Finding, Role, Severity } from './model.js';
import { Policy } from './policy.js';
import { matches } from './selectors.js';
import { catalog, fill, forbids } from './spec.js';
import { ENDPOINT_TAGS, moduleMatches } from './frameworks.js';
import { contextOf, roleOf } from './importer.js';

const SOURCE_LOCATION = /\([^()]*\.(?:ts|tsx|mts|cts|js|jsx|mjs|cjs):[0-9]+\)/g;

export function fingerprint(rule: string, d: Dependency): string {
  const semantic = d.evidence.replace(SOURCE_LOCATION, '(source)');
  const key = `${rule}\n${d.location.module}\n${d.origin}\n${d.target}\n${semantic}`;
  return createHash('sha256').update(key, 'utf8').digest('hex');
}

export function active(id: string, p: Policy): boolean {
  const setting = p.rules[id];
  if (setting && setting.enabled !== undefined) return setting.enabled;
  const c = catalog();
  if (c.activatedBy(id, p.profiles)) return true;
  switch (c.rule(id).activation) {
    case 'always':
      return true;
    case 'requireClassification':
      return p.requireClassification;
    default:
      return false;
  }
}

/** Infrastructure entries match the specifier exactly, by `entry/` prefix, or by npm scope (`@x/*`). */
export function isInfrastructure(specifier: string): boolean {
  return moduleMatches(specifier, catalog().infrastructure);
}

/** Strongly connected components with more than one member (iterative Kosaraju, sorted output). */
export function components(input: Map<string, Set<string>>): string[][] {
  const graph = new Map<string, string[]>();
  const reverse = new Map<string, string[]>();
  const vertices = new Set<string>();
  for (const [v, edges] of input) {
    vertices.add(v);
    for (const e of edges) vertices.add(e);
  }
  const sorted = [...vertices].sort(cmp);
  for (const v of sorted) {
    graph.set(v, [...(input.get(v) ?? [])].sort(cmp));
    reverse.set(v, []);
  }
  for (const v of sorted) for (const e of graph.get(v)!) reverse.get(e)!.push(v);
  for (const v of sorted) reverse.get(v)!.sort(cmp);
  const seen = new Set<string>();
  const order: string[] = [];
  for (const start of sorted) {
    if (seen.has(start)) continue;
    seen.add(start);
    const stack: [string, number][] = [[start, 0]];
    while (stack.length) {
      const frame = stack[stack.length - 1];
      const edges = graph.get(frame[0])!;
      if (frame[1] < edges.length) {
        const n = edges[frame[1]++];
        if (!seen.has(n)) {
          seen.add(n);
          stack.push([n, 0]);
        }
      } else {
        order.push(frame[0]);
        stack.pop();
      }
    }
  }
  seen.clear();
  const result: string[][] = [];
  for (const start of order.reverse()) {
    if (seen.has(start)) continue;
    seen.add(start);
    const component: string[] = [];
    const stack = [start];
    while (stack.length) {
      const v = stack.pop()!;
      component.push(v);
      for (const e of reverse.get(v)!) if (!seen.has(e)) (seen.add(e), stack.push(e));
    }
    component.sort(cmp);
    if (component.length > 1) result.push(component);
  }
  return result.sort((a, b) => cmp(a[0], b[0]));
}

function cmp(a: string, b: string): number {
  return a < b ? -1 : a > b ? 1 : 0;
}

function render(list: string[]): string {
  return `[${list.join(', ')}]`;
}

export function evaluate(model: ArchitectureModel, p: Policy): Finding[] {
  const c = catalog();
  const out: Finding[] = [];
  const add = (
    id: string,
    severity: Severity,
    message: string,
    d: Dependency,
    fix: string,
  ): void => {
    if (c.ruleIds.has(id) && !active(id, p)) return;
    const setting = p.rules[id];
    if (setting) {
      if (setting.enabled === false) return;
      if (setting.severity) severity = setting.severity;
    }
    out.push({
      fingerprint: fingerprint(id, d),
      ruleId: id,
      severity,
      message,
      evidence: d.evidence,
      location: d.location,
      target: d.target,
      remediation: fix,
      status: 'NEW',
    });
  };
  const addRule = (id: string, values: Record<string, string>, d: Dependency) => {
    const rule = c.rule(id);
    add(id, rule.defaultSeverity, fill(rule.message, values), d, fill(rule.remediation, values));
  };
  const self = (name: string, evidence: string, location: Dependency['location']): Dependency => ({
    origin: name,
    target: name,
    evidence,
    location,
    kind: 'IMPORT',
    targetContainers: [],
  });

  for (const u of model.units.values()) {
    const roleValues = { role: u.role };
    if (u.role === 'UNCLASSIFIED')
      addRule('MODEL-001', {}, self(u.name, fill(c.rule('MODEL-001').evidence, roleValues), u.location));
    if (u.tags.length > 0) {
      const tags = { tags: render([...u.tags].sort(cmp)) };
      addRule('MODEL-002', tags, self(u.name, fill(c.rule('MODEL-002').evidence, tags), u.location));
    }
    if (u.tags.some((t) => ENDPOINT_TAGS.has(t)) && u.role !== 'INBOUND_ADAPTER' && u.role !== 'UNCLASSIFIED')
      addRule('FW-001', {}, self(u.name, fill(c.rule('FW-001').evidence, roleValues), u.location));
  }

  for (const d of model.dependencies) {
    if (d.kind === 'HTTP_ENTITY_EXPOSURE') {
      addRule('FW-002', {}, d);
      continue;
    }
    const from = model.units.get(d.origin);
    if (!from) continue;
    const to = model.units.get(d.target);
    const targetRole: Role = to ? to.role : roleOf(p, d.targetContainers, d.target, 'target role');
    const infrastructure = d.externalSpecifier !== undefined && isInfrastructure(d.externalSpecifier);
    const boundary = new Set<string>();
    for (const rule of c.roleRules) if (forbids(rule, from.role, targetRole, infrastructure)) boundary.add(rule.rule);
    for (const id of boundary) addRule(id, {}, d);
    const targetContext = to ? to.context : contextOf(p, d.targetContainers, d.target, 'target context');
    if (from.context && targetContext && from.context !== targetContext) {
      const ctx = p.contexts.find((x) => x.id === targetContext)!;
      if (!matches(ctx.exposedPackages, d.targetContainers)) addRule('DDD-001', { targetContext }, d);
    }
    for (const constraint of p.constraints)
      if (matches(constraint.from, from.containers) && matches(constraint.forbidden, d.targetContainers))
        add(constraint.id, constraint.severity, constraint.rationale, d, constraint.remediation);
  }
  if (active('DDD-002', p)) cycleFindings(model, true, addRule);
  if (active('CYCLE-001', p)) cycleFindings(model, false, addRule);
  return out;
}

function cycleFindings(
  m: ArchitectureModel,
  context: boolean,
  addRule: (id: string, values: Record<string, string>, d: Dependency) => void,
): void {
  const graph = new Map<string, Set<string>>();
  const witnesses = new Map<string, Dependency>();
  for (const d of m.dependencies) {
    const a = m.units.get(d.origin);
    const b = m.units.get(d.target);
    if (!a || !b) continue;
    const x = context ? a.context : a.containers[0];
    const y = context ? b.context : b.containers[0];
    if (!x || !y || x === y) continue;
    if (!graph.has(x)) graph.set(x, new Set());
    graph.get(x)!.add(y);
    const key = `${x}\n${y}`;
    if (!witnesses.has(key)) witnesses.set(key, d);
  }
  const id = context ? 'DDD-002' : 'CYCLE-001';
  for (const component of components(graph)) {
    const members = new Set(component);
    const edges: string[] = [];
    let first: Dependency | undefined;
    for (const x of component)
      for (const y of [...(graph.get(x) ?? [])].sort(cmp))
        if (members.has(y)) {
          edges.push(`${x} -> ${y}`);
          first ??= witnesses.get(`${x}\n${y}`);
        }
    if (!first) continue;
    const values = { component: render(component), edges: edges.join(', ') };
    addRule(id, values, {
      origin: first.origin,
      target: first.target,
      evidence: fill(catalog().rule(id).evidence, values),
      location: first.location,
      kind: 'IMPORT',
      targetContainers: first.targetContainers,
    });
  }
}

export function checkRuleIds(p: Policy): void {
  const ids = new Set(catalog().ruleIds);
  for (const constraint of p.constraints) {
    if (ids.has(constraint.id)) throw new AnalysisError(`Duplicate rule ID: ${constraint.id}`);
    ids.add(constraint.id);
  }
  for (const configured of Object.keys(p.rules))
    if (!ids.has(configured)) throw new AnalysisError(`Unknown rule ID: ${configured}`);
}
