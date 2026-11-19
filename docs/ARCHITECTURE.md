# SDK architecture and operational contract

## Modules

- `archguard-api`: immutable records and custom rule SPI; no Maven, framework or ArchUnit dependency.
- `archguard-core`: YAML configuration, bytecode import, framework classifiers, built-in rules, debt handling and reporting. Subpackages separate these responsibilities without publishing a dozen tightly coupled artifacts prematurely.
- `archguard-maven-plugin`: Maven lifecycle, reactor and classpath adapter. No analysis logic belongs in the Mojo.

The SDK and plugin share exactly the same engine. Consumers can use the SDK without Maven. A custom rule pack depends only on the API.

## Evidence model

The graph contains owned application classes and their direct dependency edges. Type nodes carry module/source location, declared role, declared context, direct annotations and framework signals. Dependencies retain readable bytecode evidence. HTTP entity exposure is a distinct edge kind with a method-level location. Static type/call relationships do not imply runtime invocation.

The compiler's debug metadata governs line accuracy. Missing lines remain 0. Missing sources produce symbol-only locations. Source paths are relative to an explicit workspace root, and support nonstandard source roots when supplied by Maven. Bytecode remains the analysis authority; compile fresh sources before invoking checks. The plugin does not prove that pre-existing class files are fresh.

The importer rejects duplicate owned class names, missing outputs, unreadable in-scope class files and unresolved direct application dependency metadata. Dependency resources are resolved on demand through a thread-local, closeable URL classloader with the platform classloader as parent. It reads class resources and does not initialize application classes. Framework metadata farther than the dependency import traversal can still be incomplete; this release does not claim full DI resolution.

## Spec-driven rules

`archguard-core` bundles the language-neutral [ArchGuard Spec](../spec/README.md) under `META-INF/archguard/spec/` and loads it through `io.archguard.spec.SpecCatalog`. Rule titles, messages, remediations, default severities and activation come from `spec/rules`. Role-boundary rules are evaluated generically from every profile's role matrix in `spec/profiles`, and HEX-001/003 infrastructure prefixes come from `spec/infrastructure/java.yml`. Bounded-context, cycle and framework detection remain code because they depend on the Java model. `SpecParityTest` checks every role pair against the profile data, and the cross-language conformance suite in `spec/conformance` runs against the built plugin.

## Rules and policy

Declared roles and contexts are authoritative. Overlaps fail instead of selecting whichever pattern appears first. Framework signals never silently remap roles. Rules evaluate immutable graph data; custom rules must be deterministic and read-only. A rule exception aborts evaluation. Java SPI providers are trusted build code, not sandboxed scripts.

Configuration is strictly typed; custom dependency constraints carry their own rationale and remediation. Policy hashing is canonical across map iteration order and profile-set order. Rule IDs are stable and checked for collisions.

## Build integration

Local checks run at verify. Global checks require an explicit post-compilation Maven goal. The engine sees selected modules together and removes their matching artifacts from the external dependency classpath to avoid accidentally choosing an older installed copy. Artifact scope filtering excludes test-only dependencies. POM aggregators do not count as code modules.

Parallel module builds are supported by separate output directories and thread-scoped importer settings. Global goals execute as Maven aggregator goals after the earlier task segment. They do not rely on a static counter of completed modules. Partial reactors require explicit acknowledgement and are marked as limited scope.

## Scale

The engine reads each supplied module's class files once per analysis and resolves external metadata on demand. It does not eagerly import every dependency archive as application code. Graph state is O(V+E); cycle detection is iterative O(V+E), avoiding stack overflow on long chains. Report size grows with findings and cycle-component evidence. There is no unbounded static graph cache.

Role/constraint matching contributes work proportional to the number of applicable selectors and edges. Rules with large selector sets, very broad roots, dense graphs and many findings require measurement. This release has no persistent incremental cache, distributed analyzer or guaranteed production throughput SLA. Use the included benchmark harness and the delivery's measured result to establish a budget on your own repositories. For large builds, run the global analysis in its own Maven process and set an explicit heap budget via MAVEN_OPTS.

A future incremental cache must key compiled bytes, classpath content, policy, framework interpretation and analyzer version. Global cycle/boundary checks must still re-evaluate the impacted complete graph. An SDK dependency is a packaging mechanism, not a scalability guarantee.

## Reports and failures

All formats derive from normalized findings. Fingerprints bind a rule, module, origin, target and semantic evidence, excluding Java source line numbers. Findings are sorted deterministically. Each report file is atomically replaced; the three-file report set is not a filesystem transaction. Consumers must wait for Maven to finish before reading the report set.

Analysis failures replace the report files with explicit failure outputs. Policy violations write complete successful-analysis reports and then throw a Maven policy failure. INFO evidence, accepted debt and suppressions remain inspectable. HTML escapes source-derived text and contains no scripts or external assets.

## Extension path

Framework classifiers and ModelImporter are internal implementation components. Future adapters can add Quarkus post-synthesis metadata, Spring AOT/context metadata, AST evidence or service contracts, but must label evidence source and environment. Future policy inheritance needs explicit precedence and lock semantics. No stub for these features is advertised as working functionality in this release.

## API stability policy

`archguard-api` is the only compatibility surface for rule packs and SDK users. Before 1.0, a minor release may make source-incompatible changes, listed in the release notes. Patch releases never do. From 1.0, binary-incompatible API changes require a major release, and a japicmp check against the previous release enforces this. That check is added with the first published release, because it needs a released artifact to compare against. `archguard-core` packages other than `io.archguard.config`, `io.archguard.engine.ArchitectureEngine`, `io.archguard.engine.ModuleInput`, `io.archguard.report.Reports` and `io.archguard.spec.SpecCatalog` are internal. Keep implementation-specific ArchUnit objects out of custom rule contracts.

Changes since 0.1.0: `Finding.status()` is the enum `Finding.Status` (JSON output is unchanged), `ArchitectureRule.descriptor()` and `RuleDescriptor` were added, and `AnalysisResult` gained optional `specVersion` and `language`.
