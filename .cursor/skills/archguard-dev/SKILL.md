---
name: archguard-dev
description: >-
  Guide for changing the ArchGuard repository itself (spec, Java engine, CLI, Maven plugin, skill,
  conformance suite). Use when modifying ArchGuard source, rules, profiles, schemas or analyzers, or
  when asked how ArchGuard works internally.
---

# Working on ArchGuard

## Orient first

- Read `docs/kb/ARCHGUARD_KB.md`: modules, data flow, rule locations, invariants and the verified test baseline.
- Query the code graph instead of grepping blindly (`pipx install graphifyy` if `graphify` is missing):

```bash
graphify query "how is a finding fingerprint computed" --graph docs/kb/graphify-out/graph.json
graphify explain "<full node id>" --graph docs/kb/graphify-out/graph.json
graphify path "Policies" "BuiltinRules" --graph docs/kb/graphify-out/graph.json
```

`docs/kb/graphify-out/GRAPH_REPORT.md` lists god nodes and communities.

## Invariants

- `spec/` is the source of truth. Profiles (role matrices), rule texts, infrastructure lists and schemas live there; the Java engine loads them through `SpecCatalog`. Change behaviour in the spec, not in Java constants.
- schemaVersion 1 policies must keep their policy hash and fingerprints (pinned in `SpecDrivenEngineTest`). Never change fingerprint inputs without a major spec version.
- Exit codes are 0/1/2/64, and an analysis error (2) must never look like a pass.
- `skills/archguard/reference/rules.md` and `docs/architecture.schema.json` are generated or copied from the spec.

## After a change

```bash
python3 scripts/gen_skill_reference.py            # if spec/rules or spec/profiles changed
python3 scripts/spec_check.py
mvn -B install                                    # unit tests, builds the CLI jar
python3 scripts/conformance.py --language java --engine maven
python3 scripts/conformance.py --language java --engine cli
python3 scripts/integration_test.py               # Maven plugin scenarios (slow)
graphify extract . --code-only --out docs/kb && graphify cluster-only docs/kb --no-label
```

A new rule needs a `spec/rules/<ID>.yml` with examples for each language, an entry in `spec/index.yml`, and a conformance case under `spec/conformance/` with `expected.json`.
