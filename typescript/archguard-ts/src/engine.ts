import { AnalysisResult, ArchitectureModel, Finding, LANGUAGE, VERSION } from './model.js';
import { Policy, policyHash, semanticValidate } from './policy.js';
import { loadProject } from './project.js';
import { readModel } from './importer.js';
import { checkRuleIds, evaluate } from './rules.js';
import { catalog } from './spec.js';

function cmp(a: string, b: string): number {
  return a < b ? -1 : a > b ? 1 : 0;
}

export function evaluateModel(model: ArchitectureModel, policy: Policy): AnalysisResult {
  semanticValidate(policy);
  checkRuleIds(policy);
  const unique = new Map<string, Finding>();
  for (const f of evaluate(model, policy)) if (!unique.has(f.fingerprint)) unique.set(f.fingerprint, f);
  const findings = [...unique.values()].sort(
    (a, b) =>
      cmp(a.ruleId, b.ruleId) ||
      cmp(a.location.module, b.location.module) ||
      cmp(a.location.symbol, b.location.symbol) ||
      cmp(a.fingerprint, b.fingerprint),
  );
  return {
    schemaVersion: '1',
    engineVersion: VERSION,
    policyHash: policyHash(policy),
    analyzedClasses: model.units.size,
    dependencies: model.dependencies.length,
    findings,
    diagnostics: [
      ...model.diagnostics,
      'Scope: configured source roots and root selectors only; external service behavior is not analyzed.',
    ],
    specVersion: catalog().specVersion,
    language: LANGUAGE,
  };
}

export function analyze(projectRoot: string, policy: Policy, tsconfig?: string): AnalysisResult {
  checkRuleIds(policy);
  const project = loadProject(projectRoot, policy.sourceRoots, tsconfig);
  return evaluateModel(readModel(project, policy), policy);
}
