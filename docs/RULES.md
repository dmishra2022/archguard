# Rule catalog

All findings include a stable ID, severity, fingerprint, module, symbol, available source path/line, evidence, target and suggested correction. A line of 0 means unavailable. JSON is authoritative; HTML and SARIF derive from the same findings. INFO classification signals do not block the default ERROR gate.

| ID | Default activation | Default severity | Meaning |
|---|---|---|---|
| HEX-001 | hexagonal profile | ERROR | Domain depends on application, adapter, composition root, or listed framework/persistence/transport APIs |
| HEX-002 | hexagonal profile | ERROR | Application depends on an adapter or composition root |
| HEX-003 | hexagonal profile | ERROR | Inbound/outbound port depends on adapter, composition root or listed infrastructure APIs |
| HEX-004 | hexagonal profile | ERROR | Inbound and outbound adapters directly depend on one another |
| DDD-001 | ddd profile | ERROR | Context accesses a different declared context's non-exposed package |
| DDD-002 | ddd profile | ERROR | Cycle among declared bounded contexts |
| CYCLE-001 | opt-in | ERROR | Cycle among packages inside the supplied application graph |
| FW-001 | on | ERROR | Recognized HTTP endpoint is explicitly mapped outside INBOUND_ADAPTER |
| FW-002 | on | ERROR | Declared mapped endpoint method exposes JPA entity in return/parameter signature; generic arguments included |
| MODEL-001 | requireClassification=true | ERROR | Application class matches roots but has no role |
| MODEL-002 | on | INFO | Framework classification evidence; no runtime wiring claim |

`rules.<ID>.enabled` and `rules.<ID>.severity` override defaults. Profiles activate rules, not automatic role inference. An unclassified HTTP endpoint does not produce FW-001 because no conflicting intent is known; MODEL-001 can require its classification.

HEX-001/003 infrastructure prefixes: `org.springframework.`, `io.quarkus.`, `jakarta.persistence.`, `javax.persistence.`, `jakarta.ws.rs.`, `javax.ws.rs.`, `jakarta.enterprise.`, `javax.enterprise.`, `jakarta.servlet.`, `javax.servlet.`, `org.hibernate.`, `java.sql.`, `javax.sql.`. These defaults intentionally represent a strict pure-core profile. Disable/override rules or provide custom constraints for a different architectural policy. Not every third-party client library is automatically recognized; add forbidden-dependency constraints for vendor SDKs.

HEX-004 separates inbound from outbound adapter roles; it does not prohibit all dependencies between two adapters of the same role. Model finer boundaries with custom constraints. HTTP exposure checks inspect entity types directly involved in the signature, not recursively every field of arbitrary nested DTOs.

DDD contexts are configured explicitly. Unassigned contexts are not inferred. Shared kernels and published contracts must be deliberately represented using exposed packages and/or custom constraints. Context cycle detection uses the supplied owned classes; external-library contexts can be checked for direct internal access but their hidden dependency graph is not reconstructed.

CYCLE-001 reports one finding per strongly connected component, with its internal package edges. A component may contain several cycles. Breaking an arbitrary single edge may not remove all cycles; re-run the check. Cycles are not automatically "fixed" by moving classes.

Java SPI rules can implement additional domain conventions using the stable graph API. A custom rule returning null, throwing, duplicating another ID, or emitting a different rule ID fails analysis.
