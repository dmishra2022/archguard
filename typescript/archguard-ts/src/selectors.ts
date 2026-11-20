/**
 * Neutral glob selectors over '/'-separated containers (spec/SELECTORS.md): a segment is a literal
 * name, '*' (exactly one segment) or '**' (zero or more segments).
 */
const compiled = new Map<string, string[]>();

export function validateSelector(s: unknown): void {
  if (typeof s !== 'string' || s.trim() === '' || s.length > 512)
    throw new Error(`Invalid path selector: ${JSON.stringify(s)}`);
  if (s.includes('\\') || s.startsWith('/') || s.startsWith('./'))
    throw new Error(`Invalid path selector (use project-relative POSIX paths): ${s}`);
  for (const segment of s.split('/')) {
    if (segment === '' || segment === '.' || segment === '..')
      throw new Error(`Invalid path selector: ${s}`);
    if (segment.includes('*') && segment !== '*' && segment !== '**')
      throw new Error(`Invalid path selector (wildcards must be whole segments): ${s}`);
  }
}

function segments(selector: string): string[] {
  let s = compiled.get(selector);
  if (!s) {
    validateSelector(selector);
    s = selector.split('/');
    compiled.set(selector, s);
  }
  return s;
}

function matchFrom(sel: string[], i: number, path: string[], j: number): boolean {
  if (i === sel.length) return j === path.length;
  if (sel[i] === '**') {
    for (let k = j; k <= path.length; k++) if (matchFrom(sel, i + 1, path, k)) return true;
    return false;
  }
  if (j === path.length) return false;
  return (sel[i] === '*' || sel[i] === path[j]) && matchFrom(sel, i + 1, path, j + 1);
}

export function matchesOne(selector: string, container: string): boolean {
  return matchFrom(segments(selector), 0, container === '' ? [] : container.split('/'), 0);
}

/** True when any selector matches any of the unit's container forms. */
export function matches(selectors: readonly string[], containers: readonly string[]): boolean {
  return selectors.some((s) => containers.some((c) => matchesOne(s, c)));
}
