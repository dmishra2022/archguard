import { isAbsolute, normalize, relative } from 'node:path';
import { AnalysisResult } from './model.js';
import { posix, real } from './project.js';

export function normalizePath(path: string, project: string): string {
  let p = path.replace(/\\/g, '/');
  if (isAbsolute(p)) p = relative(real(project), real(p));
  return posix(normalize(p));
}

/**
 * Restricts reported and gated findings to those located in changed files. The full graph is still
 * analyzed, so violations caused by a changed file against unchanged code are kept.
 */
export function restrictToChangedFiles(result: AnalysisResult, lines: string[], project: string): AnalysisResult {
  const files = new Set<string>();
  for (const line of lines) {
    const entry = line.trim();
    if (!entry || entry.startsWith('#')) continue;
    files.add(normalizePath(entry, project));
  }
  const kept = result.findings.filter((f) => f.location.path && files.has(normalizePath(f.location.path, project)));
  return {
    ...result,
    findings: kept,
    diagnostics: [
      ...result.diagnostics,
      `Changed-files scope: ${files.size} file(s); ${result.findings.length - kept.length} finding(s) outside the list not reported`,
    ],
  };
}
