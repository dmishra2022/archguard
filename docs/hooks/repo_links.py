"""MkDocs hook: links from docs pages to repository files outside docs/ (templates, spec, skill,
examples) work on GitHub as relative paths; on the site they become links to the repository."""
import posixpath
import re

REPO = 'https://github.com/dmishra2022/archguard/blob/main/'
LINK = re.compile(r'(\]\()([^)\s#]+)(#[^)\s]*)?(\))')
NOT_ON_SITE = re.compile(r'^docs/(kb/|hooks/|pilots/[^/]+/|architecture\.schema\.json)')


def on_page_markdown(markdown, page, config, files):
    base = posixpath.dirname('docs/' + page.file.src_uri)

    def rewrite(match):
        target = match.group(2)
        if '://' in target or target.startswith(('mailto:', '/')):
            return match.group(0)
        path = posixpath.normpath(posixpath.join(base, target))
        if path.startswith('..') or (path.startswith('docs/') and not NOT_ON_SITE.match(path)):
            return match.group(0)
        return f'{match.group(1)}{REPO}{path}{match.group(3) or ""}{match.group(4)}'

    return LINK.sub(rewrite, markdown)
