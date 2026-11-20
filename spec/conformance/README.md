# Conformance suite

Every analyzer must pass every case for its language. A case is the same architecture expressed in each language, with one language-neutral expectation file.

```
spec/conformance/<case>/
  expected.json            exit code, status and expected findings
  java/                    architecture.yml + src/main/java/...
  python/                  architecture.yml + src/... (+ pyproject.toml)
  typescript/              architecture.yml + src/... (+ tsconfig.json, package.json)
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
python3 scripts/conformance.py --language java --engine cli

(cd typescript/archguard-ts && npm ci && npm run build)
python3 scripts/conformance.py --language typescript

python3 scripts/conformance.py --language python   # runs python/archguard-py/src directly (PyYAML, jsonschema)
```

TypeScript origins and targets are module names (project-relative paths without extension). Python origins and targets are dotted module names (`conf.shop.web.product_resource`). Member symbols use `#` (`src/shop/web/product-resource#ProductResource.get`, `conf.shop.web.product_resource#get_product`); the runner compares the part before `#`.

The Python variants exercise both regular packages (`clean` has `__init__.py` files) and namespace packages (the other cases), relative imports, `if TYPE_CHECKING:` imports, and a FastAPI router imported from another module (`http-entity`).

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
