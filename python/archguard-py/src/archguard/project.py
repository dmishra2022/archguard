"""Discovers the analyzed Python modules of a project (spec/languages/python.md)."""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set

from .model import AnalysisError

try:  # Python 3.11+
    import tomllib as _toml
except ImportError:  # pragma: no cover - exercised on Python 3.9/3.10
    _toml = None

TEST_DIRS = frozenset({'test', 'tests', 'testing'})
SKIPPED_DIRS = {
    '__pycache__', 'node_modules', 'site-packages', 'venv', 'env', 'build', 'dist', 'htmlcov',
    'reports', 'target',
} | TEST_DIRS
TEST_FILE = re.compile(r'^(test_.*|.*_test|conftest|tests)\.py$')


@dataclass(frozen=True)
class SourceFile:
    path: Path
    module: str
    package: str
    source_root: Path


@dataclass
class Project:
    root: Path
    source_roots: List[Path]
    files: List[SourceFile]
    modules: Dict[str, SourceFile]
    namespaces: Set[str]
    owned_tops: Set[str]
    diagnostics: List[str] = field(default_factory=list)
    test_modules: Set[str] = field(default_factory=set)
    fallback_module_id: bool = False
    _module_ids: Dict[Path, str] = field(default_factory=dict)

    def rel(self, path: Path) -> str:
        return path.relative_to(self.root).as_posix()

    def module_id(self, path: Path) -> str:
        directory = path.parent
        while True:
            if directory in self._module_ids:
                return self._module_ids[directory]
            name = distribution_name(directory)
            if name:
                self._module_ids[directory] = name
                return name
            if directory == self.root or self.root not in directory.parents:
                break
            directory = directory.parent
        self.fallback_module_id = True
        self._module_ids[directory] = self.root.name
        return self.root.name

    def module_id_diagnostics(self) -> List[str]:
        if not self.fallback_module_id:
            return []
        return [
            f"No distribution name in a pyproject.toml or setup.cfg above some analyzed modules; their module ID "
            f"falls back to the directory name '{self.root.name}' (fingerprints include it)"
        ]


def distribution_name(directory: Path) -> Optional[str]:
    """[project].name or [tool.poetry].name from pyproject.toml, else [metadata] name in setup.cfg."""
    pyproject = directory / 'pyproject.toml'
    if pyproject.is_file():
        text = pyproject.read_text(encoding='utf-8', errors='replace')
        if _toml is not None:
            try:
                data = _toml.loads(text)
                name = (data.get('project') or {}).get('name') or ((data.get('tool') or {}).get('poetry') or {}).get('name')
                if isinstance(name, str) and name.strip():
                    return name.strip()
            except ValueError:
                pass
        else:
            name = _section_name(text, ('project', 'tool.poetry'))
            if name:
                return name
    setup_cfg = directory / 'setup.cfg'
    if setup_cfg.is_file():
        name = _section_name(setup_cfg.read_text(encoding='utf-8', errors='replace'), ('metadata',))
        if name:
            return name
    return None


def _section_name(text: str, sections) -> Optional[str]:
    current = None
    for raw in text.splitlines():
        line = raw.strip()
        header = re.match(r'^\[([^\]]+)\]$', line)
        if header:
            current = header.group(1).strip()
            continue
        if current in sections:
            m = re.match(r'''^name\s*[=:]\s*["']?([^"'\s#]+)["']?''', line)
            if m:
                return m.group(1)
    return None


def _skip_dir(name: str) -> bool:
    return name.startswith('.') or name in SKIPPED_DIRS or name.endswith('.egg-info')


def module_name(source_root: Path, path: Path) -> str:
    """Dotted module name, or '' when a path segment is not an identifier (``gunicorn.conf.py``, ``0001_x.py``)."""
    relative = path.relative_to(source_root)
    parts = list(relative.parent.parts) + [relative.name[: -len('.py')]]
    if not all(part.isidentifier() for part in parts):
        return ''
    if parts[-1] == '__init__':
        parts = parts[:-1]
    return '.'.join(parts)


def default_source_roots(root: Path) -> List[str]:
    src = root / 'src'
    if src.is_dir() and any(src.rglob('*.py')):
        return ['src']
    return ['.']


def load_project(root: Path, configured: Optional[List[str]]) -> Project:
    root = root.resolve()
    if not root.is_dir():
        raise AnalysisError(f'Project directory not found: {root}')
    diagnostics: List[str] = []
    names = configured if configured else default_source_roots(root)
    if not configured:
        diagnostics.append(f"Source roots (auto-detected; set sourceRoots to override): {', '.join(names)}")
    roots: List[Path] = []
    for name in names:
        candidate = (root / name).resolve()
        if not candidate.is_dir():
            raise AnalysisError(f'Source root not found: {name}')
        if candidate != root and root not in candidate.parents:
            raise AnalysisError(f'Source root escapes the project: {name}')
        roots.append(candidate)

    files: List[SourceFile] = []
    modules: Dict[str, SourceFile] = {}
    namespaces: Set[str] = set()
    tests: Set[str] = set()
    for source_root in roots:
        for directory, dirs, filenames in os.walk(source_root):
            here = Path(directory)
            for d in dirs:
                if d in TEST_DIRS:
                    tests.add(module_name(source_root, here / d / '__init__.py'))
            dirs[:] = sorted(d for d in dirs if not _skip_dir(d))
            for filename in sorted(filenames):
                if not filename.endswith('.py'):
                    continue
                path = here / filename
                name = module_name(source_root, path)
                if TEST_FILE.match(filename):
                    tests.add(name)
                    continue
                if not name:
                    continue
                package = name if filename == '__init__.py' else name.rpartition('.')[0]
                sf = SourceFile(path, name, package, source_root)
                if name in modules:
                    raise AnalysisError(
                        f'Ambiguous module name {name}: {modules[name].path.relative_to(root).as_posix()} '
                        f'and {path.relative_to(root).as_posix()}'
                    )
                modules[name] = sf
                files.append(sf)
                parts = name.split('.')
                for i in range(1, len(parts)):
                    namespaces.add('.'.join(parts[:i]))
    namespaces -= set(modules)
    owned_tops = {m.split('.')[0] for m in modules}
    tests.discard('')
    return Project(root, roots, files, modules, namespaces, owned_tops, diagnostics, test_modules=tests)
