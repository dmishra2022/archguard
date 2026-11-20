#!/usr/bin/env python3
"""Prefix the relative artifact URIs of a SARIF log so they are relative to the repository root.

Usage: rebase_sarif.py <archguard.sarif> <prefix ending in />

The TypeScript and Python analyzers write paths relative to the analyzed project. When the project
is a subdirectory of the repository, GitHub code scanning needs repository-relative paths.
"""
import json
import sys
from pathlib import Path
from urllib.parse import quote


def rebase(node, prefix):
    if isinstance(node, dict):
        location = node.get('artifactLocation')
        if isinstance(location, dict):
            uri = location.get('uri', '')
            if uri and '://' not in uri and not uri.startswith('/'):
                location['uri'] = prefix + uri
        for value in node.values():
            rebase(value, prefix)
    elif isinstance(node, list):
        for value in node:
            rebase(value, prefix)


def main():
    path, prefix = Path(sys.argv[1]), quote(sys.argv[2])
    if not prefix:
        return
    log = json.loads(path.read_text(encoding='utf-8'))
    rebase(log, prefix)
    path.write_text(json.dumps(log, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
