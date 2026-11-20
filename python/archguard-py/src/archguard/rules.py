"""Rule evaluation over the architecture model (same semantics as the Java and TypeScript engines)."""
from __future__ import annotations

import hashlib
import re
from typing import Callable, Dict, List, Optional, Set

from .frameworks import ENDPOINT_TAGS
from .importer import context_of, role_of
from .model import UNCLASSIFIED, AnalysisError, Dependency, Finding, Location, Model
from .policy import Policy
from .selectors import matches
from .spec import catalog, fill

SOURCE_LOCATION = re.compile(r'\([^()]*\.py:[0-9]+\)')


def fingerprint(rule: str, d: Dependency) -> str:
    semantic = SOURCE_LOCATION.sub('(source)', d.evidence)
    key = f'{rule}\n{d.location.module}\n{d.origin}\n{d.target}\n{semantic}'
    return hashlib.sha256(key.encode('utf-8')).hexdigest()


def active(rule_id: str, p: Policy) -> bool:
    setting = p.rules.get(rule_id)
    if setting is not None and 'enabled' in setting:
        return bool(setting['enabled'])
    c = catalog()
    if c.activated_by(rule_id, p.profiles):
        return True
    activation = c.rule(rule_id).activation
    if activation == 'always':
        return True
    if activation == 'requireClassification':
        return p.requireClassification
    return False


def module_matches(module: str, entries: List[str]) -> bool:
    """Infrastructure entries match the imported module exactly or as a parent package."""
    return any(module == e or module.startswith(e + '.') for e in entries)


def is_infrastructure(module: str) -> bool:
    return module_matches(module, catalog().infrastructure)


def components(graph_in: Dict[str, Set[str]]) -> List[List[str]]:
    """Strongly connected components with more than one member (iterative Kosaraju, sorted output)."""
    vertices: Set[str] = set()
    for v, edges in graph_in.items():
        vertices.add(v)
        vertices.update(edges)
    ordered = sorted(vertices)
    graph = {v: sorted(graph_in.get(v, ())) for v in ordered}
    reverse: Dict[str, List[str]] = {v: [] for v in ordered}
    for v in ordered:
        for e in graph[v]:
            reverse[e].append(v)
    for v in ordered:
        reverse[v].sort()
    seen: Set[str] = set()
    order: List[str] = []
    for start in ordered:
        if start in seen:
            continue
        seen.add(start)
        stack = [[start, 0]]
        while stack:
            frame = stack[-1]
            edges = graph[frame[0]]
            if frame[1] < len(edges):
                n = edges[frame[1]]
                frame[1] += 1
                if n not in seen:
                    seen.add(n)
                    stack.append([n, 0])
            else:
                order.append(frame[0])
                stack.pop()
    seen.clear()
    result: List[List[str]] = []
    for start in reversed(order):
        if start in seen:
            continue
        seen.add(start)
        component = []
        work = [start]
        while work:
            v = work.pop()
            component.append(v)
            for e in reverse[v]:
                if e not in seen:
                    seen.add(e)
                    work.append(e)
        component.sort()
        if len(component) > 1:
            result.append(component)
    return sorted(result, key=lambda c: c[0])


def _render(items: List[str]) -> str:
    return '[' + ', '.join(items) + ']'


def evaluate(model: Model, p: Policy) -> List[Finding]:
    c = catalog()
    out: List[Finding] = []

    def add(rule_id: str, severity: str, message: str, d: Dependency, fix: str) -> None:
        if rule_id in c.rule_ids and not active(rule_id, p):
            return
        setting = p.rules.get(rule_id)
        if setting is not None:
            if setting.get('enabled') is False:
                return
            severity = setting.get('severity', severity)
        out.append(Finding(fingerprint(rule_id, d), rule_id, severity, message, d.evidence, d.location, d.target, fix))

    def add_rule(rule_id: str, values: Dict[str, str], d: Dependency) -> None:
        rule = c.rule(rule_id)
        add(rule_id, rule.default_severity, fill(rule.message, values), d, fill(rule.remediation, values))

    def self_dep(name: str, evidence: str, location: Location) -> Dependency:
        return Dependency(name, name, evidence, location)

    for u in model.units.values():
        role_values = {'role': u.role}
        if u.role == UNCLASSIFIED:
            add_rule('MODEL-001', {}, self_dep(u.name, fill(c.rule('MODEL-001').evidence, role_values), u.location))
        if u.tags:
            tags = {'tags': _render(sorted(u.tags))}
            add_rule('MODEL-002', tags, self_dep(u.name, fill(c.rule('MODEL-002').evidence, tags), u.location))
        if any(t in ENDPOINT_TAGS for t in u.tags) and u.role not in ('INBOUND_ADAPTER', UNCLASSIFIED):
            add_rule('FW-001', {}, self_dep(u.name, fill(c.rule('FW-001').evidence, role_values), u.location))

    for d in model.dependencies:
        if d.kind == 'HTTP_ENTITY_EXPOSURE':
            add_rule('FW-002', {}, d)
            continue
        origin = model.units.get(d.origin)
        if origin is None:
            continue
        target = model.units.get(d.target)
        target_role = target.role if target else role_of(p, d.target_containers, d.target, 'target role')
        infrastructure = d.external_module is not None and is_infrastructure(d.external_module)
        boundary = sorted({r.rule for r in c.role_rules if r.forbids(origin.role, target_role, infrastructure)})
        for rule_id in boundary:
            add_rule(rule_id, {}, d)
        target_context = target.context if target else context_of(p, d.target_containers, d.target, 'target context')
        if origin.context and target_context and origin.context != target_context:
            if not matches(p.context(target_context).exposedPackages, d.target_containers):
                add_rule('DDD-001', {'targetContext': target_context}, d)
        for constraint in p.constraints:
            if matches(constraint.from_, origin.containers) and matches(constraint.forbidden, d.target_containers):
                add(constraint.id, constraint.severity, constraint.rationale, d, constraint.remediation)
    if active('DDD-002', p):
        _cycle_findings(model, True, add_rule)
    if active('CYCLE-001', p):
        _cycle_findings(model, False, add_rule)
    return out


def _cycle_findings(m: Model, context: bool, add_rule: Callable[[str, Dict[str, str], Dependency], None]) -> None:
    graph: Dict[str, Set[str]] = {}
    witnesses: Dict[tuple, Dependency] = {}
    for d in m.dependencies:
        a = m.units.get(d.origin)
        b = m.units.get(d.target)
        if a is None or b is None:
            continue
        x = a.context if context else (a.package or a.name)
        y = b.context if context else (b.package or b.name)
        if not x or not y or x == y:
            continue
        graph.setdefault(x, set()).add(y)
        witnesses.setdefault((x, y), d)
    rule_id = 'DDD-002' if context else 'CYCLE-001'
    for component in components(graph):
        members = set(component)
        edges: List[str] = []
        first: Optional[Dependency] = None
        for x in component:
            for y in sorted(graph.get(x, ())):
                if y in members:
                    edges.append(f'{x} -> {y}')
                    if first is None:
                        first = witnesses.get((x, y))
        if first is None:
            continue
        values = {'component': _render(component), 'edges': ', '.join(edges)}
        add_rule(rule_id, values, Dependency(
            first.origin, first.target, fill(catalog().rule(rule_id).evidence, values), first.location,
        ))


def check_rule_ids(p: Policy) -> None:
    ids = set(catalog().rule_ids)
    for constraint in p.constraints:
        if constraint.id in ids:
            raise AnalysisError(f'Duplicate rule ID: {constraint.id}')
        ids.add(constraint.id)
    for configured in p.rules:
        if configured not in ids:
            raise AnalysisError(f'Unknown rule ID: {configured}')
