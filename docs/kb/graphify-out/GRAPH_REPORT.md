# Graph Report - kb  (2026-11-19)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 659 nodes · 1073 edges · 69 communities (30 shown, 39 thin omitted)
- Extraction: 94% EXTRACTED · 6% INFERRED · 0% AMBIGUOUS · INFERRED: 61 edges (avg confidence: 0.85)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `3e3f7d08`
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

## God Nodes (most connected - your core abstractions)
1. `EngineTest` - 37 edges
2. `ImporterTest` - 26 edges
3. `Policy` - 21 edges
4. `ArchitectureEngine` - 15 edges
5. `ModelImporter` - 15 edges
6. `AbstractArchitectureMojo` - 15 edges
7. `Finding` - 15 edges
8. `ArchitectureModel` - 15 edges
9. `AnalysisResult` - 14 edges
10. `PolicyTest` - 14 edges

## Surprising Connections (you probably didn't know these)
- `RuleSetting` --references--> `Severity`  [EXTRACTED]
  archguard-core/src/main/java/io/archguard/config/Policy.java → archguard-api/src/main/java/io/archguard/api/Severity.java
- `ImporterTest` --references--> `ArchitectureModel`  [EXTRACTED]
  archguard-core/src/test/java/io/archguard/engine/ImporterTest.java → archguard-api/src/main/java/io/archguard/api/ArchitectureModel.java
- `Policy` --references--> `Role`  [EXTRACTED]
  archguard-core/src/main/java/io/archguard/config/Policy.java → archguard-api/src/main/java/io/archguard/api/Role.java
- `Policy` --references--> `Severity`  [EXTRACTED]
  archguard-core/src/main/java/io/archguard/config/Policy.java → archguard-api/src/main/java/io/archguard/api/Severity.java
- `Constraint` --references--> `Severity`  [EXTRACTED]
  archguard-core/src/main/java/io/archguard/config/Policy.java → archguard-api/src/main/java/io/archguard/api/Severity.java

## Import Cycles
- None detected.

## Communities (69 total, 39 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.06
Nodes (26): ArchitectureModel, Dependency, Kind, HTTP_ENTITY_EXPOSURE, STATIC, Finding, Location, Role (+18 more)

### Community 1 - "Community 1"
Cohesion: 0.12
Nodes (9): RuleSetting, ArchitectureEngine, Debt, Baseline, Suppression, Suppressions, EngineTest, ArchitectureRule (+1 more)

### Community 2 - "Community 2"
Cohesion: 0.07
Nodes (7): AnalysisResult, Reports, AbstractArchitectureMojo, AnalyzeMojo, BaselineMojo, CheckMojo, ReactorMojo

### Community 3 - "Community 3"
Cohesion: 0.04
Nodes (46): additionalProperties, additionalProperties, properties, required, type, type, type, type (+38 more)

### Community 5 - "Community 5"
Cohesion: 0.15
Nodes (3): ModelImporter, ModuleInput, ImporterTest

### Community 7 - "Community 7"
Cohesion: 0.10
Nodes (19): jobs, test, java, name, on, if, run, uses (+11 more)

### Community 9 - "Community 9"
Cohesion: 0.12
Nodes (15): contexts, exposedPackages, id, packages, failOn, newOnly, profiles, requireClassification (+7 more)

### Community 10 - "Community 10"
Cohesion: 0.12
Nodes (15): contexts, exposedPackages, id, packages, failOn, newOnly, profiles, requireClassification (+7 more)

### Community 12 - "Community 12"
Cohesion: 0.15
Nodes (3): MicronautEntity, MicronautEndpoint, MicronautRepository

### Community 15 - "Community 15"
Cohesion: 0.24
Nodes (10): items, minItems, type, items, items, type, maxLength, minLength (+2 more)

### Community 16 - "Community 16"
Cohesion: 0.29
Nodes (10): items, items, items, minItems, type, additionalProperties, properties, required (+2 more)

### Community 19 - "Community 19"
Cohesion: 0.25
Nodes (8): minItems, type, items, minItems, type, COMPOSITION_ROOT, OUTBOUND_PORT, properties

### Community 20 - "Community 20"
Cohesion: 0.25
Nodes (7): profiles, requireClassification, roles, COMPOSITION_ROOT, INBOUND_ADAPTER, roots, schemaVersion

### Community 21 - "Community 21"
Cohesion: 0.25
Nodes (7): profiles, requireClassification, roles, APPLICATION, DOMAIN, roots, schemaVersion

### Community 22 - "Community 22"
Cohesion: 0.25
Nodes (7): profiles, requireClassification, roles, COMPOSITION_ROOT, INBOUND_ADAPTER, roots, schemaVersion

### Community 23 - "Community 23"
Cohesion: 0.25
Nodes (7): profiles, requireClassification, roles, COMPOSITION_ROOT, INBOUND_ADAPTER, roots, schemaVersion

### Community 24 - "Community 24"
Cohesion: 0.29
Nodes (6): profiles, requireClassification, roles, INBOUND_ADAPTER, roots, schemaVersion

### Community 25 - "Community 25"
Cohesion: 0.29
Nodes (6): profiles, requireClassification, roles, INBOUND_ADAPTER, roots, schemaVersion

### Community 26 - "Community 26"
Cohesion: 0.29
Nodes (6): analysisProcessSeconds, classes, compileSeconds, dependencies, maxRssKiB, note

### Community 37 - "Community 37"
Cohesion: 0.50
Nodes (4): items, minItems, type, DOMAIN

### Community 38 - "Community 38"
Cohesion: 0.50
Nodes (4): items, minItems, type, from

### Community 39 - "Community 39"
Cohesion: 0.50
Nodes (4): items, minItems, type, INBOUND_ADAPTER

### Community 40 - "Community 40"
Cohesion: 0.50
Nodes (4): items, minItems, type, INBOUND_PORT

### Community 41 - "Community 41"
Cohesion: 0.50
Nodes (4): items, minItems, type, OUTBOUND_ADAPTER

### Community 42 - "Community 42"
Cohesion: 0.50
Nodes (4): items, minItems, type, packages

### Community 43 - "Community 43"
Cohesion: 0.50
Nodes (4): roots, items, minItems, type

### Community 49 - "Community 49"
Cohesion: 0.50
Nodes (4): example:company-rules, io.archguard:archguard-api, io.archguard:archguard-core, io.archguard:archguard-maven-plugin

### Community 52 - "Community 52"
Cohesion: 0.67
Nodes (3): pattern, type, id

### Community 53 - "Community 53"
Cohesion: 0.67
Nodes (3): rationale, minLength, type

### Community 54 - "Community 54"
Cohesion: 0.67
Nodes (3): remediation, minLength, type

## Knowledge Gaps
- **26 isolated node(s):** `HTTP_ENTITY_EXPOSURE`, `STATIC`, `APPLICATION`, `COMPOSITION_ROOT`, `DOMAIN` (+21 more)
  These have ≤1 connection - possible missing edges. (Counts symbols only; 294 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **39 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `AbstractArchitectureMojo` connect `Community 2` to `Community 4`?**
  _High betweenness centrality (0.039) - this node is a cross-community bridge._
- **What connects `HTTP_ENTITY_EXPOSURE`, `STATIC`, `APPLICATION` to the rest of the system?**
  _26 weakly-connected nodes found - possible missing edges._
- **Should `Community 0` be split into smaller, more focused modules?**
  _Cohesion score 0.06363636363636363 - nodes in this community are weakly interconnected._
- **Why does `Policy` connect `Community 0` to `Community 1`, `Community 4`, `Community 5`, `Community 11`, `Community 14`?**
  _High betweenness centrality (0.030) - this node is a cross-community bridge._
- **Should `Community 1` be split into smaller, more focused modules?**
  _Cohesion score 0.1243885394828791 - nodes in this community are weakly interconnected._
- **Why does `EngineTest` connect `Community 1` to `Community 0`, `Community 4`?**
  _High betweenness centrality (0.024) - this node is a cross-community bridge._
- **Should `Community 2` be split into smaller, more focused modules?**
  _Cohesion score 0.06567992599444958 - nodes in this community are weakly interconnected._