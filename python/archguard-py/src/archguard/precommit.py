"""pre-commit entry point: ``archguard-pre-commit [archguard options] [--] FILE...``.

pre-commit passes the staged file names as arguments; they become the changed-files scope, so the
hook reports only findings located in the files being committed while still analyzing the whole graph.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import List, Optional

from .cli import Io, run


def split(argv: List[str]):
    if '--' in argv:
        i = argv.index('--')
        return argv[:i], argv[i + 1:]
    options: List[str] = []
    files: List[str] = []
    rest = list(argv)
    while rest:
        arg = rest.pop(0)
        if arg.startswith('--'):
            options.append(arg)
            if '=' not in arg and arg not in ('--overwrite-baseline', '--json') and rest and not rest[0].startswith('--'):
                options.append(rest.pop(0))
        else:
            files.append(arg)
    return options, files


def main(argv: Optional[List[str]] = None) -> None:
    options, files = split(sys.argv[1:] if argv is None else argv)
    if not any(o == '--format' or o.startswith('--format=') for o in options):
        options += ['--format', 'console']
    stdin = '\n'.join(files)
    io = Io(Path.cwd(), sys.stdout.write, sys.stderr.write, lambda: stdin)
    sys.exit(run(['check', *options, '--changed-files', '-'], io))
