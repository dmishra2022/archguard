# Rule catalog

The authoritative catalog is [spec/rules](https://github.com/dmishra2022/archguard/blob/main/spec/rules): one YAML file per rule with its title, default severity, activation, message, remediation, rationale and bad/good examples for Java, Python and TypeScript. The Java engine loads titles, messages and remediations from it at runtime, and role-boundary rules (HEX, LAYER) are evaluated from the role matrices in [spec/profiles](https://github.com/dmishra2022/archguard/blob/main/spec/profiles).

All findings include a stable ID, severity, fingerprint, module, symbol, available source path/line, evidence, target and suggested correction. A line of 0 means unavailable. JSON is authoritative; HTML and SARIF derive from the same findings. INFO classification signals do not block the default ERROR gate.

| ID | Default activation | Default severity | Meaning |
|---|---|---|---|
| HEX-001 | hexagonal profile | ERROR | Domain depends on application, adapter, composition root, or listed framework/persistence/transport APIs |
| HEX-002 | hexagonal profile | ERROR | Application depends on an adapter or composition root |
| HEX-003 | hexagonal profile | ERROR | Inbound/outbound port depends on adapter, composition root or listed infrastructure APIs |
| HEX-004 | hexagonal profile | ERROR | Inbound and outbound adapters directly depend on one another |
| LAYER-001 | layered profile | ERROR | A lower layer (domain, business, persistence) depends on a higher layer (business, presentation, composition root) |
| LAYER-002 | layered profile | ERROR | Presentation (INBOUND_ADAPTER) depends directly on persistence (OUTBOUND_ADAPTER) |
| DDD-001 | ddd profile | ERROR | Context accesses a different declared context's non-exposed package |
| DDD-002 | ddd profile | ERROR | Cycle among declared bounded contexts |
| CYCLE-001 | opt-in; clean and modular-monolith profiles | ERROR | Cycle among packages inside the supplied application graph |
| FW-001 | on | ERROR | Recognized HTTP endpoint is explicitly mapped outside INBOUND_ADAPTER |
| FW-002 | on | ERROR | Declared mapped endpoint exposes a persistence entity (JPA, TypeORM/MikroORM/Mongoose, SQLAlchemy/Django/SQLModel) in its return or parameter types; generic arguments included |
| MODEL-001 | requireClassification=true | ERROR | Application unit (Java class, TypeScript file, Python module) matches roots but has no role |
| MODEL-002 | on | INFO | Framework classification evidence; no runtime wiring claim |

`rules.<ID>.enabled` and `rules.<ID>.severity` override defaults. Profiles activate rules, not automatic role inference. An unclassified HTTP endpoint does not produce FW-001 because no conflicting intent is known; MODEL-001 can require its classification.

HEX-001/003 infrastructure prefixes ([spec/infrastructure/java.yml](https://github.com/dmishra2022/archguard/blob/main/spec/infrastructure/java.yml)): `org.springframework.`, `io.quarkus.`, `io.micronaut.`, `jakarta.persistence.`, `javax.persistence.`, `jakarta.ws.rs.`, `javax.ws.rs.`, `jakarta.enterprise.`, `javax.enterprise.`, `jakarta.servlet.`, `javax.servlet.`, `org.hibernate.`, `java.sql.`, `javax.sql.`. These defaults intentionally represent a strict pure-core profile. Disable/override rules or provide custom constraints for a different architectural policy. Not every third-party client library is automatically recognized; add forbidden-dependency constraints for vendor SDKs.

The TypeScript and Python lists are [spec/infrastructure/typescript.yml](https://github.com/dmishra2022/archguard/blob/main/spec/infrastructure/typescript.yml) and [spec/infrastructure/python.yml](https://github.com/dmishra2022/archguard/blob/main/spec/infrastructure/python.yml). Python's list deliberately leaves out `pydantic`, which many teams use for value objects; forbid it with a constraint if your policy wants that:

```yaml
constraints:
  - id: ORG-001
    from: ["**.domain.**"]
    forbidden: ["pydantic", "pydantic.**"]
    rationale: "The domain model does not depend on a serialisation library."
```

HEX-004 separates inbound from outbound adapter roles; it does not prohibit all dependencies between two adapters of the same role. Model finer boundaries with custom constraints. HTTP exposure checks inspect entity types directly involved in the signature, not recursively every field of arbitrary nested DTOs.

DDD contexts are configured explicitly. Unassigned contexts are not inferred. Shared kernels and published contracts must be deliberately represented using exposed packages and/or custom constraints. Context cycle detection uses the supplied owned classes; external-library contexts can be checked for direct internal access but their hidden dependency graph is not reconstructed. Code outside every declared context is not checked by DDD-001 or DDD-002. A shared kernel that every context may use is either left outside the contexts or declared as a context that exposes everything:

```yaml
contexts:
  - id: shared
    packages: ["com.acme.shared.**"]
    exposedPackages: ["com.acme.shared.**"]
```

CYCLE-001 reports one finding per strongly connected component, with its internal package edges. A component may contain several cycles. Breaking an arbitrary single edge may not remove all cycles; re-run the check. Cycles are not automatically "fixed" by moving classes. Imports with a literal argument (`importlib.import_module("x")` in Python, `import("./x")` and `require("./x")` in TypeScript) are edges, so plugin-registration patterns where a package imports its submodules and they import the package back form cycles.

Java SPI rules can implement additional domain conventions using the stable graph API. A custom rule returning null, throwing, duplicating another ID, or emitting a different rule ID fails analysis.
