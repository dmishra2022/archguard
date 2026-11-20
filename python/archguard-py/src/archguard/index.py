"""Parsed module index: name bindings and top-level definitions used for static name resolution."""
from __future__ import annotations

import ast
from dataclasses import dataclass, field
from typing import Dict, Optional, Set, Tuple, Union

from .model import AnalysisError
from .project import Project, SourceFile

Definition = Union[ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef, ast.expr]


@dataclass
class ModuleInfo:
    source: SourceFile
    tree: ast.Module
    bindings: Dict[str, str] = field(default_factory=dict)
    definitions: Dict[str, Definition] = field(default_factory=dict)
    imported: Set[str] = field(default_factory=set)

    @property
    def name(self) -> str:
        return self.source.module


def absolute(package: str, level: int, module: Optional[str]) -> Optional[str]:
    """Absolute module of a relative import, or None when it climbs above the top-level package."""
    if level == 0:
        return module
    parts = package.split('.') if package else []
    if level - 1 >= len(parts):
        return None
    base = parts[: len(parts) - (level - 1)]
    if module:
        base.append(module)
    return '.'.join(base) if base else None


class SourceIndex:
    def __init__(self, project: Project):
        self.project = project
        self._parsed: Dict[str, ModuleInfo] = {}

    def parse(self, module: str) -> ModuleInfo:
        if module in self._parsed:
            return self._parsed[module]
        source = self.project.modules[module]
        try:
            tree = ast.parse(source.path.read_bytes(), filename=str(source.path))
        except SyntaxError as e:
            raise AnalysisError(
                f'Cannot parse {self.project.rel(source.path)}:{e.lineno}: {e.msg}. Run ArchGuard with a '
                f'Python version that supports the project syntax.'
            ) from None
        except (OSError, ValueError) as e:
            raise AnalysisError(f'Cannot read {self.project.rel(source.path)}: {e}') from None
        info = ModuleInfo(source, tree)
        for node in tree.body:
            self._bind(info, node)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                info.imported.update(a.name for a in node.names)
            elif isinstance(node, ast.ImportFrom):
                target = absolute(source.package, node.level, node.module)
                if target:
                    info.imported.add(target)
        self._parsed[module] = info
        return info

    def _bind(self, info: ModuleInfo, node: ast.stmt) -> None:
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            info.definitions[node.name] = node
        elif isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            info.definitions[node.targets[0].id] = node.value
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.value is not None:
            info.definitions[node.target.id] = node.value
        elif isinstance(node, ast.Import):
            for a in node.names:
                if a.asname:
                    info.bindings[a.asname] = a.name
                else:
                    top = a.name.split('.')[0]
                    info.bindings[top] = top
        elif isinstance(node, ast.ImportFrom):
            base = absolute(info.source.package, node.level, node.module)
            if base is None:
                return
            for a in node.names:
                if a.name != '*':
                    info.bindings[a.asname or a.name] = f'{base}.{a.name}'
        elif isinstance(node, (ast.If, ast.Try)):
            for child in node.body + getattr(node, 'orelse', []) + getattr(node, 'finalbody', []):
                self._bind(info, child)
            for handler in getattr(node, 'handlers', []):
                for child in handler.body:
                    self._bind(info, child)

    def qualify(self, info: ModuleInfo, expr: ast.expr) -> Optional[str]:
        """Dotted qualified name of a Name/Attribute expression, resolved through module bindings."""
        if isinstance(expr, ast.Name):
            if expr.id in info.bindings:
                return info.bindings[expr.id]
            if expr.id in info.definitions:
                return f'{info.name}.{expr.id}'
            return None
        if isinstance(expr, ast.Attribute):
            base = self.qualify(info, expr.value)
            return f'{base}.{expr.attr}' if base else None
        return None

    def lookup(self, qualified: str, depth: int = 0) -> Optional[Tuple[ModuleInfo, str, Definition]]:
        """Follows re-exports to the owned module that defines ``qualified`` (a top-level name)."""
        if depth > 8 or '.' not in qualified:
            return None
        module, _, name = qualified.rpartition('.')
        if module not in self.project.modules:
            return None
        info = self.parse(module)
        if name in info.definitions:
            return info, name, info.definitions[name]
        if name in info.bindings and info.bindings[name] != qualified:
            return self.lookup(info.bindings[name], depth + 1)
        return None
