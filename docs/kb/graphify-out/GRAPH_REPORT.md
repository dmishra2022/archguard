# Graph Report - kb  (2026-11-19)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 1253 nodes · 2072 edges · 90 communities (53 shown, 37 thin omitted)
- Extraction: 95% EXTRACTED · 5% INFERRED · 0% AMBIGUOUS · INFERRED: 111 edges (avg confidence: 0.85)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `12899dd0`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- Community 0
- Community 1
- Community 2
- Community 3
- Community 4
- Community 5
- Community 6
- Community 7
- Community 8
- Community 9
- Community 10
- Community 11
- Community 12
- Community 13
- Community 14
- Community 15
- Community 16
- Community 17
- Community 18
- Community 19
- Community 20
- Community 21
- Community 22
- Community 23
- Community 24
- Community 25
- Community 26
- Community 27
- Community 28
- Community 29
- Community 30
- Community 31
- Community 32
- Community 33
- Community 34
- Community 35
- Community 36
- Community 37
- Community 38
- Community 39
- Community 40
- Community 41
- Community 42
- Community 43
- Community 44
- Community 45
- Community 46
- Community 47
- Community 48
- Community 49
- Community 50
- Community 51
- Community 52
- Community 53
- Community 54
- Community 55
- Community 56
- Community 57
- Community 58
- Community 59
- Community 60
- Community 61
- Community 62
- Community 63
- Community 64
- Community 65
- Community 66
- Community 67
- Community 68
- Community 69
- Community 70
- Community 71
- Community 72
- Community 73
- Community 74
- Community 75
- Community 76
- Community 77
- Community 78
- Community 79
- Community 80
- Community 81
- Community 82
- Community 83
- Community 84
- Community 85
- Community 86
- Community 87
- Community 88
- Community 89

## God Nodes (most connected - your core abstractions)
1. `EngineTest` - 37 edges
2. `Policy` - 28 edges
3. `ImporterTest` - 26 edges
4. `PolicyTest` - 25 edges
5. `SpecCatalog` - 24 edges
6. `ArchitectureEngine` - 23 edges
7. `Finding` - 22 edges
8. `Policies` - 19 edges
9. `Reports` - 19 edges
10. `MainTest` - 19 edges

## Surprising Connections (you probably didn't know these)
- `Policy` --references--> `Role`  [EXTRACTED]
  archguard-core/src/main/java/io/archguard/config/Policy.java → archguard-api/src/main/java/io/archguard/api/Role.java
- `Options` --references--> `Severity`  [EXTRACTED]
  archguard-cli/src/main/java/io/archguard/cli/Main.java → archguard-api/src/main/java/io/archguard/api/Severity.java
- `ImporterTest` --references--> `ArchitectureModel`  [EXTRACTED]
  archguard-core/src/test/java/io/archguard/engine/ImporterTest.java → archguard-api/src/main/java/io/archguard/api/ArchitectureModel.java
- `Policy` --references--> `Severity`  [EXTRACTED]
  archguard-core/src/main/java/io/archguard/config/Policy.java → archguard-api/src/main/java/io/archguard/api/Severity.java
- `Constraint` --references--> `Severity`  [EXTRACTED]
  archguard-core/src/main/java/io/archguard/config/Policy.java → archguard-api/src/main/java/io/archguard/api/Severity.java

## Import Cycles
- None detected.

## Communities (90 total, 37 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.06
Nodes (5): AnalysisClassResolver, Cycles, FrameworkClassifier, AbstractArchitectureMojo, ClasspathMojo

### Community 1 - "Community 1"
Cohesion: 0.06
Nodes (8): AnalysisResult, ChangedFiles, Inputs, Main, Options, UsageException, Reports, NoSystemExit

### Community 2 - "Community 2"
Cohesion: 0.10
Nodes (9): ArchitectureEngine, Debt, Baseline, Suppression, Suppressions, EngineTest, ArchitectureRule, SpecDrivenEngineTest (+1 more)

### Community 3 - "Community 3"
Cohesion: 0.06
Nodes (24): ArchitectureModel, Dependency, Kind, HTTP_ENTITY_EXPOSURE, STATIC, Finding, Status, EXISTING (+16 more)

### Community 4 - "Community 4"
Cohesion: 0.07
Nodes (16): ArchitectureRule, Role, APPLICATION, COMPOSITION_ROOT, DOMAIN, INBOUND_ADAPTER, INBOUND_PORT, OUTBOUND_ADAPTER (+8 more)

### Community 5 - "Community 5"
Cohesion: 0.09
Nodes (16): SqlOrderStore, PlaceOrder, Order, OrderStore, SqlOrderStore, PlaceOrder, Order, OrderStore (+8 more)

### Community 6 - "Community 6"
Cohesion: 0.07
Nodes (15): run(), check_case(), expected_tuples(), java_dependencies(), main(), maven_artifact(), origin(), run_java_cli() (+7 more)

### Community 7 - "Community 7"
Cohesion: 0.15
Nodes (3): ModelImporter, ModuleInput, ImporterTest

### Community 9 - "Community 9"
Cohesion: 0.09
Nodes (4): AnalyzeMojo, BaselineMojo, CheckMojo, ReactorMojo

### Community 11 - "Community 11"
Cohesion: 0.11
Nodes (6): JpaEntity, WebEndpoint, OrderResource, AdminResource, ProductEntity, ProductResource

### Community 12 - "Community 12"
Cohesion: 0.08
Nodes (23): activation, category, defaultSeverity, evidence, examples, java, python, typescript (+15 more)

### Community 13 - "Community 13"
Cohesion: 0.08
Nodes (23): activation, category, defaultSeverity, evidence, examples, java, python, typescript (+15 more)

### Community 14 - "Community 14"
Cohesion: 0.08
Nodes (23): activation, category, defaultSeverity, evidence, examples, java, python, typescript (+15 more)

### Community 15 - "Community 15"
Cohesion: 0.09
Nodes (22): activation, category, defaultSeverity, evidence, examples, java, python, typescript (+14 more)

### Community 16 - "Community 16"
Cohesion: 0.09
Nodes (22): activation, category, defaultSeverity, evidence, examples, java, python, typescript (+14 more)

### Community 17 - "Community 17"
Cohesion: 0.09
Nodes (22): activation, category, defaultSeverity, evidence, examples, java, python, typescript (+14 more)

### Community 18 - "Community 18"
Cohesion: 0.09
Nodes (21): activation, category, defaultSeverity, examples, java, python, typescript, id (+13 more)

### Community 20 - "Community 20"
Cohesion: 0.10
Nodes (19): jobs, test, java, name, on, if, run, uses (+11 more)

### Community 21 - "Community 21"
Cohesion: 0.10
Nodes (19): activation, category, defaultSeverity, examples, java, python, typescript, id (+11 more)

### Community 22 - "Community 22"
Cohesion: 0.10
Nodes (19): activation, category, defaultSeverity, examples, java, python, typescript, id (+11 more)

### Community 23 - "Community 23"
Cohesion: 0.10
Nodes (19): activation, category, defaultSeverity, examples, java, python, typescript, id (+11 more)

### Community 24 - "Community 24"
Cohesion: 0.10
Nodes (19): activation, category, defaultSeverity, examples, java, python, typescript, id (+11 more)

### Community 25 - "Community 25"
Cohesion: 0.10
Nodes (19): activation, category, defaultSeverity, examples, java, python, typescript, id (+11 more)

### Community 26 - "Community 26"
Cohesion: 0.10
Nodes (19): activation, category, defaultSeverity, examples, java, python, typescript, id (+11 more)

### Community 27 - "Community 27"
Cohesion: 0.12
Nodes (15): contexts, exposedPackages, id, packages, failOn, newOnly, profiles, requireClassification (+7 more)

### Community 28 - "Community 28"
Cohesion: 0.12
Nodes (15): contexts, exposedPackages, id, packages, failOn, newOnly, profiles, requireClassification (+7 more)

### Community 29 - "Community 29"
Cohesion: 0.15
Nodes (3): MicronautEntity, MicronautEndpoint, MicronautRepository

### Community 30 - "Community 30"
Cohesion: 0.14
Nodes (13): contexts, exposedPackages, id, packages, profiles, requireClassification, roles, APPLICATION (+5 more)

### Community 31 - "Community 31"
Cohesion: 0.14
Nodes (13): contexts, exposedPackages, id, packages, profiles, requireClassification, roles, APPLICATION (+5 more)

### Community 32 - "Community 32"
Cohesion: 0.18
Nodes (10): contexts, exposedPackages, id, packages, enabled, profiles, roots, rules (+2 more)

### Community 33 - "Community 33"
Cohesion: 0.18
Nodes (10): activates, description, id, roleRules, crossRoleOnly, forbiddenRoles, forbidInfrastructure, from (+2 more)

### Community 34 - "Community 34"
Cohesion: 0.20
Nodes (9): language, profiles, requireClassification, roles, APPLICATION, INBOUND_ADAPTER, OUTBOUND_ADAPTER, roots (+1 more)

### Community 35 - "Community 35"
Cohesion: 0.40
Nodes (3): OrderDao, OrderService, OrderController

### Community 37 - "Community 37"
Cohesion: 0.22
Nodes (8): activates, description, id, roleRules, forbiddenRoles, from, rule, title

### Community 38 - "Community 38"
Cohesion: 0.25
Nodes (7): profiles, requireClassification, roles, COMPOSITION_ROOT, INBOUND_ADAPTER, roots, schemaVersion

### Community 39 - "Community 39"
Cohesion: 0.25
Nodes (7): profiles, requireClassification, roles, APPLICATION, DOMAIN, roots, schemaVersion

### Community 40 - "Community 40"
Cohesion: 0.25
Nodes (7): profiles, requireClassification, roles, COMPOSITION_ROOT, INBOUND_ADAPTER, roots, schemaVersion

### Community 41 - "Community 41"
Cohesion: 0.25
Nodes (7): profiles, requireClassification, roles, COMPOSITION_ROOT, INBOUND_ADAPTER, roots, schemaVersion

### Community 42 - "Community 42"
Cohesion: 0.25
Nodes (7): contexts, exposedPackages, id, packages, profiles, roots, schemaVersion

### Community 43 - "Community 43"
Cohesion: 0.29
Nodes (6): profiles, requireClassification, roles, INBOUND_ADAPTER, roots, schemaVersion

### Community 44 - "Community 44"
Cohesion: 0.29
Nodes (6): profiles, requireClassification, roles, INBOUND_ADAPTER, roots, schemaVersion

### Community 45 - "Community 45"
Cohesion: 0.29
Nodes (6): profiles, roles, APPLICATION, INBOUND_ADAPTER, roots, schemaVersion

### Community 46 - "Community 46"
Cohesion: 0.29
Nodes (6): profiles, roles, DOMAIN, roots, schemaVersion, unknownKey

### Community 47 - "Community 47"
Cohesion: 0.29
Nodes (6): profiles, requireClassification, roles, DOMAIN, roots, schemaVersion

### Community 48 - "Community 48"
Cohesion: 0.29
Nodes (6): analysisProcessSeconds, classes, compileSeconds, dependencies, maxRssKiB, note

### Community 53 - "Community 53"
Cohesion: 0.33
Nodes (5): activates, description, id, includes, title

### Community 54 - "Community 54"
Cohesion: 0.33
Nodes (5): activates, description, id, includes, title

### Community 59 - "Community 59"
Cohesion: 0.40
Nodes (5): example:company-rules, io.archguard:archguard-api, io.archguard:archguard-cli, io.archguard:archguard-core, io.archguard:archguard-maven-plugin

### Community 60 - "Community 60"
Cohesion: 0.40
Nodes (4): infrastructure, profiles, rules, specVersion

### Community 61 - "Community 61"
Cohesion: 0.40
Nodes (4): description, entries, language, matching

### Community 62 - "Community 62"
Cohesion: 0.40
Nodes (4): description, entries, language, matching

### Community 63 - "Community 63"
Cohesion: 0.40
Nodes (4): description, entries, language, matching

### Community 64 - "Community 64"
Cohesion: 0.40
Nodes (4): activates, description, id, title

## Knowledge Gaps
- **30 isolated node(s):** `HTTP_ENTITY_EXPOSURE`, `STATIC`, `EXISTING`, `NEW`, `SUPPRESSED` (+25 more)
  These have ≤1 connection - possible missing edges. (Counts symbols only; 578 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **37 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `AbstractArchitectureMojo` connect `Community 0` to `Community 1`, `Community 9`?**
  _High betweenness centrality (0.028) - this node is a cross-community bridge._
- **What connects `HTTP_ENTITY_EXPOSURE`, `STATIC`, `EXISTING` to the rest of the system?**
  _30 weakly-connected nodes found - possible missing edges._
- **Should `Community 0` be split into smaller, more focused modules?**
  _Cohesion score 0.05527805527805528 - nodes in this community are weakly interconnected._
- **Why does `Policy` connect `Community 3` to `Community 0`, `Community 2`, `Community 4`, `Community 7`, `Community 8`, `Community 10`?**
  _High betweenness centrality (0.026) - this node is a cross-community bridge._
- **Should `Community 1` be split into smaller, more focused modules?**
  _Cohesion score 0.05755693581780538 - nodes in this community are weakly interconnected._
- **Why does `EngineTest` connect `Community 2` to `Community 0`?**
  _High betweenness centrality (0.016) - this node is a cross-community bridge._
- **Should `Community 2` be split into smaller, more focused modules?**
  _Cohesion score 0.09859791949344188 - nodes in this community are weakly interconnected._