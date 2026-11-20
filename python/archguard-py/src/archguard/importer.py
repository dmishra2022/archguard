"""Builds the architecture model of a Python project from static imports (stdlib ``ast``)."""
from __future__ import annotations

import ast
from dataclasses import dataclass, replace
from typing import Dict, FrozenSet, Iterator, List, Optional, Tuple

from .frameworks import Frameworks, annotation_leaves, signature_types
from .index import ModuleInfo, SourceIndex, absolute
from .model import ROLES, UNCLASSIFIED, AnalysisError, Dependency, Location, Model, Unit
from .policy import Policy
from .project import Project
from .selectors import matches
from .spec import catalog

DYNAMIC_IMPORTERS = frozenset({'importlib.import_module', '__import__'})


@dataclass(frozen=True)
class RawImport:
    module: Optional[str]
    names: Tuple[str, ...]
    line: int
    verb: str
    display: str
    is_from: bool


def _single(items: list, error: str):
    if len(items) > 1:
        raise AnalysisError(error)
    return items[0] if items else None


def role_of(policy: Policy, containers: List[str], name: str, label: str = 'role mapping') -> str:
    roles = [r for r in ROLES if r in policy.roles and matches(policy.roles[r], containers)]
    return _single(roles, f"Ambiguous {label} for {name}: [{', '.join(roles)}]") or UNCLASSIFIED


def context_of(policy: Policy, containers: List[str], name: str, label: str = 'context mapping') -> str:
    found = [c for c in policy.contexts if matches(c.packages, containers)]
    hit = _single(found, f'Ambiguous {label} for {name}')
    return hit.id if hit else ''


def _type_checking(test: ast.expr) -> bool:
    return (isinstance(test, ast.Name) and test.id == 'TYPE_CHECKING') or (
        isinstance(test, ast.Attribute) and test.attr == 'TYPE_CHECKING'
    )


def collect_imports(info: ModuleInfo) -> Tuple[List[RawImport], int]:
    """Every import statement (module level, nested, lazy) plus literal dynamic imports."""
    out: List[RawImport] = []
    computed = 0
    package = info.source.package

    def visit(node: ast.AST, type_only: bool) -> None:
        nonlocal computed
        if isinstance(node, ast.If) and _type_checking(node.test):
            for child in node.body:
                visit(child, True)
            for child in node.orelse:
                visit(child, type_only)
            return
        verb = 'imports type' if type_only else 'imports'
        if isinstance(node, ast.Import):
            for a in node.names:
                out.append(RawImport(a.name, (), node.lineno, verb, f'import {a.name}', False))
        elif isinstance(node, ast.ImportFrom):
            target = absolute(package, node.level, node.module)
            display = f"from {'.' * node.level}{node.module or ''} import {', '.join(a.name for a in node.names)}"
            out.append(RawImport(target, tuple(a.name for a in node.names), node.lineno, verb, display, True))
        elif isinstance(node, ast.Call):
            callee = _dotted(node.func)
            if callee in DYNAMIC_IMPORTERS or (callee == 'import_module' and 'import_module' in info.bindings):
                arg = node.args[0] if node.args else None
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str) and not arg.value.startswith('.'):
                    out.append(RawImport(arg.value, (), node.lineno, 'dynamically imports', f"import_module('{arg.value}')", False))
                else:
                    computed += 1
        for child in ast.iter_child_nodes(node):
            visit(child, type_only)

    visit(info.tree, False)
    return out, computed


def _dotted(expr: ast.expr) -> Optional[str]:
    if isinstance(expr, ast.Name):
        return expr.id
    if isinstance(expr, ast.Attribute):
        base = _dotted(expr.value)
        return f'{base}.{expr.attr}' if base else None
    return None


class Resolver:
    def __init__(self, project: Project, infrastructure: FrozenSet[str] = frozenset(),
                 analyzed: FrozenSet[str] = frozenset()):
        self.project = project
        self.infrastructure = infrastructure
        self.analyzed_tops = frozenset(m.split('.')[0] for m in analyzed)
        self.shadowed: set = set()

    def _namespace_top(self, module: str) -> bool:
        """A top-level namespace package (no __init__.py) outside roots, e.g. a local alembic/ migrations
        folder: an installed regular package of the same name takes precedence (PEP 420)."""
        top = module.split('.')[0]
        if top in self.project.namespaces and top not in self.analyzed_tops:
            self.shadowed.add(top)
            return True
        return False

    def resolve(self, module: str) -> Tuple[str, str]:
        """('internal'|'namespace'|'test'|'external'|'unresolved', name)."""
        if module in self.project.modules:
            return 'internal', module
        if module in self.project.namespaces:
            return 'namespace', module
        parts = module.split('.')
        if any('.'.join(parts[:i]) in self.project.test_modules for i in range(1, len(parts) + 1)):
            return 'test', module
        if parts[0] in self.project.owned_tops:
            return ('external', module) if self._namespace_top(module) else ('unresolved', module)
        return 'external', module

    def targets(self, imp: RawImport) -> Iterator[Tuple[str, str]]:
        if imp.module is None:
            yield 'unresolved', imp.display
            return
        if not imp.is_from:
            yield self.resolve(imp.module)
            return
        rest = False
        for name in imp.names:
            child = f'{imp.module}.{name}'
            if name != '*' and child in self.project.modules:
                yield 'internal', child
            elif name != '*' and self.resolve(child)[0] in ('namespace', 'test'):
                yield self.resolve(child)
            elif child in self.infrastructure and self.resolve(imp.module)[0] == 'external':
                yield 'external', child
            else:
                rest = True
        if rest:
            kind, target = self.resolve(imp.module)
            if kind == 'namespace':
                kind = 'external' if self._namespace_top(imp.module) else 'unresolved'
            yield kind, target


def _require_match(units: Dict[str, Unit], patterns: List[str], label: str) -> None:
    if not any(matches(patterns, u.containers) for u in units.values()):
        raise AnalysisError(f'Empty selector for {label}')


def read_model(project: Project, policy: Policy) -> Model:
    index = SourceIndex(project)
    frameworks = Frameworks(index)
    units: Dict[str, Unit] = {}
    infos: Dict[str, ModuleInfo] = {}
    diagnostics = list(project.diagnostics)
    outside = 0
    for sf in project.files:
        if not matches(policy.roots, [sf.module]):
            outside += 1
            continue
        info = index.parse(sf.module)
        infos[sf.module] = info
        path = project.rel(sf.path)
        units[sf.module] = Unit(
            name=sf.module,
            package=sf.package,
            role=role_of(policy, [sf.module], sf.module),
            context=context_of(policy, [sf.module], sf.module),
            tags=frameworks.tags(info),
            location=Location(project.module_id(sf.path), path, sf.module, 0),
            endpoint_line=next((decorator.lineno for _, _, _, decorator in frameworks.handlers(info)), 0),
        )
    if not units and not policy.allowEmptyAnalysis:
        raise AnalysisError('No application modules matched roots; refusing a vacuous pass')
    if not policy.allowEmptySelectors:
        for r in ROLES:
            if r in policy.roles:
                _require_match(units, policy.roles[r], f'role {r}')
        for c in policy.contexts:
            _require_match(units, c.packages, f'context {c.id}')
        for c in policy.constraints:
            _require_match(units, c.from_, f'constraint {c.id}')

    resolver = Resolver(project, frozenset(catalog().infrastructure), frozenset(units))
    dependencies: List[Dependency] = []
    unresolved: List[str] = []
    computed = 0
    type_only_skipped = 0
    namespace_imports = 0
    test_imports = 0
    for name, unit in units.items():
        found, dynamic = collect_imports(infos[name])
        computed += dynamic
        filename = unit.location.path.rpartition('/')[2]
        for imp in found:
            if imp.verb == 'imports type' and policy.typeOnlyImports == 'ignore':
                type_only_skipped += 1
                continue
            for kind, target in resolver.targets(imp):
                if kind == 'namespace':
                    namespace_imports += 1
                    continue
                if kind == 'test':
                    test_imports += 1
                    continue
                if kind == 'unresolved':
                    where = f'{unit.location.path}:{imp.line}'
                    if policy.unresolvedImports == 'fail':
                        raise AnalysisError(
                            f"Unresolved import of an owned module: '{imp.display}' in {where}. "
                            f'Fix the import or set unresolvedImports: warn.'
                        )
                    unresolved.append(f"'{imp.display}' in {where}")
                    continue
                if target == name:
                    continue
                dependencies.append(Dependency(
                    origin=name,
                    target=target,
                    evidence=f'Module <{name}> {imp.verb} <{target}> ({filename}:{imp.line})',
                    location=replace(unit.location, line=imp.line),
                    external_module=target if kind == 'external' else None,
                ))
    dependencies.extend(_http_entity_exposures(units, infos, frameworks))
    dependencies.sort(key=lambda d: (d.origin, d.target, d.evidence))

    diagnostics.append(
        'Static imports only: runtime plugin loading, importlib calls with computed names and '
        'string-based framework references (for example Django INSTALLED_APPS) are not resolved.'
    )
    diagnostics.append(
        f'Type-only imports ignored (typeOnlyImports: ignore): {type_only_skipped}'
        if policy.typeOnlyImports == 'ignore'
        else 'Type-only imports (if TYPE_CHECKING) count as dependencies (typeOnlyImports: count).'
    )
    if computed:
        diagnostics.append(f'Computed dynamic imports not analyzed: {computed}')
    if test_imports:
        diagnostics.append(f'Imports of excluded test modules not treated as dependencies: {test_imports}')
    if resolver.shadowed:
        diagnostics.append(
            f"Top-level namespace packages outside roots: {', '.join(sorted(resolver.shadowed))}; "
            'imports under them that match no source file are treated as external '
            '(an installed package of the same name takes precedence).'
        )
    if namespace_imports:
        diagnostics.append(f'Imports of namespace packages (no module code) not treated as dependencies: {namespace_imports}')
    if unresolved:
        diagnostics.append(f'Unresolved imports ignored (unresolvedImports: warn): {len(unresolved)}')
        diagnostics.extend(f'Unresolved import {u}' for u in unresolved[:20])
    diagnostics.extend(project.module_id_diagnostics())
    unclassified = sum(1 for u in units.values() if u.role == UNCLASSIFIED)
    diagnostics.append(f'Unclassified application modules: {unclassified} / {len(units)}')
    if outside:
        diagnostics.append(f'Source files outside roots (not checked, and their own imports are ignored): {outside}')
    return Model(units, dependencies, diagnostics)


def _http_entity_exposures(units: Dict[str, Unit], infos: Dict[str, ModuleInfo], frameworks: Frameworks) -> List[Dependency]:
    """FW-002: route handler signatures (parameters, return, response_model) naming an ORM entity."""
    out: List[Dependency] = []
    for name, unit in units.items():
        if not any(t in ('fastapi.endpoint', 'flask.endpoint', 'ninja.endpoint') for t in unit.tags):
            continue
        info = infos[name]
        for _, suffix, fn, decorator in frameworks.handlers(info):
            method = f'{name}#{suffix}'
            entities: Dict[str, str] = {}
            for expr in signature_types(fn, decorator):
                for leaf in annotation_leaves(expr):
                    found = frameworks.resolve_class(info, leaf)
                    if found and frameworks.class_kind(found[0], found[1]) == 'entity':
                        entities[f'{found[0].name}#{found[1].name}'] = found[0].name
            for entity, module in sorted(entities.items()):
                out.append(Dependency(
                    origin=name,
                    target=module,
                    evidence=f'HTTP method <{method}> exposes persistence entity <{entity}>',
                    location=Location(unit.location.module, unit.location.path, method, fn.lineno),
                    kind='HTTP_ENTITY_EXPOSURE',
                ))
    return out
