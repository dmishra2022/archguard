# AI coding agents

ArchGuard checks code the same way regardless of who wrote it. For teams that use AI coding agents (Cursor, Claude Code and similar), the optional **agent skill** adds guidance *before* code is written, so agents place new code in the right role and fix violations themselves instead of leaving them to review.

## What the skill does

1. Reads `architecture.yml` to learn the project's language, roles and profiles.
2. Before writing code, decides which role the new code belongs to, using the placement guide for the language ([Java](https://github.com/dmishra2022/archguard/blob/main/skills/archguard/reference/java-placement.md), [TypeScript](https://github.com/dmishra2022/archguard/blob/main/skills/archguard/reference/typescript-placement.md), [Python](https://github.com/dmishra2022/archguard/blob/main/skills/archguard/reference/python-placement.md)) and the role matrix of each profile.
3. After writing code, runs the check on the changed files with the machine-readable `agent` format, and fixes every new finding using the rule's remediation.
4. Never edits the policy, the baseline or suppressions to make a check pass. It reports such needs to a human instead.

## Install

```bash
mkdir -p .cursor/skills
cp -r <path-to-archguard>/skills/archguard .cursor/skills/
```

The skill uses the analyzer the project already has (Maven plugin or CLI jar, `archguard-cli` from npm, or `archguard-cli` from PyPI). Its check script is [`skills/archguard/scripts/check.sh`](https://github.com/dmishra2022/archguard/blob/main/skills/archguard/scripts/check.sh):

```bash
bash .cursor/skills/archguard/scripts/check.sh --changed --baseline architecture-baseline.json
```

## Automatic feedback with a hook

The example Cursor `stop` hook runs the check when the agent finishes and feeds new findings back to it, so the agent keeps working until the check passes. See [`skills/archguard/hooks`](https://github.com/dmishra2022/archguard/blob/main/skills/archguard/hooks/README.md).

## The agent output format

`--format agent` prints one JSON object per finding, then a summary line, on stdout:

```json
{"rule":"HEX-002","severity":"ERROR","status":"NEW","file":"src/orders/application/place-order.ts","line":3,"symbol":"src/orders/application/place-order","target":"src/orders/infrastructure/sql-order-repository","message":"Application depends on a concrete outer component","fix":"Replace the concrete adapter dependency with an outbound port owned by the core...","fingerprint":"..."}
{"summary":true,"status":"FAILED","new":1,"existing":0,"suppressed":0}
```

The schema is [`spec/schemas/agent-finding.schema.json`](https://github.com/dmishra2022/archguard/blob/main/spec/schemas/agent-finding.schema.json).

## Keeping agents honest

The skill instructs agents not to touch the policy files, but instructions are not enforcement. Enforce it with:

- **CODEOWNERS** on `architecture.yml`, `architecture-baseline.json` and `architecture-suppressions.json`.
- **The CI gate**, which re-runs the full check independently of anything the agent claims.
- Agents must not work around the analyzer with reflection, computed imports or string-based wiring; reviewers should treat those as violations.
