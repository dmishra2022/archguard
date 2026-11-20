from __future__ import annotations

import os
from pathlib import Path, PurePosixPath
from typing import Iterable

from .model import AnalysisResult


def normalize_path(path: str, project: Path) -> str:
    p = path.replace('\\', '/')
    if os.path.isabs(p):
        p = os.path.relpath(os.path.realpath(p), os.path.realpath(project)).replace('\\', '/')
    return PurePosixPath(os.path.normpath(p).replace('\\', '/')).as_posix()


def restrict_to_changed_files(result: AnalysisResult, lines: Iterable[str], project: Path) -> AnalysisResult:
    """Restricts reported and gated findings to those located in changed files. The full graph is still
    analyzed, so violations caused by a changed file against unchanged code are kept."""
    files = set()
    for line in lines:
        entry = line.strip()
        if entry and not entry.startswith('#'):
            files.add(normalize_path(entry, project))
    kept = [f for f in result.findings if f.location.path and normalize_path(f.location.path, project) in files]
    diagnostics = list(result.diagnostics) + [
        f'Changed-files scope: {len(files)} file(s); {len(result.findings) - len(kept)} finding(s) outside the list not reported'
    ]
    return result.with_findings(kept, diagnostics)
