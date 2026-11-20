import { readFileSync } from 'node:fs';
import { AnalysisError, AnalysisResult, Finding } from './model.js';
import { atomic } from './reports.js';

interface Suppression {
  fingerprint: string;
  owner: string;
  reason: string;
  expires: string;
}

const FINGERPRINT = /^[a-f0-9]{64}$/;

function readJson(file: string, label: string): any {
  try {
    return JSON.parse(readFileSync(file, 'utf8'));
  } catch (e) {
    throw new AnalysisError(`Cannot read ${label} ${file}: ${(e as Error).message}`);
  }
}

function onlyKeys(value: any, keys: string[], label: string): void {
  if (typeof value !== 'object' || value === null || Array.isArray(value))
    throw new AnalysisError(`Invalid ${label} schema`);
  for (const k of Object.keys(value))
    if (!keys.includes(k)) throw new AnalysisError(`Invalid ${label} schema: unknown field ${k}`);
}

export function writeBaseline(file: string, result: AnalysisResult): void {
  const fingerprints = [
    ...new Set(result.findings.filter((f) => f.severity !== 'INFO').map((f) => f.fingerprint)),
  ].sort();
  atomic(file, JSON.stringify({ schemaVersion: 1, policyHash: result.policyHash, fingerprints }, null, 2) + '\n');
}

function today(now: Date): string {
  return now.toISOString().slice(0, 10);
}

function validDate(s: unknown): s is string {
  if (typeof s !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(s)) return false;
  const d = new Date(`${s}T00:00:00Z`);
  return !Number.isNaN(d.getTime()) && d.toISOString().slice(0, 10) === s;
}

export function applyDebt(
  r: AnalysisResult,
  baseline: string | undefined,
  suppressions: string | undefined,
  now: Date = new Date(),
): AnalysisResult {
  let accepted = new Set<string>();
  const ignored = new Map<string, Suppression>();
  if (baseline) {
    const b = readJson(baseline, 'baseline');
    onlyKeys(b, ['schemaVersion', 'policyHash', 'fingerprints'], 'baseline');
    if (b.schemaVersion !== 1 || b.policyHash !== r.policyHash || !Array.isArray(b.fingerprints))
      throw new AnalysisError(
        'Baseline schema, engine or policy does not match; review and explicitly regenerate it',
      );
    accepted = new Set(b.fingerprints);
  }
  if (suppressions) {
    const file = readJson(suppressions, 'suppressions');
    onlyKeys(file, ['schemaVersion', 'entries'], 'suppression');
    if (file.schemaVersion !== 1 || !Array.isArray(file.entries))
      throw new AnalysisError('Invalid suppression schema');
    for (const s of file.entries) {
      onlyKeys(s, ['fingerprint', 'owner', 'reason', 'expires'], 'suppression');
      if (
        typeof s.fingerprint !== 'string' ||
        !FINGERPRINT.test(s.fingerprint) ||
        typeof s.owner !== 'string' ||
        !s.owner.trim() ||
        typeof s.reason !== 'string' ||
        !s.reason.trim()
      )
        throw new AnalysisError('Suppression requires fingerprint, owner and reason');
      if (!validDate(s.expires)) throw new AnalysisError('Invalid suppression expiry');
      if (s.expires < today(now)) throw new AnalysisError(`Expired suppression: ${s.fingerprint}`);
      if (ignored.has(s.fingerprint)) throw new AnalysisError(`Duplicate suppression: ${s.fingerprint}`);
      ignored.set(s.fingerprint, s);
    }
  }
  const findings: Finding[] = r.findings.map((f) => ({
    ...f,
    status: ignored.has(f.fingerprint) ? 'SUPPRESSED' : accepted.has(f.fingerprint) ? 'EXISTING' : 'NEW',
  }));
  const current = new Set(findings.map((f) => f.fingerprint));
  const stale = [...accepted].filter((f) => !current.has(f)).length;
  const diagnostics = [
    ...r.diagnostics,
    `Baseline entries no longer observed in this scope: ${stale} (baseline not modified)`,
  ];
  for (const s of ignored.values())
    diagnostics.push(`Suppression ${s.fingerprint} owner=${s.owner} expires=${s.expires} reason=${s.reason}`);
  return { ...r, findings, diagnostics };
}
