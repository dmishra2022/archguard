"""Framework classification of Python modules by static name resolution (no imports are executed)."""
from __future__ import annotations

import ast
from typing import Dict, Iterator, List, Optional, Sequence, Set, Tuple

from .index import ModuleInfo, SourceIndex

ENDPOINT_TAGS = frozenset({'fastapi.endpoint', 'flask.endpoint', 'django.endpoint', 'ninja.endpoint'})

DECLARATIVE_BASES = frozenset({
    'sqlalchemy.orm.DeclarativeBase',
    'sqlalchemy.orm.DeclarativeBaseNoMeta',
    'sqlalchemy.orm.decl_api.DeclarativeBase',
    'sqlalchemy.orm.decl_api.DeclarativeBaseNoMeta',
})
DECLARATIVE_FACTORIES = frozenset({
    'sqlalchemy.orm.declarative_base',
    'sqlalchemy.orm.decl_api.declarative_base',
    'sqlalchemy.ext.declarative.declarative_base',
})
MODEL_BASES = frozenset({
    'django.db.models.Model',
    'django.db.models.base.Model',
    'tortoise.models.Model',
    'tortoise.Model',
    'peewee.Model',
    'mongoengine.Document',
    'mongoengine.document.Document',
    'beanie.Document',
    'odmantic.Model',
})
FLASK_SQLALCHEMY = frozenset({'flask_sqlalchemy.SQLAlchemy', 'flask_sqlalchemy.extension.SQLAlchemy'})
PYDANTIC_BASES = frozenset({'pydantic.BaseModel', 'pydantic.main.BaseModel', 'ninja.Schema', 'ninja.schema.Schema'})

ROUTERS = {
    'fastapi.FastAPI': 'fastapi',
    'fastapi.APIRouter': 'fastapi',
    'fastapi.applications.FastAPI': 'fastapi',
    'fastapi.routing.APIRouter': 'fastapi',
    'flask.Flask': 'flask',
    'flask.Blueprint': 'flask',
    'flask.app.Flask': 'flask',
    'flask.blueprints.Blueprint': 'flask',
    'quart.Quart': 'flask',
    'quart.Blueprint': 'flask',
    'apiflask.APIFlask': 'flask',
    'apiflask.APIBlueprint': 'flask',
    'ninja.NinjaAPI': 'ninja',
    'ninja.Router': 'ninja',
}
ROUTE_METHODS = {
    'fastapi': frozenset({'get', 'post', 'put', 'patch', 'delete', 'options', 'head', 'trace', 'api_route', 'websocket'}),
    'flask': frozenset({'route', 'get', 'post', 'put', 'patch', 'delete'}),
    'ninja': frozenset({'get', 'post', 'put', 'patch', 'delete', 'api_operation'}),
}
FLASK_VIEWS = frozenset({'flask.views.MethodView', 'flask.views.View'})
DJANGO_VIEW_PREFIXES = ('django.views.', 'rest_framework.views.', 'rest_framework.viewsets.', 'rest_framework.generics.')
DJANGO_VIEW_NAMES = frozenset({'rest_framework.decorators.api_view', 'rest_framework.decorators.action'})

Function = (ast.FunctionDef, ast.AsyncFunctionDef)


class Frameworks:
    """Classifies classes and route handlers; results are memoized per qualified name."""

    def __init__(self, index: SourceIndex):
        self.index = index
        self._kinds: Dict[str, Optional[str]] = {}
        self._routers: Dict[str, Optional[str]] = {}

    # ---- classes -------------------------------------------------------------------------

    def class_kind(self, info: ModuleInfo, cls: ast.ClassDef) -> Optional[str]:
        """'entity', 'abstract-model', 'declarative', 'sqlmodel', 'pydantic', 'flask.view',
        'django.view' or None."""
        key = f'{info.name}.{cls.name}'
        if key in self._kinds:
            return self._kinds[key]
        self._kinds[key] = None
        kinds = {self._base_kind(info, b) for b in cls.bases}
        abstract = _abstract(cls)
        table = any(k.arg == 'table' and isinstance(k.value, ast.Constant) and k.value.value is True for k in cls.keywords)
        kind: Optional[str] = None
        if kinds & {'model', 'entity', 'abstract-model'}:
            kind = 'abstract-model' if abstract else 'entity'
        elif 'declarative' in kinds:
            kind = 'entity' if not abstract and _mapped(cls) else 'declarative'
        elif 'sqlmodel' in kinds:
            kind = 'entity' if table else 'sqlmodel'
        elif 'pydantic' in kinds:
            kind = 'pydantic'
        elif 'flask.view' in kinds:
            kind = 'flask.view'
        elif 'django.view' in kinds:
            kind = 'django.view'
        self._kinds[key] = kind
        return kind

    def _base_kind(self, info: ModuleInfo, expr: ast.expr) -> Optional[str]:
        if isinstance(expr, ast.Attribute) and expr.attr == 'Model' and self._is_flask_sqlalchemy(info, expr.value):
            return 'declarative'
        q = self.index.qualify(info, expr)
        if q is None:
            return None
        if q in DECLARATIVE_BASES:
            return 'declarative'
        if q in MODEL_BASES:
            return 'model'
        if q in ('sqlmodel.SQLModel', 'sqlmodel.main.SQLModel'):
            return 'sqlmodel'
        if q in PYDANTIC_BASES:
            return 'pydantic'
        if q in FLASK_VIEWS:
            return 'flask.view'
        if q.startswith(DJANGO_VIEW_PREFIXES):
            return 'django.view'
        found = self.index.lookup(q)
        if found is None:
            return None
        owner, _, definition = found
        if isinstance(definition, ast.ClassDef):
            kind = self.class_kind(owner, definition)
            return 'sqlmodel' if kind == 'entity' and self._sqlmodel(owner, definition) else kind
        if isinstance(definition, ast.Call):
            callee = self.index.qualify(owner, definition.func)
            if callee in DECLARATIVE_FACTORIES or (
                isinstance(definition.func, ast.Attribute) and definition.func.attr == 'generate_base'
            ):
                return 'declarative'
        return None

    def _sqlmodel(self, info: ModuleInfo, cls: ast.ClassDef) -> bool:
        return any(self.index.qualify(info, b) in ('sqlmodel.SQLModel', 'sqlmodel.main.SQLModel') for b in cls.bases)

    def _is_flask_sqlalchemy(self, info: ModuleInfo, expr: ast.expr) -> bool:
        q = self.index.qualify(info, expr)
        found = self.index.lookup(q) if q else None
        if found is None:
            return False
        owner, _, definition = found
        return isinstance(definition, ast.Call) and self.index.qualify(owner, definition.func) in FLASK_SQLALCHEMY

    def resolve_class(self, info: ModuleInfo, expr: ast.expr) -> Optional[Tuple[ModuleInfo, ast.ClassDef]]:
        q = self.index.qualify(info, expr)
        found = self.index.lookup(q) if q else None
        if found and isinstance(found[2], ast.ClassDef):
            return found[0], found[2]
        return None

    # ---- routes --------------------------------------------------------------------------

    def router_kind(self, info: ModuleInfo, expr: ast.expr) -> Optional[str]:
        """Framework of a router/app object (``router`` in ``@router.get(...)``)."""
        q = self.index.qualify(info, expr)
        if q is None:
            return None
        if q in self._routers:
            return self._routers[q]
        self._routers[q] = None
        kind = None
        found = self.index.lookup(q)
        if found is not None:
            owner, _, definition = found
            if isinstance(definition, ast.Call):
                callee = self.index.qualify(owner, definition.func)
                kind = ROUTERS.get(callee or '')
                if kind is None and callee:
                    factory = self.index.lookup(callee)
                    if factory and isinstance(factory[2], ast.ClassDef):
                        kind = next(
                            (ROUTERS[b] for b in (self.index.qualify(factory[0], x) for x in factory[2].bases) if b in ROUTERS),
                            None,
                        )
        self._routers[q] = kind
        return kind

    def route_framework(self, info: ModuleInfo, fn: ast.AST) -> Optional[Tuple[str, ast.Call]]:
        """(framework, decorator) when ``fn`` is a route handler registered by a decorator."""
        for decorator in getattr(fn, 'decorator_list', []):
            if not isinstance(decorator, ast.Call) or not isinstance(decorator.func, ast.Attribute):
                continue
            method = decorator.func.attr
            kind = self.router_kind(info, decorator.func.value)
            if kind is None and isinstance(decorator.func.value, ast.Name):
                kind = self._imported_framework(info, method)
            if kind and method in ROUTE_METHODS[kind]:
                return kind, decorator
        return None

    @staticmethod
    def _imported_framework(info: ModuleInfo, method: str) -> Optional[str]:
        for prefix, kind in (('fastapi', 'fastapi'), ('flask', 'flask'), ('quart', 'flask'), ('ninja', 'ninja')):
            if any(m == prefix or m.startswith(prefix + '.') for m in info.imported) and method in ROUTE_METHODS[kind]:
                return kind
        return None

    def handlers(self, info: ModuleInfo) -> Iterator[Tuple[str, str, ast.AST, ast.Call]]:
        """(framework, symbol suffix, function, decorator) for each decorated route handler."""
        for node in info.tree.body:
            if isinstance(node, Function):
                found = self.route_framework(info, node)
                if found:
                    yield found[0], node.name, node, found[1]
            elif isinstance(node, ast.ClassDef):
                for member in node.body:
                    if isinstance(member, Function):
                        found = self.route_framework(info, member)
                        if found:
                            yield found[0], f'{node.name}.{member.name}', member, found[1]

    # ---- module tags ---------------------------------------------------------------------

    def tags(self, info: ModuleInfo) -> List[str]:
        tags: Set[str] = set()
        for framework, _, _, _ in self.handlers(info):
            tags.add(f'{framework}.endpoint')
        imports_django = any(m == 'django' or m.startswith('django.') for m in info.imported)
        for node in info.tree.body:
            if isinstance(node, ast.ClassDef):
                kind = self.class_kind(info, node)
                if kind == 'entity':
                    tags.add('persistence.entity')
                elif kind == 'pydantic':
                    tags.add('pydantic.model')
                elif kind == 'flask.view':
                    tags.add('flask.endpoint')
                elif kind == 'django.view':
                    tags.add('django.endpoint')
            elif isinstance(node, Function):
                if any(self.index.qualify(info, _callee(d)) in DJANGO_VIEW_NAMES for d in node.decorator_list):
                    tags.add('django.endpoint')
            elif isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'urlpatterns' for t in node.targets):
                tags.add('django.routing')
        if imports_django and info.name.rpartition('.')[2] == 'views' and any(isinstance(n, Function) for n in info.tree.body):
            tags.add('django.endpoint')
        return sorted(tags)


def _callee(decorator: ast.expr) -> ast.expr:
    return decorator.func if isinstance(decorator, ast.Call) else decorator


def _abstract(cls: ast.ClassDef) -> bool:
    for node in cls.body:
        if isinstance(node, ast.Assign) and _assigns(node, '__abstract__') and _true(node.value):
            return True
        if isinstance(node, ast.ClassDef) and node.name == 'Meta':
            for inner in node.body:
                if isinstance(inner, ast.Assign) and _assigns(inner, 'abstract') and _true(inner.value):
                    return True
    return False


def _mapped(cls: ast.ClassDef) -> bool:
    for node in cls.body:
        if isinstance(node, ast.Assign) and (_assigns(node, '__tablename__') or _assigns(node, '__table__')):
            return True
        if isinstance(node, ast.AnnAssign):
            ann = node.annotation
            if isinstance(ann, ast.Subscript) and _name(ann.value) == 'Mapped':
                return True
        if isinstance(node, (ast.Assign, ast.AnnAssign)) and isinstance(node.value, ast.Call):
            if _name(node.value.func) in ('Column', 'mapped_column'):
                return True
    return False


def _assigns(node: ast.Assign, name: str) -> bool:
    return any(isinstance(t, ast.Name) and t.id == name for t in node.targets)


def _true(value: ast.expr) -> bool:
    return isinstance(value, ast.Constant) and value.value is True


def _name(expr: ast.expr) -> Optional[str]:
    if isinstance(expr, ast.Name):
        return expr.id
    if isinstance(expr, ast.Attribute):
        return expr.attr
    return None


def annotation_leaves(expr: Optional[ast.expr], depth: int = 0) -> Iterator[ast.expr]:
    """Name/Attribute leaves of a type expression (generics, unions, Annotated, string forms)."""
    if expr is None or depth > 12:
        return
    if isinstance(expr, (ast.Name, ast.Attribute)):
        yield expr
    elif isinstance(expr, ast.Subscript):
        yield from annotation_leaves(expr.slice, depth + 1)
    elif isinstance(expr, ast.Tuple):
        for e in expr.elts:
            yield from annotation_leaves(e, depth + 1)
    elif isinstance(expr, ast.BinOp):
        yield from annotation_leaves(expr.left, depth + 1)
        yield from annotation_leaves(expr.right, depth + 1)
    elif isinstance(expr, ast.Constant) and isinstance(expr.value, str):
        try:
            parsed = ast.parse(expr.value, mode='eval').body
        except SyntaxError:
            return
        yield from annotation_leaves(parsed, depth + 1)
    elif hasattr(ast, 'Index') and isinstance(expr, getattr(ast, 'Index')):  # Python 3.8 compatibility
        yield from annotation_leaves(expr.value, depth + 1)  # pragma: no cover


INJECTORS = frozenset({'Depends', 'Security'})


def _injected(expr: Optional[ast.expr]) -> bool:
    """FastAPI dependency injection (``Depends(...)``/``Security(...)``) is not part of the HTTP contract."""
    return isinstance(expr, ast.Call) and _name(expr.func) in INJECTORS


def _annotated_injection(annotation: ast.expr) -> bool:
    if isinstance(annotation, ast.Subscript) and _name(annotation.value) == 'Annotated':
        items = annotation.slice.elts if isinstance(annotation.slice, ast.Tuple) else []
        return any(_injected(item) for item in items[1:])
    return False


def signature_types(fn: ast.AST, decorator: ast.Call) -> List[ast.expr]:
    """Annotations that form the HTTP contract: request parameters, return type and response model."""
    args = fn.args
    positional = list(getattr(args, 'posonlyargs', [])) + args.args
    defaults: List[Optional[ast.expr]] = [None] * (len(positional) - len(args.defaults)) + list(args.defaults)
    params = list(zip(positional, defaults)) + list(zip(args.kwonlyargs, args.kw_defaults))
    if args.vararg:
        params.append((args.vararg, None))
    if args.kwarg:
        params.append((args.kwarg, None))
    out = [
        p.annotation for p, default in params
        if p.annotation is not None and not _injected(default) and not _annotated_injection(p.annotation)
    ]
    if fn.returns is not None:
        out.append(fn.returns)
    for k in decorator.keywords:
        if k.arg in ('response_model', 'response'):
            out.append(k.value)
    return out
