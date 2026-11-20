"""Neutral glob selectors over dotted Python module names (spec/SELECTORS.md).

A segment is a literal name, '*' (exactly one segment) or '**' (zero or more segments). Python
selectors match the module name itself, so 'orders.domain.**' matches 'orders.domain' (the package
``__init__``) and 'orders.domain.model'.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Iterable, Sequence, Tuple


def validate_selector(s: object) -> None:
    if not isinstance(s, str) or not s.strip() or len(s) > 512:
        raise ValueError(f'Invalid package selector: {s!r}')
    if '/' in s or '\\' in s:
        raise ValueError(f'Invalid package selector (Python selectors use dotted module names): {s}')
    for segment in s.split('.'):
        if segment == '':
            raise ValueError(f'Invalid package selector: {s}')
        if '*' in segment and segment not in ('*', '**'):
            raise ValueError(f'Invalid package selector (wildcards must be whole segments): {s}')


@lru_cache(maxsize=4096)
def _segments(selector: str) -> Tuple[str, ...]:
    validate_selector(selector)
    return tuple(selector.split('.'))


def _match(sel: Tuple[str, ...], i: int, path: Sequence[str], j: int) -> bool:
    if i == len(sel):
        return j == len(path)
    if sel[i] == '**':
        return any(_match(sel, i + 1, path, k) for k in range(j, len(path) + 1))
    if j == len(path):
        return False
    return (sel[i] == '*' or sel[i] == path[j]) and _match(sel, i + 1, path, j + 1)


def matches_one(selector: str, container: str) -> bool:
    return _match(_segments(selector), 0, container.split('.') if container else [], 0)


def matches(selectors: Iterable[str], containers: Iterable[str]) -> bool:
    containers = list(containers)
    return any(matches_one(s, c) for s in selectors for c in containers)
