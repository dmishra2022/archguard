import { mkdirSync, renameSync, rmSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { randomBytes } from 'node:crypto';
import { AnalysisResult, Status } from './model.js';
import { catalog } from './spec.js';

export const FORMATS = new Set(['json', 'sarif', 'html', 'agent', 'console']);
export const AGENT_FILE = 'archguard.agent.jsonl';

export function atomic(file: string, contents: string): void {
  mkdirSync(dirname(file), { recursive: true });
  const temporary = join(dirname(file), `.archguard-${randomBytes(6).toString('hex')}.tmp`);
  try {
    writeFileSync(temporary, contents, 'utf8');
    renameSync(temporary, file);
  } finally {
    rmSync(temporary, { force: true });
  }
}

function pretty(value: unknown): string {
  return JSON.stringify(value, null, 2) + '\n';
}

export function writeReports(dir: string, result: AnalysisResult, formats: Set<string>, gateFailed: boolean): void {
  mkdirSync(dir, { recursive: true });
  if (formats.has('json')) atomic(join(dir, 'archguard.json'), pretty(result));
  if (formats.has('sarif')) atomic(join(dir, 'archguard.sarif'), pretty(sarif(result)));
  if (formats.has('html')) atomic(join(dir, 'index.html'), html(result));
  if (formats.has('agent')) atomic(join(dir, AGENT_FILE), agent(result, gateFailed));
}

/** Overwrites the report set with explicit failure outputs so a stale pass is never left behind. */
export function writeFailure(dir: string, message: string, formats: Set<string>): void {
  atomic(
    join(dir, 'archguard.json'),
    pretty({ schemaVersion: '1', specVersion: specVersion(), analysisStatus: 'FAILED', error: message }),
  );
  atomic(
    join(dir, 'archguard.sarif'),
    pretty({
      version: '2.1.0',
      runs: [
        {
          tool: { driver: { name: 'ArchGuard' } },
          invocations: [
            { executionSuccessful: false, toolExecutionNotifications: [{ level: 'error', message: { text: message } }] },
          ],
        },
      ],
    }),
  );
  atomic(
    join(dir, 'index.html'),
    '<!doctype html><html lang="en"><meta charset="utf-8"><title>ArchGuard analysis failed</title><h1>Analysis failed</h1><p>No compliance result is available. See archguard.json and the build log for the error.</p></html>',
  );
  if (formats.has('agent')) atomic(join(dir, AGENT_FILE), agentError(message));
}

function specVersion(): string {
  try {
    return catalog().specVersion;
  } catch {
    return 'unknown';
  }
}

/** One JSON object per non-INFO finding, then a summary line (spec/CLI.md, agent format). */
export function agent(r: AnalysisResult, gateFailed: boolean): string {
  const counts: Record<Status, number> = { NEW: 0, EXISTING: 0, SUPPRESSED: 0 };
  let s = '';
  for (const f of r.findings) {
    if (f.severity === 'INFO') continue;
    counts[f.status]++;
    s +=
      JSON.stringify({
        rule: f.ruleId,
        severity: f.severity,
        status: f.status,
        file: f.location.path,
        line: f.location.line,
        symbol: f.location.symbol,
        target: f.target,
        message: f.message,
        fix: f.remediation,
        fingerprint: f.fingerprint,
      }) + '\n';
  }
  return (
    s +
    JSON.stringify({
      summary: true,
      status: gateFailed ? 'FAILED' : 'PASSED',
      new: counts.NEW,
      existing: counts.EXISTING,
      suppressed: counts.SUPPRESSED,
    }) +
    '\n'
  );
}

export function agentError(message: string): string {
  return JSON.stringify({ summary: true, status: 'ERROR', error: message }) + '\n';
}

export function summary(r: AnalysisResult): string {
  const counts: Record<string, number> = { NEW: 0, EXISTING: 0, SUPPRESSED: 0 };
  let info = 0;
  for (const f of r.findings) {
    if (f.severity === 'INFO') info++;
    else counts[f.status]++;
  }
  let s =
    `ArchGuard ${r.engineVersion}: ${r.analyzedClasses} modules, ${r.dependencies} dependencies, ${r.findings.length} findings ` +
    `(${counts.NEW} new, ${counts.EXISTING} existing, ${counts.SUPPRESSED} suppressed, ${info} info)`;
  for (const d of r.diagnostics) {
    const value = d.split(': ').slice(1).join(': ');
    if (d.startsWith('Unclassified application') && !value.startsWith('0 ')) s += `; unclassified ${value}`;
  }
  return s;
}

export function consoleReport(r: AnalysisResult): string {
  let s = summary(r) + '\n';
  for (const f of r.findings) {
    if (f.severity === 'INFO') continue;
    s += `${f.severity} ${f.ruleId} [${f.status}] ${f.location.symbol}:${f.location.line} — ${f.message}\n  ${f.remediation}\n`;
  }
  return s;
}

function sarif(r: AnalysisResult): object {
  const rules = new Map<string, object>();
  const results: object[] = [];
  const specs = catalog().rules;
  for (const f of r.findings) {
    if (!rules.has(f.ruleId))
      rules.set(f.ruleId, {
        id: f.ruleId,
        shortDescription: { text: specs.get(f.ruleId)?.title ?? f.ruleId },
        help: { text: f.remediation },
      });
    const location: Record<string, unknown> = {
      logicalLocations: [{ fullyQualifiedName: f.location.symbol, kind: 'module' }],
    };
    if (f.location.path) {
      const physical: Record<string, unknown> = {
        artifactLocation: { uri: encodeURI(f.location.path), uriBaseId: '%SRCROOT%' },
      };
      if (f.location.line > 0) physical.region = { startLine: f.location.line };
      location.physicalLocation = physical;
    }
    const entry: Record<string, unknown> = {
      ruleId: f.ruleId,
      level: f.severity === 'ERROR' ? 'error' : f.severity === 'WARNING' ? 'warning' : 'note',
      message: { text: `${f.message}\nEvidence: ${f.evidence}\nSuggested correction: ${f.remediation}` },
      partialFingerprints: { 'archguard/v1': f.fingerprint },
      baselineState: f.status === 'EXISTING' ? 'unchanged' : 'new',
      locations: [location],
      properties: { module: f.location.module, target: f.target, status: f.status },
    };
    if (f.status === 'SUPPRESSED')
      entry.suppressions = [
        {
          kind: 'external',
          status: 'accepted',
          justification: 'Reviewed suppression; see report diagnostics for owner, reason and expiry',
        },
      ];
    results.push(entry);
  }
  return {
    version: '2.1.0',
    $schema: 'https://json.schemastore.org/sarif-2.1.0.json',
    runs: [
      {
        tool: {
          driver: {
            name: 'ArchGuard',
            version: r.engineVersion,
            rules: [...rules.entries()].sort(([a], [b]) => (a < b ? -1 : a > b ? 1 : 0)).map(([, v]) => v),
          },
        },
        results,
        invocations: [{ executionSuccessful: true }],
        properties: { policyHash: r.policyHash, diagnostics: r.diagnostics, specVersion: r.specVersion },
      },
    ],
  };
}

function escape(s: string): string {
  return s
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

export function html(r: AnalysisResult): string {
  let s =
    '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'"><title>ArchGuard architecture report</title><style>body{font:16px system-ui;max-width:1100px;margin:40px auto;padding:0 24px;background:#f5f7fb;color:#19243a}article{background:white;border:1px solid #dce3ee;border-left:5px solid #375dd3;padding:20px;margin:18px 0;border-radius:8px}code,pre{white-space:pre-wrap;overflow-wrap:anywhere}small{color:#526078}h1{letter-spacing:-1px}.ERROR{border-left-color:#be3030}.WARNING{border-left-color:#b8860b}summary{cursor:pointer}</style><body><h1>ArchGuard</h1>';
  s += `<p>Engine ${escape(r.engineVersion)} · ${r.analyzedClasses} modules · ${r.dependencies} static dependencies · ${r.findings.length} findings</p><p>Analysis completed. Gate outcome depends on configured severity and baseline policy.</p>`;
  s += '<details><summary>Scope and diagnostics</summary><ul>';
  for (const d of r.diagnostics) s += `<li>${escape(d)}</li>`;
  s += `</ul><small>Policy: ${escape(r.policyHash)}</small></details>`;
  for (const f of r.findings)
    s +=
      `<article class="${f.severity}"><small>${escape(f.ruleId)} · ${f.severity} · ${escape(f.status)}</small>` +
      `<h2>${escape(f.message)}</h2><p><code>${escape(`${f.location.module} / ${f.location.path}:${f.location.line} — ${f.location.symbol}`)}</code></p>` +
      `<p><strong>Evidence</strong></p><pre>${escape(f.evidence)}</pre><p><strong>Suggested correction</strong></p><p>${escape(f.remediation)}</p>` +
      `<small>Fingerprint: ${escape(f.fingerprint)}</small></article>`;
  return s + '</body></html>';
}
