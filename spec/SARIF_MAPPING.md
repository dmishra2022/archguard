# SARIF 2.1.0 mapping

| SARIF | Source |
|---|---|
| `runs[0].tool.driver.name` | `ArchGuard` |
| `runs[0].tool.driver.version` | `engineVersion` |
| `runs[0].tool.driver.rules[]` | One entry per rule ID with findings: `id`, `shortDescription.text` (rule title, or the ID when no catalog entry exists), `help.text` (remediation), optional `helpUri` |
| `results[].ruleId` | `ruleId` |
| `results[].level` | `ERROR` -> `error`, `WARNING` -> `warning`, `INFO` -> `note` |
| `results[].message.text` | `message + "\nEvidence: " + evidence + "\nSuggested correction: " + remediation` |
| `results[].partialFingerprints["archguard/v1"]` | `fingerprint` |
| `results[].baselineState` | `EXISTING` -> `unchanged`, otherwise `new` |
| `results[].locations[0].logicalLocations[0]` | `fullyQualifiedName = location.symbol`, `kind = type` (Java), `module` (Python, TypeScript) or `function` for method-level symbols |
| `results[].locations[0].physicalLocation` | Present only when `location.path` is non-empty: `artifactLocation.uri` (URI-encoded relative path), `uriBaseId = %SRCROOT%`, `region.startLine` only when `line > 0` |
| `results[].properties` | `module`, `target`, `status` |
| `results[].suppressions` | For `SUPPRESSED`: `[{kind: external, status: accepted, justification: ...}]` |
| `runs[0].invocations[0].executionSuccessful` | `true` for completed analyses, `false` for failure reports |
| `runs[0].properties` | `policyHash`, `diagnostics`, `specVersion` |

Failure reports contain a run with `invocations[0].executionSuccessful = false` and a `toolExecutionNotifications` entry with the error message, and no results.

Code-scanning platforms that deduplicate by `partialFingerprints` will therefore track a violation across line movements exactly like ArchGuard baselines do.
