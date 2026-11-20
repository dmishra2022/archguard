# ArchGuard Spec 2.0

The ArchGuard Spec is the language-neutral contract that every ArchGuard analyzer (Java, Python, TypeScript) implements. The analyzer, the agent skill and CI integrations all consume the same files in this directory, so a policy, a rule ID, a finding and an exit code mean the same thing in every language.

Spec version: **2.0.0** (see [VERSIONING.md](VERSIONING.md)).

## Contents

| Path | Normative content |
|---|---|
| [schemas/policy.schema.json](schemas/policy.schema.json) | `architecture.yml` for schemaVersion 1 (Java legacy) and 2 (all languages) |
| [schemas/profile.schema.json](schemas/profile.schema.json) | Shape of a profile file in `profiles/` |
| [schemas/rule.schema.json](schemas/rule.schema.json) | Shape of a rule catalog entry in `rules/` |
| [schemas/findings.schema.json](schemas/findings.schema.json) | `archguard.json` report (completed and failed analyses) |
| [schemas/agent-finding.schema.json](schemas/agent-finding.schema.json) | One line of the `agent` report format |
| [schemas/baseline.schema.json](schemas/baseline.schema.json) | `architecture-baseline.json` |
| [schemas/suppressions.schema.json](schemas/suppressions.schema.json) | Reviewed suppression file |
| [profiles/](profiles/) | Data-driven architecture profiles (role matrices and default rule activation) |
| [infrastructure/](infrastructure/) | Per-language infrastructure/framework dependency lists used by profile rules |
| [rules/](rules/) | Rule catalog: ID, severity, messages, rationale, remediation, per-language examples |
| [SELECTORS.md](SELECTORS.md) | Selector syntax for packages, modules and paths |
| [FINGERPRINT.md](FINGERPRINT.md) | Finding fingerprint algorithm, ordering and deduplication |
| [CLI.md](CLI.md) | Command-line contract, exit codes and report formats |
| [SARIF_MAPPING.md](SARIF_MAPPING.md) | How findings map to SARIF 2.1.0 |
| [conformance/](conformance/) | Cross-language conformance cases with expected findings |
| [languages/typescript.md](languages/typescript.md) | TypeScript/JavaScript binding: units, containers, resolution, framework tags |
| [languages/python.md](languages/python.md) | Python binding: modules, containers, import resolution, framework tags |

## Core model

Every analyzer builds the same abstract model:

- **Unit**: the smallest analyzed element. Java: a class. Python: a module (`.py` file). TypeScript: a module (`.ts`/`.tsx`/`.js` file). Each unit has a fully qualified name, a container name (Java package, Python package, TS directory), a location, exactly one role and at most one bounded context.
- **Dependency**: a directed, static edge from an owned unit to a target unit or external symbol, with human-readable evidence and a location. Kinds: `STATIC` and `HTTP_ENTITY_EXPOSURE`.
- **Role**: one value from the fixed standard vocabulary `DOMAIN`, `APPLICATION`, `INBOUND_PORT`, `OUTBOUND_PORT`, `INBOUND_ADAPTER`, `OUTBOUND_ADAPTER`, `COMPOSITION_ROOT`, or the implicit `UNCLASSIFIED`. The vocabulary is fixed on purpose: profiles differ only in which role-to-role dependencies they forbid, so the same role names, rules and agent guidance apply across languages and architecture styles.
- **Context**: a declared bounded context with owned and exposed selectors.
- **Finding**: a rule violation or informational signal with a stable fingerprint (see [FINGERPRINT.md](FINGERPRINT.md)).

## Evaluation semantics

1. Decode and validate the policy strictly. Unknown keys, duplicate keys, explicit nulls and unknown rule IDs are analysis errors.
2. Resolve `extends` (schemaVersion 2) with the precedence rules in [schemas/policy.schema.json](schemas/policy.schema.json): parents first, local file last; maps merge by key; lists of objects merge by `id`; scalar values are overridden; rule settings marked `locked: true` in a parent cannot be changed by a child.
3. Build the model. A unit matching more than one role or context selector is an analysis error. Units outside `roots` are not evaluated as origins but remain visible as dependency targets.
4. Evaluate rules. **All profile role matrices are always loaded.** A profile only changes the default activation of its rules; `rules.<ID>.enabled` overrides activation in either direction.
5. Deduplicate by fingerprint, sort, apply baseline and suppressions, write reports, then gate on `failOn` and `newOnly`.

An analyzer must never report a pass when analysis could not be completed.

## What is intentionally out of scope

Runtime DI resolution, reflection and dynamic imports, call-path or dataflow analysis, cross-repository contracts and business invariants. Analyzers must state these limits in diagnostics rather than imply coverage.
