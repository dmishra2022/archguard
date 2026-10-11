# Verification results — ArchGuard 0.1.0

Validated on 2026-10-06 using OpenJDK 17.0.20 and Apache Maven 3.9.9 on Linux.

## Outcome

- Clean reactor `mvn clean install`: **BUILD SUCCESS**, all three implementation modules compiled and installed.
- **56 automated Java tests: 0 failures, 0 errors, 0 skipped.**
- **27 Maven process integration scenarios passed.** Expected negative scenarios returned nonzero as asserted; those are successful tests of enforcement.
- Extracted source ZIP: offline `mvn -o clean verify` returned **exit 0 / BUILD SUCCESS**. This fresh-directory check compiled all modules and reran the Java tests.
- **11 SARIF outputs** validated against the SARIF 2.1.0 JSON schema, including analysis-failure reports.
- Source-integrity assertions passed for both clean and violating consumer builds: analysis did not change application Java files.

## Executed compatibility coverage

| Area | Version / case | Result |
|---|---|---|
| Build and analyzer runtime | OpenJDK 17.0.20 | Passed |
| Maven | 3.9.9 | Passed |
| Spring Boot | 3.4.3 | Package, check and offline check passed |
| Spring Boot legacy | 2.7.18 on Java 17 | Package, check and offline check passed |
| Quarkus | 3.20.0 | Package, check and offline check passed |
| Quarkus legacy | 2.16.12.Final on Java 17 | Package, check and offline check passed |
| Persistence metadata | javax.persistence 2.2 and jakarta.persistence 3.1.0 | Classification tests passed |
| Java 21 / 25 runtime | CI matrix supplied | **Not executed in this environment** |
| Maven 4 / other OSes | Not part of this run | **Not verified** |

Run the analyzer using a JDK compatible with the application's build toolchain. A future class-file version or framework release needs its own compatibility validation; Java 17+ is the source/runtime baseline, not a promise about all future versions.

## Integration coverage

Lifecycle binding, direct goal, offline goal, clean pass, intentional violation failure, report-only mode, baseline capture, overwrite protection, explicit baseline update, new-only adoption, new violation rejection, unchanged baseline behavior, invalid configuration failure, missing output failure, parallel reactor, rejected partial reactor, explicitly acknowledged partial reactor with and without a compatible scoped policy, Java SPI rule pack installation/loading, and the four framework packaging/offline pairs.

Each integration execution creates a unique disposable workspace, preventing old fixture files from contaminating subsequent runs. The retained `integration-results.json` contains only the final successful complete run; raw Maven logs are in `logs/`.

## Java test coverage

Hexagonal boundaries and permitted dependencies; context internals and public contracts; context cycles; custom dependency constraints; disabled rules; custom rule execution/errors/ID collisions; severity gates; stable fingerprints after line movement; baselines and new debt; expired and valid suppressions; deterministic reports and HTML escaping; schema validation failures; actual bytecode extraction; composed Spring stereotypes; JAX-RS endpoints; both persistence namespaces; generic port and HTTP entity exposure; missing/duplicate/corrupt classes; missing direct dependency metadata; conflicting and empty selectors; concurrent importer isolation; iterative cycle traversal on a 20,001-node graph.

## Scale measurement

Synthetic sparse project: **2,000 compiled classes, 5,999 dependencies**.

- Separate compilation process: 2.657 seconds.
- Offline Maven analysis process, including JVM/Maven startup: **2.243 seconds**.
- Peak RSS was not measured in this environment.

This is a reproducible small scale exercise, not an enterprise throughput SLA. Dense graphs, very large rule packs, framework-heavy classpaths and large reports require representative benchmarking. `scripts/benchmark.py` recreates the workload.

## Included evidence and scope limits

`unit-results.json`, `integration-results.json`, `benchmark.json`, `sarif-validation.json`, raw logs, and a real HTML/JSON/SARIF report are included here. Source locations and messages in that report refer to the disposable example project.

The implementation is static structural analysis. Runtime DI/profiles, Quarkus synthetic-bean resolution, business invariant verification, deep dataflow, cross-repository contracts, persistent incremental caching and policy inheritance are not implemented. Review the README and rule catalog before rollout. No code is automatically fixed.
