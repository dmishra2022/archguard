# Versioning

## Spec version

The spec uses semantic versioning, independent of analyzer versions.

- **Major**: incompatible change to a schema, the fingerprint algorithm, exit codes or the meaning of an existing rule ID. Requires a new policy `schemaVersion` and a baseline regeneration for every consumer.
- **Minor**: additive change. New optional policy keys, new rules, new profiles, new infrastructure entries, new conformance cases. A change to a rule's *detection* semantics (what it matches) is also minor, but must be called out in the changelog because it can change findings and therefore baselines.
- **Patch**: wording, examples and documentation only. Messages and remediations are part of the report, not of the fingerprint, so editing them is a patch change.

Each analyzer declares the spec version it implements (`specVersion` in `archguard.json`) and must pass every conformance case for its language at that version.

## Rule IDs

- Rule IDs are permanent. A removed rule's ID is never reused.
- Built-in IDs use the prefixes `HEX-`, `DDD-`, `LAYER-`, `CYCLE-`, `FW-`, `MODEL-`. Organisation rules and declarative constraints must use a different prefix (for example `ACME-`).
- Default severity changes are minor changes.

## Policy schema versions

| schemaVersion | Spec | Languages | Notes |
|---|---|---|---|
| 1 | 1.x | Java | Original ArchGuard 0.1.0 format. Still accepted. |
| 2 | 2.x | Java, Python, TypeScript | Superset of 1: adds `language`, `kind`, `extends`, `sourceRoots`, `typeOnlyImports`, `unresolvedImports`, `locked` rule settings and data-driven profiles. |

A schemaVersion 1 file is interpreted as `schemaVersion: 2, language: java` with no `extends`.

## Baselines

Baselines bind to the analyzer's engine version and canonical policy hash. Changing either one requires a deliberate, reviewed regeneration. Baselines are per analyzer: a Java baseline is never applied to a Python analysis.
