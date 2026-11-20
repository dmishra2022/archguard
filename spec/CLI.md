# Command-line contract

Every analyzer ships an `archguard` command with the same commands, options, exit codes and outputs. Language-specific options are allowed but must not change the meaning of the shared ones.

## Commands

| Command | Purpose | Gates on policy |
|---|---|---|
| `archguard check` | Analyze, apply baseline and suppressions, write reports, gate | Yes |
| `archguard analyze` | Same analysis and reports, never fails on policy violations | No |
| `archguard baseline` | Write a baseline of current non-INFO findings | No |
| `archguard validate` | Validate the policy only (schema, semantics, `extends` resolution) | n/a |
| `archguard rules` | Print the rule catalog known to this analyzer (JSON with `--json`) | n/a |

## Shared options

| Option | Default | Meaning |
|---|---|---|
| `--config <file>` | `architecture.yml` | Policy file |
| `--project <dir>` | `.` | Project root; source paths in reports are relative to it |
| `--out <dir>` | `target/archguard` (Java), `reports/archguard` (Python, TypeScript) | Report directory |
| `--format <list>` | `json,sarif,html` | Comma-separated subset of `json`, `sarif`, `html`, `agent`, `console` |
| `--baseline <file>` | none | Reviewed baseline to apply |
| `--suppressions <file>` | none | Reviewed suppressions to apply |
| `--changed-files <file or ->` | none | Newline-separated project-relative paths. The full graph is still analyzed; only findings whose origin location is in the list are reported and gated. |
| `--baseline-output <file>` | `architecture-baseline.json` | `baseline` command destination |
| `--overwrite-baseline` | false | Allow replacing an existing baseline |
| `--fail-on <severity>` | policy `failOn` | Override the gate severity |

Java adds `--classes <dir>` (repeatable), `--source-root <dir>` (repeatable), `--classpath <path-list>` and `--classpath-file <file>`. Python and TypeScript read source roots from the policy (`sourceRoots`) or their project configuration. TypeScript adds `--tsconfig <file>` (default `<project>/tsconfig.json`).

## Exit codes

| Code | Meaning |
|---|---|
| 0 | Analysis completed and the gate passed (or the command does not gate) |
| 1 | Analysis completed and the policy gate failed |
| 2 | Analysis could not be completed (invalid policy, missing inputs, unresolved dependencies, rule error). Never a pass. |
| 64 | Command-line usage error |

CI systems must treat 1 as a policy failure and 2 as a broken pipeline.

## Report files

All formats derive from the same normalized findings.

| Format | File | Schema |
|---|---|---|
| json | `archguard.json` | [schemas/findings.schema.json](schemas/findings.schema.json) |
| sarif | `archguard.sarif` | SARIF 2.1.0, see [SARIF_MAPPING.md](SARIF_MAPPING.md) |
| html | `index.html` | Self-contained, no scripts or external assets, escapes all source-derived text |
| agent | `archguard.agent.jsonl` and stdout | One JSON object per line, [schemas/agent-finding.schema.json](schemas/agent-finding.schema.json) |
| console | stdout | Human summary; not machine-readable |

On analysis failure (exit 2) analyzers overwrite `archguard.json`, `archguard.sarif` and `index.html` with explicit failure reports so a stale pass is never left behind.

## Agent format

Designed for coding agents and pre-commit hooks: compact, sorted, no prose wrapping.

```json
{"rule":"HEX-002","severity":"ERROR","status":"NEW","file":"src/main/java/com/acme/orders/application/OrderService.java","line":12,"symbol":"com.acme.orders.application.OrderService","target":"com.acme.orders.adapter.SqlOrderStore","message":"Application depends on a concrete outer component","fix":"Replace the concrete adapter dependency with an outbound port owned by the core. Implement the port in the adapter and wire it in the composition root.","fingerprint":"<64 hex>"}
```

INFO findings are omitted from the agent format. The last line is a summary object: `{"summary":true,"status":"PASSED|FAILED|ERROR","new":N,"existing":N,"suppressed":N}`.
