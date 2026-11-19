# Conformance suite

Every analyzer must pass every case for its language. A case is the same architecture expressed in each language, with one language-neutral expectation file.

```
spec/conformance/<case>/
  expected.json            exit code, status and expected findings
  java/                    architecture.yml + src/main/java/...
  python/                  architecture.yml + src/...           (added with the Python analyzer)
  typescript/              architecture.yml + src/... + tsconfig (added with the TypeScript analyzer)
```

## expected.json

```json
{
  "case": "hex-002",
  "description": "...",
  "status": "PASSED | FAILED | ERROR",
  "exitCode": 0,
  "findings": [
    {
      "rule": "HEX-002",
      "severity": "ERROR",
      "origin": { "java": "conf.orders.application.PlaceOrder" },
      "target": { "java": "conf.orders.adapter.SqlOrderStore" }
    }
  ],
  "java": { "dependencies": ["group:artifact:version"] }
}
```

## Comparison semantics

- The exit code must equal `exitCode` (0 compliant, 1 policy violation, 2 analysis error).
- For completed analyses, the **set** of `(rule, severity, origin, target)` over all non-INFO findings must equal the expected set for that language. Several dependency edges between the same two units (field, parameter, call) produce several findings with distinct fingerprints; they collapse to one tuple here because languages express the same dependency with different numbers of edges.
- INFO findings (framework signals) are language-specific and are not compared.
- For `ERROR` cases the analyzer must write a failure report (`analysisStatus: FAILED`) and no compliant result.

## Running

```bash
mvn -B install                                  # Java engine and plugin
python3 scripts/conformance.py --language java
```

The runner copies each case to a temporary directory, so the suite never writes into `spec/`.

## Cases

| Case | Architecture | Expected |
|---|---|---|
| clean | hexagonal + ddd, one context, port implemented by adapter | pass |
| hex-002 | application uses a concrete adapter | HEX-002 |
| ddd-001 | billing uses an orders internal type | DDD-001 |
| cycles | orders and billing public APIs use each other | DDD-002, CYCLE-001 |
| http-entity | endpoint returns a persistence entity; endpoint declared in the application role | FW-002, FW-001 |
| unclassified | a unit under roots has no role, classification required | MODEL-001 |
| invalid-policy | policy contains an unknown key | analysis error, exit 2 |
| layered | schemaVersion 2, glob selectors, layered profile: persistence calls business, presentation calls persistence | LAYER-001, LAYER-002 |
