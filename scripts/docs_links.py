#!/usr/bin/env python3
"""Links from site pages to repository files that are not on the site (templates, spec, skill, examples).

Relative links that leave the site work on GitHub but break on the documentation site, so pages link to
those files with absolute repository URLs. Default: fail if a relative link leaves the site. --fix: rewrite
such links to repository URLs.
"""
import argparse
import posixpath
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = 'https://github.com/dmishra2022/archguard/blob/main/'
LINK = re.compile(r'(\]\()([^)\s#]+)(#[^)\s]*)?(\))')
# Must match exclude_docs in zensical.toml.
NOT_ON_SITE = re.compile(r'^docs/(kb/|pilots/[^/]+/|requirements\.txt$|architecture\.schema\.json$)')


def leaves_site(page: str, target: str) -> str:
    """Repository path of the target if a link from page to target leaves the site, else ''."""
    if '://' in target or target.startswith(('mailto:', '/')):
        return ''
    path = posixpath.normpath(posixpath.join(posixpath.dirname(page), target))
    if path.startswith('..'):
        return ''
    if path.startswith('docs/') and not NOT_ON_SITE.match(path):
        return ''
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--fix', action='store_true', help='rewrite offending links to repository URLs')
    args = parser.parse_args()
    problems = 0
    for file in sorted((ROOT / 'docs').rglob('*.md')):
        page = file.relative_to(ROOT).as_posix()
        if NOT_ON_SITE.match(page):
            continue
        text = file.read_text(encoding='utf-8')

        def rewrite(match):
            nonlocal problems
            path = leaves_site(page, match.group(2))
            if not path:
                return match.group(0)
            if not (ROOT / path).exists():
                print(f'{page}: link to missing file {path}', file=sys.stderr)
                problems += 1
                return match.group(0)
            if not args.fix:
                print(f'{page}: relative link leaves the site: {match.group(2)} (use {REPO}{path})', file=sys.stderr)
                problems += 1
            return f'{match.group(1)}{REPO}{path}{match.group(3) or ""}{match.group(4)}'

        fixed = LINK.sub(rewrite, text)
        if args.fix and fixed != text:
            file.write_text(fixed, encoding='utf-8')
    if problems:
        print(f'{problems} link problem(s). Run scripts/docs_links.py --fix', file=sys.stderr)
        return 1
    print('Docs links OK: no relative link leaves the site.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
