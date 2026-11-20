export const VERSION = '0.1.0';
export const LANGUAGE = 'typescript';

export type Severity = 'INFO' | 'WARNING' | 'ERROR';
export const SEVERITIES: readonly Severity[] = ['INFO', 'WARNING', 'ERROR'];

export function atLeast(s: Severity, minimum: Severity): boolean {
  return SEVERITIES.indexOf(s) >= SEVERITIES.indexOf(minimum);
}

export const ROLES = [
  'DOMAIN',
  'APPLICATION',
  'INBOUND_PORT',
  'OUTBOUND_PORT',
  'INBOUND_ADAPTER',
  'OUTBOUND_ADAPTER',
  'COMPOSITION_ROOT',
] as const;
export type Role = (typeof ROLES)[number] | 'UNCLASSIFIED';

export type Status = 'NEW' | 'EXISTING' | 'SUPPRESSED';

export interface Location {
  module: string;
  path: string;
  symbol: string;
  line: number;
}

/** An analyzed module (one source file under roots). */
export interface Unit {
  name: string;
  /** Selector containers: the directory path, plus the workspace-package form when available. */
  containers: string[];
  role: Role;
  context: string;
  tags: string[];
  location: Location;
}

export type DependencyKind = 'IMPORT' | 'HTTP_ENTITY_EXPOSURE';

export interface Dependency {
  origin: string;
  target: string;
  evidence: string;
  location: Location;
  kind: DependencyKind;
  /** Containers of the target used for role, context and constraint selectors. */
  targetContainers: string[];
  /** The import specifier for external package targets (used for infrastructure matching). */
  externalSpecifier?: string;
}

export interface ArchitectureModel {
  units: Map<string, Unit>;
  dependencies: Dependency[];
  diagnostics: string[];
}

export interface Finding {
  fingerprint: string;
  ruleId: string;
  severity: Severity;
  message: string;
  evidence: string;
  location: Location;
  target: string;
  remediation: string;
  status: Status;
}

export interface AnalysisResult {
  schemaVersion: '1';
  engineVersion: string;
  policyHash: string;
  analyzedClasses: number;
  dependencies: number;
  findings: Finding[];
  diagnostics: string[];
  specVersion: string;
  language: string;
}

export function fails(r: AnalysisResult, minimum: Severity, newOnly: boolean): boolean {
  return r.findings.some(
    (f) =>
      f.status !== 'SUPPRESSED' && (!newOnly || f.status === 'NEW') && atLeast(f.severity, minimum),
  );
}

/** Analysis could not be completed; always exit code 2, never a pass. */
export class AnalysisError extends Error {}
