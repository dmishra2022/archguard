# ArchGuard

Offline Java architecture analysis with a Java SDK and Maven plugin. Java 17 bytecode baseline. Version **0.1.0**.

ArchGuard reports structural deviations, source locations when available, evidence, and suggested corrections. It **never modifies application source** and makes **no AI/network calls during analysis**. Maven may download build dependencies unless you use an already provisioned offline repository.

## Build and test

Requirements: JDK 17+, Maven 3.9.x, Python 3 for the Maven integration suite.

```bash
mvn -B clean install
python3 scripts/integration_test.py
```

The integration suite builds real consumer projects, checks expected failures, packages modern and legacy Spring Boot and Quarkus applications, and tests offline execution. It creates disposable projects and logs under `.validation/`. See [verification/RESULTS.md](verification/RESULTS.md) for the results actually obtained for this delivery, rather than assuming every CI matrix cell was executed.

These coordinates are local/private publication coordinates, not an assertion that these artifacts are published to Maven Central. Install this repository first or publish its artifacts to your organization's Maven repository.

## Try a clean project

```bash
cd examples/clean
mvn clean verify
```

Open `target/archguard/index.html`. JSON and SARIF are in the same directory. The `examples/violating` project intentionally fails with `HEX-002` and writes reports before the build fails.

## Add the Maven plugin

Create `architecture.yml` at the Maven multi-module project root. Copy and adapt the policy from `examples/clean/architecture.yml`.

```xml
<plugin>
  <groupId>io.archguard</groupId>
  <artifactId>archguard-maven-plugin</artifactId>
  <version>0.1.0</version>
  <executions>
    <execution>
      <goals><goal>check</goal></goals>
    </execution>
  </executions>
</plugin>
```

`check` binds to `verify`. A dependency declaration alone does not execute checks. Source code is read-only. Unknown rules, invalid policies, missing output and incomplete direct application dependencies are analysis failures, not compliant results.

## Multi-module CI

Invoke the aggregate goal **after compilation** in a separate Maven task segment:

```bash
mvn -B clean compile io.archguard:archguard-maven-plugin:0.1.0:check-reactor
```

This form also works with `-T 2`. Run it from the reactor root. Do not lifecycle-bind `check-reactor` or `baseline` to the parent: an aggregator annotation does not provide an end-of-reactor barrier; ArchGuard rejects that binding. `check-reactor` analyzes the selected reactor in one graph. POM-only modules are skipped; other missing class directories are errors.

Partial reactors fail by default. An explicit `-Darchguard.allowPartialReactor=true` acknowledges limited scope, but does not disable policy selector validation. For that workflow supply a scoped configuration or intentionally set `allowEmptySelectors: true`. A limited scan never establishes cross-repository compliance.

For report-only analysis of one module:

```bash
mvn compile io.archguard:archguard-maven-plugin:0.1.0:analyze
```

## Embed the SDK

Add `io.archguard:archguard-core:0.1.0` to the analysis tool (not to application runtime dependencies unless actually embedding analysis).

```java
Policy policy = Policies.read(Path.of("architecture.yml"));
ModuleInput app = new ModuleInput(
    "com.acme:orders",
    Path.of("target/classes"),
    List.of(Path.of("src/main/java")),
    Path.of(".")); // source paths are relative to this workspace root
AnalysisResult result = new ArchitectureEngine().analyze(
    List.of(app),
    dependencyClasspath, // List<Path>; include compile/provided/runtime metadata
    policy,
    customRules);        // List<ArchitectureRule>; empty is supported
Reports.write(Path.of("target/archguard"), result);
boolean failed = result.fails(policy.failOn(), policy.newOnly());
```

Imports: `io.archguard.api.*`, `io.archguard.config.*`, `io.archguard.engine.*`, `io.archguard.report.Reports`, `java.nio.file.Path`, `java.util.List`.

SDK calls throw when analysis cannot be completed. The Maven adapter converts those into a distinct execution failure and overwrites stale reports with an explicit FAILED result.

## What is implemented

- Direct compiled-code dependency checks, including generic type dependencies.
- Configurable hexagonal role boundaries and DDD bounded-context boundaries.
- Package and bounded-context strongly connected components with concrete evidence.
- Spring stereotypes/composed stereotypes, Spring Data repository ancestry, JAX-RS endpoints, CDI bean signals, JPA entities in both namespaces, and Panache ancestry signals.
- Declared HTTP method signatures exposing JPA entities, including generic type arguments.
- Declarative custom forbidden-dependency rules and Java SPI rule packs.
- Strict YAML decoding and semantic validation; explicit classification requirements.
- Stable violation fingerprints, policy-bound baselines, owned/reasoned/expiring suppressions.
- HTML, JSON, SARIF and console reporting; severity gates and new-only gates.
- Thread-scoped metadata resolution, immutable SDK models, atomic report writes, iterative cycle detection.

## Boundaries you should know

This release performs **static structural analysis**. It does not resolve active Spring profiles, conditional beans, synthetic Quarkus beans, actual DI wiring, reflection targets, runtime call paths, API traffic, or database access. It does not prove business invariants, infer correct aggregate boundaries, or prescribe that all domain models must use one persistence style. Framework classification is informational until a declared boundary or directly observed violation applies.

The DDD pack checks bounded-context coupling and cycles; it is not an aggregate/invariant verifier. HTTP entity checks inspect annotated methods declared on recognized endpoint classes, not inherited or dynamically registered routes. Source-level AST/dataflow analysis and cross-repository service contracts are not implemented. Neither persistent incremental caching nor organization policy inheritance is implemented in 0.1.0. See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for their extension points.

Java 17 is the build baseline. See the tested compatibility matrix in the verification report. Future Java class-file formats are not automatically supported merely because they are newer than 17. Unsupported or unreadable application classes must fail analysis.

## Further documentation

- [Configuration and Maven parameters](docs/CONFIGURATION.md)
- [Rule catalog](docs/RULES.md)
- [SDK architecture and scaling](docs/ARCHITECTURE.md)
- [Custom rules](docs/CUSTOM_RULES.md)
- [Verification results](verification/RESULTS.md)

The repository uses Apache-2.0; see LICENSE. Third-party dependencies retain their own licenses; see THIRD_PARTY.md.
