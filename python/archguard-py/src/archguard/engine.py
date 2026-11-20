from __future__ import annotations

from pathlib import Path

from .importer import read_model
from .model import VERSION, AnalysisResult, Model
from .policy import Policy, policy_hash, semantic_validate
from .project import load_project
from .rules import check_rule_ids, evaluate
from .spec import catalog


def evaluate_model(model: Model, policy: Policy) -> AnalysisResult:
    semantic_validate(policy)
    check_rule_ids(policy)
    unique = {}
    for f in evaluate(model, policy):
        unique.setdefault(f.fingerprint, f)
    findings = sorted(unique.values(), key=lambda f: (f.rule_id, f.location.module, f.location.symbol, f.fingerprint))
    return AnalysisResult(
        engine_version=VERSION,
        policy_hash=policy_hash(policy),
        analyzed=len(model.units),
        dependencies=len(model.dependencies),
        findings=findings,
        diagnostics=model.diagnostics + [
            'Scope: configured source roots and root selectors only; external service behavior is not analyzed.'
        ],
        spec_version=catalog().spec_version,
    )


def analyze(project_root: Path, policy: Policy) -> AnalysisResult:
    check_rule_ids(policy)
    project = load_project(project_root, policy.sourceRoots)
    return evaluate_model(read_model(project, policy), policy)
