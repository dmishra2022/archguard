# Graph Report - kb  (2026-11-20)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 3450 nodes · 5452 edges · 293 communities (188 shown, 105 thin omitted)
- Extraction: 96% EXTRACTED · 4% INFERRED · 0% AMBIGUOUS · INFERRED: 208 edges (avg confidence: 0.87)
- Token cost: 0 input · 0 output

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
- Community 90
- Community 91
- Community 92
- Community 93
- Community 94
- Community 95
- Community 96
- Community 97
- Community 98
- Community 99
- Community 100
- Community 101
- Community 102
- Community 103
- Community 104
- Community 105
- Community 106
- Community 107
- Community 108
- Community 109
- Community 110
- Community 111
- Community 112
- Community 113
- Community 114
- Community 115
- Community 116
- Community 117
- Community 118
- Community 119
- Community 120
- Community 121
- Community 122
- Community 123
- Community 124
- Community 125
- Community 126
- Community 127
- Community 128
- Community 129
- Community 130
- Community 131
- Community 132
- Community 133
- Community 134
- Community 135
- Community 136
- Community 137
- Community 138
- Community 139
- Community 140
- Community 141
- Community 142
- Community 143
- Community 144
- Community 145
- Community 146
- Community 147
- Community 148
- Community 149
- Community 150
- Community 151
- Community 152
- Community 153
- Community 154
- Community 155
- Community 156
- Community 157
- Community 158
- Community 159
- Community 160
- Community 161
- Community 162
- Community 163
- Community 164
- Community 165
- Community 166
- Community 167
- Community 168
- Community 169
- Community 170
- Community 171
- Community 172
- Community 173
- Community 174
- Community 175
- Community 176
- Community 177
- Community 178
- Community 179
- Community 180
- Community 181
- Community 182
- Community 183
- Community 184
- Community 185
- Community 186
- Community 187
- Community 188
- Community 189
- Community 190
- Community 191
- Community 193
- Community 194
- Community 195
- Community 196
- Community 197
- Community 198
- Community 199
- Community 200
- Community 201
- Community 202
- Community 203
- Community 204
- Community 205
- Community 206
- Community 207
- Community 208
- Community 209
- Community 210
- Community 211
- Community 212
- Community 213
- Community 214
- Community 215
- Community 216
- Community 217
- Community 218
- Community 219
- Community 220
- Community 221
- Community 222
- Community 223
- Community 224
- Community 225
- Community 226
- Community 227
- Community 228
- Community 229
- Community 230
- Community 231
- Community 232
- Community 233
- Community 234
- Community 235
- Community 236
- Community 237
- Community 238
- Community 239
- Community 240
- Community 241
- Community 242
- Community 243
- Community 244
- Community 245
- Community 246
- Community 247
- Community 248
- Community 249
- Community 250
- Community 251
- Community 254
- Community 255
- Community 256
- Community 258
- Community 259
- Community 273
- Community 274
- Community 275
- Community 276
- Community 277
- Community 278
- Community 279
- Community 280
- Community 281
- Community 282
- Community 283
- Community 284
- Community 285
- Community 286
- Community 287
- Community 288

## God Nodes (most connected - your core abstractions)
1. `EngineTest` - 37 edges
2. `AnalyzerTest` - 28 edges
3. `SpecCatalog` - 26 edges
4. `ImporterTest` - 26 edges
5. `PolicyTest` - 25 edges
6. `read_model()` - 25 edges
7. `ArchitectureEngine` - 23 edges
8. `ModuleInfo` - 23 edges
9. `with` - 23 edges
10. `inputs` - 22 edges

## Surprising Connections (you probably didn't know these)
- `Inputs` --references--> `ModuleInput`  [EXTRACTED]
  archguard-cli/src/main/java/io/archguard/cli/Inputs.java → archguard-core/src/main/java/io/archguard/engine/ModuleInput.java
- `book_by_isbn()` --uses--> `Book`  [INFERRED]
  examples/python-django/catalog/selectors.py → examples/python-django/catalog/models.py
- `AnalyzerTest` --uses--> `PolicyError`  [INFERRED]
  python/archguard-py/tests/test_analyzer.py → python/archguard-py/src/archguard/policy.py
- `SourceIndex` --uses--> `AnalysisError`  [INFERRED]
  python/archguard-py/src/archguard/index.py → python/archguard-py/src/archguard/model.py
- `read_model()` --uses--> `Project`  [INFERRED]
  python/archguard-py/src/archguard/importer.py → python/archguard-py/src/archguard/project.py

## Import Cycles
- None detected.

## Communities (293 total, 105 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.08
Nodes (7): Policies, Source, Policy, Constraint, Context, RuleSetting, PolicyTest

### Community 1 - "Community 1"
Cohesion: 0.08
Nodes (5): Inputs, ModelImporter, ModuleInput, ImporterTest, NoSystemExit

### Community 2 - "Community 2"
Cohesion: 0.09
Nodes (44): isNestHttpMethod(), allTypeOnly(), cmp(), collectEntities(), collectImports(), contextOf(), httpEntityExposures(), ImportVerb (+36 more)

### Community 3 - "Community 3"
Cohesion: 0.09
Nodes (16): SqlOrderStore, PlaceOrder, Order, OrderStore, SqlOrderStore, PlaceOrder, Order, OrderStore (+8 more)

### Community 4 - "Community 4"
Cohesion: 0.10
Nodes (4): Main, Options, UsageException, Reports

### Community 5 - "Community 5"
Cohesion: 0.10
Nodes (25): normalize_path(), restrict_to_changed_files(), main(), Options, parse_options(), value(), run(), UsageError (+17 more)

### Community 6 - "Community 6"
Cohesion: 0.13
Nodes (29): analyze(), evaluate_model(), context_of(), _http_entity_exposures(), read_model(), _require_match(), role_of(), _single() (+21 more)

### Community 7 - "Community 7"
Cohesion: 0.11
Nodes (12): _abstract(), _annotated_injection(), annotation_leaves(), _assigns(), _callee(), Frameworks, _injected(), _mapped() (+4 more)

### Community 8 - "Community 8"
Cohesion: 0.05
Nodes (44): CODE, EXPECT, LANGUAGE, OUTCOME, RULE, SARIF, URI, name (+36 more)

### Community 9 - "Community 9"
Cohesion: 0.05
Nodes (41): ajv, @types/node, typescript, yaml, author, bin, archguard, bugs (+33 more)

### Community 10 - "Community 10"
Cohesion: 0.09
Nodes (16): BookListApi, LendBookApi, checksum_valid(), remote_title(), Migration, Author, Book, TimeStamped (+8 more)

### Community 11 - "Community 11"
Cohesion: 0.10
Nodes (24): _by_id(), _canonical(), Constraint, _construct_mapping(), Context, _identifier(), merge(), _parent_file() (+16 more)

### Community 12 - "Community 12"
Cohesion: 0.06
Nodes (7): place_order(), get_order(), place_order(), status(), Base, ProductEntity, get_product()

### Community 14 - "Community 14"
Cohesion: 0.06
Nodes (35): runs-on, steps, concurrency, cancel-in-progress, group, environment, if, needs (+27 more)

### Community 15 - "Community 15"
Cohesion: 0.13
Nodes (29): normalizePath(), restrictToChangedFiles(), writeBaseline(), COMMANDS, ERROR, Io, OK, parseOptions() (+21 more)

### Community 16 - "Community 16"
Cohesion: 0.11
Nodes (27): Options, Severity, byId(), canonical(), Constraint, Context, isObject(), merge() (+19 more)

### Community 17 - "Community 17"
Cohesion: 0.07
Nodes (31): run, jobs, package, test, node, name, on, pull_request (+23 more)

### Community 18 - "Community 18"
Cohesion: 0.15
Nodes (26): analyze(), cmp(), evaluateModel(), LANGUAGE, Role, ROLES, Policy, policyHash() (+18 more)

### Community 19 - "Community 19"
Cohesion: 0.07
Nodes (29): run, jobs, package, test, python, name, on, pull_request (+21 more)

### Community 20 - "Community 20"
Cohesion: 0.12
Nodes (10): Resolver, default_source_roots(), distribution_name(), load_project(), module_name(), Project, _section_name(), _skip_dir() (+2 more)

### Community 21 - "Community 21"
Cohesion: 0.07
Nodes (27): enabled, severity, locked, severity, locked, severity, failOn, locked (+19 more)

### Community 24 - "Community 24"
Cohesion: 0.09
Nodes (4): AnalyzeMojo, BaselineMojo, CheckMojo, ReactorMojo

### Community 25 - "Community 25"
Cohesion: 0.16
Nodes (5): ORDER_REPOSITORY, OrderRepository, Order, OrderEntity, TypeOrmOrderRepository

### Community 26 - "Community 26"
Cohesion: 0.11
Nodes (11): AnalysisResult, Finding, Status, EXISTING, NEW, SUPPRESSED, Severity, ERROR (+3 more)

### Community 27 - "Community 27"
Cohesion: 0.11
Nodes (6): JpaEntity, WebEndpoint, OrderResource, AdminResource, ProductEntity, ProductResource

### Community 28 - "Community 28"
Cohesion: 0.12
Nodes (22): dependencies, @nestjs/common@^11.0.0, @nestjs/core@^11.0.0, @nestjs/typeorm@^11.0.0, typeorm@^0.3.20, description, @nestjs/common, @nestjs/core (+14 more)

### Community 29 - "Community 29"
Cohesion: 0.08
Nodes (23): activation, category, defaultSeverity, evidence, examples, java, python, typescript (+15 more)

### Community 30 - "Community 30"
Cohesion: 0.08
Nodes (23): activation, category, defaultSeverity, evidence, examples, java, python, typescript (+15 more)

### Community 31 - "Community 31"
Cohesion: 0.08
Nodes (23): activation, category, defaultSeverity, evidence, examples, java, python, typescript (+15 more)

### Community 32 - "Community 32"
Cohesion: 0.12
Nodes (4): OrderEntity, OrderResponse, PlaceOrderRequest, OrdersController

### Community 33 - "Community 33"
Cohesion: 0.09
Nodes (22): runs-on, steps, strategy, jobs, architecture, example, name, on (+14 more)

### Community 34 - "Community 34"
Cohesion: 0.10
Nodes (23): name, url, npm-public, pypi, testpypi, environment, if, needs (+15 more)

### Community 35 - "Community 35"
Cohesion: 0.09
Nodes (22): activation, category, defaultSeverity, evidence, examples, java, python, typescript (+14 more)

### Community 36 - "Community 36"
Cohesion: 0.09
Nodes (22): activation, category, defaultSeverity, evidence, examples, java, python, typescript (+14 more)

### Community 37 - "Community 37"
Cohesion: 0.09
Nodes (22): activation, category, defaultSeverity, evidence, examples, java, python, typescript (+14 more)

### Community 39 - "Community 39"
Cohesion: 0.15
Nodes (3): ArchitectureRule, ArchitectureRule, ArchitectureRule

### Community 40 - "Community 40"
Cohesion: 0.09
Nodes (21): activation, category, defaultSeverity, examples, java, python, typescript, id (+13 more)

### Community 41 - "Community 41"
Cohesion: 0.21
Nodes (5): PlaceOrder, ORDER_REPOSITORY, OrderRepository, Order, TypeOrmOrderRepository

### Community 43 - "Community 43"
Cohesion: 0.21
Nodes (3): ArchitectureEngine, SpecDrivenEngineTest, ArchitectureRule

### Community 44 - "Community 44"
Cohesion: 0.19
Nodes (3): SpecCatalog, Profile, RoleRule

### Community 45 - "Community 45"
Cohesion: 0.10
Nodes (19): jobs, test, java, name, on, if, run, uses (+11 more)

### Community 46 - "Community 46"
Cohesion: 0.10
Nodes (19): contexts, exposedPackages, id, packages, failOn, language, newOnly, profiles (+11 more)

### Community 47 - "Community 47"
Cohesion: 0.10
Nodes (19): contexts, exposedPackages, id, packages, failOn, language, newOnly, profiles (+11 more)

### Community 48 - "Community 48"
Cohesion: 0.10
Nodes (19): contexts, exposedPackages, id, packages, failOn, language, newOnly, profiles (+11 more)

### Community 49 - "Community 49"
Cohesion: 0.10
Nodes (19): activation, category, defaultSeverity, examples, java, python, typescript, id (+11 more)

### Community 50 - "Community 50"
Cohesion: 0.10
Nodes (19): activation, category, defaultSeverity, examples, java, python, typescript, id (+11 more)

### Community 51 - "Community 51"
Cohesion: 0.10
Nodes (19): activation, category, defaultSeverity, examples, java, python, typescript, id (+11 more)

### Community 52 - "Community 52"
Cohesion: 0.10
Nodes (19): activation, category, defaultSeverity, examples, java, python, typescript, id (+11 more)

### Community 53 - "Community 53"
Cohesion: 0.10
Nodes (19): activation, category, defaultSeverity, examples, java, python, typescript, id (+11 more)

### Community 54 - "Community 54"
Cohesion: 0.10
Nodes (19): activation, category, defaultSeverity, examples, java, python, typescript, id (+11 more)

### Community 55 - "Community 55"
Cohesion: 0.15
Nodes (18): applyDebt(), onlyKeys(), readJson(), Suppression, today(), validDate(), AnalysisError, ArchitectureModel (+10 more)

### Community 56 - "Community 56"
Cohesion: 0.16
Nodes (19): Binding, bindingCache, bindings(), ENDPOINT_TAGS, ENTITY_MODULES, exportsNames(), frameworkTags(), GRAPHQL_RESOLVERS (+11 more)

### Community 58 - "Community 58"
Cohesion: 0.16
Nodes (12): check_agent_output(), check_case(), expected_tuples(), java_dependencies(), main(), maven_artifact(), origin(), run_java_cli() (+4 more)

### Community 59 - "Community 59"
Cohesion: 0.11
Nodes (18): constraints, forbidden, from, id, rationale, remediation, language, profiles (+10 more)

### Community 60 - "Community 60"
Cohesion: 0.11
Nodes (18): runs-on, steps, jobs, conformance, name, on, pull_request, push (+10 more)

### Community 61 - "Community 61"
Cohesion: 0.14
Nodes (6): OrderLineIn, OrderResponse, PlaceOrderRequest, OrderLineIn, OrderResponse, PlaceOrderRequest

### Community 62 - "Community 62"
Cohesion: 0.11
Nodes (17): constraints, forbidden, from, id, rationale, remediation, contexts, exposedPackages (+9 more)

### Community 63 - "Community 63"
Cohesion: 0.11
Nodes (17): contexts, exposedPackages, id, packages, failOn, language, profiles, requireClassification (+9 more)

### Community 64 - "Community 64"
Cohesion: 0.11
Nodes (17): contexts, exposedPackages, id, packages, failOn, language, profiles, requireClassification (+9 more)

### Community 65 - "Community 65"
Cohesion: 0.11
Nodes (17): contexts, exposedPackages, id, packages, failOn, language, profiles, requireClassification (+9 more)

### Community 66 - "Community 66"
Cohesion: 0.11
Nodes (17): contexts, exposedPackages, id, packages, failOn, language, profiles, requireClassification (+9 more)

### Community 67 - "Community 67"
Cohesion: 0.15
Nodes (7): collect_imports(), visit(), _dotted(), RawImport, _type_checking(), absolute(), SourceIndex

### Community 68 - "Community 68"
Cohesion: 0.15
Nodes (6): main(), rebase(), cell(), escape(), main(), repo_path()

### Community 69 - "Community 69"
Cohesion: 0.21
Nodes (7): build(), comparable(), export_sources(), graphify(), installed_version(), main(), main()

### Community 70 - "Community 70"
Cohesion: 0.12
Nodes (17): outputs, runs-on, jobs, build, maven, npm-internal, pypi-internal, if (+9 more)

### Community 71 - "Community 71"
Cohesion: 0.16
Nodes (6): Dependency, Kind, HTTP_ENTITY_EXPOSURE, STATIC, Location, TypeInfo

### Community 73 - "Community 73"
Cohesion: 0.12
Nodes (15): failOn, language, newOnly, profiles, requireClassification, roles, APPLICATION, COMPOSITION_ROOT (+7 more)

### Community 74 - "Community 74"
Cohesion: 0.12
Nodes (15): enabled, language, newOnly, profiles, requireClassification, roles, APPLICATION, COMPOSITION_ROOT (+7 more)

### Community 75 - "Community 75"
Cohesion: 0.12
Nodes (15): enabled, language, newOnly, profiles, roles, APPLICATION, COMPOSITION_ROOT, DOMAIN (+7 more)

### Community 76 - "Community 76"
Cohesion: 0.12
Nodes (15): contexts, exposedPackages, id, packages, failOn, newOnly, profiles, requireClassification (+7 more)

### Community 77 - "Community 77"
Cohesion: 0.12
Nodes (15): contexts, exposedPackages, id, packages, failOn, newOnly, profiles, requireClassification (+7 more)

### Community 78 - "Community 78"
Cohesion: 0.18
Nodes (6): Catalog, Profile, RoleRule, _roles(), RuleSpec, spec_directory()

### Community 79 - "Community 79"
Cohesion: 0.12
Nodes (3): pkg, source, target

### Community 80 - "Community 80"
Cohesion: 0.12
Nodes (15): compilerOptions, declaration, esModuleInterop, module, moduleResolution, newLine, noFallthroughCasesInSwitch, noImplicitOverride (+7 more)

### Community 82 - "Community 82"
Cohesion: 0.18
Nodes (4): Io, main(), split(), Project

### Community 83 - "Community 83"
Cohesion: 0.13
Nodes (14): enabled, language, profiles, roles, APPLICATION, COMPOSITION_ROOT, DOMAIN, INBOUND_ADAPTER (+6 more)

### Community 84 - "Community 84"
Cohesion: 0.15
Nodes (4): AppModule, OrdersModule, AppModule, OrdersModule

### Community 85 - "Community 85"
Cohesion: 0.18
Nodes (4): PlaceOrder, OrderResponse, PlaceOrderRequest, OrdersController

### Community 86 - "Community 86"
Cohesion: 0.13
Nodes (14): runs-on, steps, jobs, freshness, name, on, pull_request, push (+6 more)

### Community 87 - "Community 87"
Cohesion: 0.13
Nodes (15): with, cache, distribution, if-no-files-found, java-version, name, node-version, packages-dir (+7 more)

### Community 88 - "Community 88"
Cohesion: 0.13
Nodes (14): contexts, exposedPackages, id, packages, language, profiles, requireClassification, roles (+6 more)

### Community 89 - "Community 89"
Cohesion: 0.13
Nodes (14): contexts, exposedPackages, id, packages, language, profiles, requireClassification, roles (+6 more)

### Community 90 - "Community 90"
Cohesion: 0.13
Nodes (14): contexts, exposedPackages, id, packages, language, profiles, requireClassification, roles (+6 more)

### Community 91 - "Community 91"
Cohesion: 0.13
Nodes (14): contexts, exposedPackages, id, packages, language, profiles, requireClassification, roles (+6 more)

### Community 92 - "Community 92"
Cohesion: 0.14
Nodes (14): ARCHGUARD_LANGUAGE, CODE, INPUT_ANNOTATIONS, INPUT_ARCHGUARD_VERSION, INPUT_BASELINE, INPUT_CHANGED_FILES_ONLY, INPUT_CLI_COMMAND, INPUT_CLI_JAR (+6 more)

### Community 94 - "Community 94"
Cohesion: 0.15
Nodes (3): MicronautEntity, MicronautEndpoint, MicronautRepository

### Community 95 - "Community 95"
Cohesion: 0.22
Nodes (3): Order, OrderError, OrderLine

### Community 96 - "Community 96"
Cohesion: 0.14
Nodes (13): description, label, options, render, body, attributes, id, type (+5 more)

### Community 97 - "Community 97"
Cohesion: 0.24
Nodes (4): Analyzer, check(), policy(), run()

### Community 98 - "Community 98"
Cohesion: 0.14
Nodes (13): contexts, exposedPackages, id, packages, profiles, requireClassification, roles, APPLICATION (+5 more)

### Community 99 - "Community 99"
Cohesion: 0.14
Nodes (13): contexts, exposedPackages, id, packages, profiles, requireClassification, roles, APPLICATION (+5 more)

### Community 100 - "Community 100"
Cohesion: 0.15
Nodes (13): description, value, description, value, outputs, exit-code, new-findings, report-dir (+5 more)

### Community 101 - "Community 101"
Cohesion: 0.15
Nodes (12): description, label, value, body, attributes, id, type, validations (+4 more)

### Community 102 - "Community 102"
Cohesion: 0.28
Nodes (13): steps, steps, steps, steps, steps, steps, id, if (+5 more)

### Community 103 - "Community 103"
Cohesion: 0.15
Nodes (13): publish, testpypi, on, push, workflow_dispatch, default, description, type (+5 more)

### Community 104 - "Community 104"
Cohesion: 0.32
Nodes (4): SqlOrderStore, PlaceOrder, Order, OrderStore

### Community 105 - "Community 105"
Cohesion: 0.26
Nodes (3): PlaceOrder, Order, OrderStore

### Community 106 - "Community 106"
Cohesion: 0.20
Nodes (3): ArchitectureModel, ArchitectureRule, RuleDescriptor

### Community 107 - "Community 107"
Cohesion: 0.21
Nodes (3): BuildPy, bundle_spec(), Sdist

### Community 108 - "Community 108"
Cohesion: 0.17
Nodes (11): contexts, exposedPackages, id, packages, failOn, language, newOnly, profiles (+3 more)

### Community 109 - "Community 109"
Cohesion: 0.27
Nodes (3): Order, OrderError, OrderLine

### Community 110 - "Community 110"
Cohesion: 0.17
Nodes (11): contexts, exposedPackages, id, packages, enabled, language, profiles, roots (+3 more)

### Community 111 - "Community 111"
Cohesion: 0.17
Nodes (11): contexts, exposedPackages, id, packages, enabled, language, profiles, roots (+3 more)

### Community 112 - "Community 112"
Cohesion: 0.35
Nodes (4): SqlOrderStore, PlaceOrder, Order, OrderStore

### Community 115 - "Community 115"
Cohesion: 0.31
Nodes (4): Debt, Baseline, Suppression, Suppressions

### Community 116 - "Community 116"
Cohesion: 0.31
Nodes (5): apply_debt(), _only_keys(), _read_json(), _valid_date(), AnalysisError

### Community 117 - "Community 117"
Cohesion: 0.25
Nodes (6): Base, OrderLineRecord, OrderRecord, Base, OrderLineRecord, OrderRecord

### Community 118 - "Community 118"
Cohesion: 0.18
Nodes (10): env, PUBLISH, if, needs, permissions, runs-on, github-release, name (+2 more)

### Community 119 - "Community 119"
Cohesion: 0.25
Nodes (5): _match(), matches_one(), _segments(), validate_selector(), OrderSummary

### Community 120 - "Community 120"
Cohesion: 0.18
Nodes (10): contexts, exposedPackages, id, packages, enabled, profiles, roots, rules (+2 more)

### Community 121 - "Community 121"
Cohesion: 0.44
Nodes (3): OrderDao, OrderService, OrderController

### Community 122 - "Community 122"
Cohesion: 0.18
Nodes (10): activates, description, id, roleRules, crossRoleOnly, forbiddenRoles, forbidInfrastructure, from (+2 more)

### Community 123 - "Community 123"
Cohesion: 0.20
Nodes (10): with, category, distribution, if-no-files-found, java-version, name, node-version, path (+2 more)

### Community 126 - "Community 126"
Cohesion: 0.20
Nodes (9): Role, APPLICATION, COMPOSITION_ROOT, DOMAIN, INBOUND_ADAPTER, INBOUND_PORT, OUTBOUND_ADAPTER, OUTBOUND_PORT (+1 more)

### Community 127 - "Community 127"
Cohesion: 0.20
Nodes (9): compilerOptions, emitDecoratorMetadata, experimentalDecorators, module, moduleResolution, outDir, strict, target (+1 more)

### Community 128 - "Community 128"
Cohesion: 0.20
Nodes (9): compilerOptions, emitDecoratorMetadata, experimentalDecorators, module, moduleResolution, outDir, strict, target (+1 more)

### Community 129 - "Community 129"
Cohesion: 0.20
Nodes (10): GH_TOKEN, MAVEN_PASSWORD, MAVEN_USERNAME, NODE_AUTH_TOKEN, REPOSITORY, TAG, TWINE_PASSWORD, TWINE_REPOSITORY_URL (+2 more)

### Community 130 - "Community 130"
Cohesion: 0.20
Nodes (9): compilerOptions, module, moduleResolution, noEmit, paths, strict, target, include (+1 more)

### Community 131 - "Community 131"
Cohesion: 0.20
Nodes (9): compilerOptions, emitDecoratorMetadata, experimentalDecorators, module, moduleResolution, noEmit, strict, target (+1 more)

### Community 132 - "Community 132"
Cohesion: 0.20
Nodes (9): language, profiles, requireClassification, roles, APPLICATION, INBOUND_ADAPTER, OUTBOUND_ADAPTER, roots (+1 more)

### Community 133 - "Community 133"
Cohesion: 0.40
Nodes (3): OrderDao, OrderService, OrderController

### Community 134 - "Community 134"
Cohesion: 0.20
Nodes (9): language, profiles, requireClassification, roles, APPLICATION, INBOUND_ADAPTER, OUTBOUND_ADAPTER, roots (+1 more)

### Community 135 - "Community 135"
Cohesion: 0.20
Nodes (9): language, profiles, requireClassification, roles, APPLICATION, INBOUND_ADAPTER, OUTBOUND_ADAPTER, roots (+1 more)

### Community 136 - "Community 136"
Cohesion: 0.40
Nodes (3): OrderDao, OrderService, OrderController

### Community 141 - "Community 141"
Cohesion: 0.22
Nodes (8): contexts, exposedPackages, id, packages, language, profiles, roots, schemaVersion

### Community 142 - "Community 142"
Cohesion: 0.22
Nodes (8): contexts, exposedPackages, id, packages, language, profiles, roots, schemaVersion

### Community 143 - "Community 143"
Cohesion: 0.22
Nodes (8): activates, description, id, roleRules, forbiddenRoles, from, rule, title

### Community 145 - "Community 145"
Cohesion: 0.25
Nodes (7): branding, color, icon, description, name, runs, using

### Community 149 - "Community 149"
Cohesion: 0.25
Nodes (7): profiles, requireClassification, roles, COMPOSITION_ROOT, INBOUND_ADAPTER, roots, schemaVersion

### Community 150 - "Community 150"
Cohesion: 0.25
Nodes (7): profiles, requireClassification, roles, APPLICATION, DOMAIN, roots, schemaVersion

### Community 151 - "Community 151"
Cohesion: 0.25
Nodes (7): profiles, requireClassification, roles, COMPOSITION_ROOT, INBOUND_ADAPTER, roots, schemaVersion

### Community 152 - "Community 152"
Cohesion: 0.25
Nodes (7): profiles, requireClassification, roles, COMPOSITION_ROOT, INBOUND_ADAPTER, roots, schemaVersion

### Community 153 - "Community 153"
Cohesion: 0.25
Nodes (8): NPM_DONE, PYPI_DONE, VERSION, verify-published, env, if, needs, runs-on

### Community 154 - "Community 154"
Cohesion: 0.43
Nodes (5): generate(), load(), main(), matrix(), profile_closure()

### Community 155 - "Community 155"
Cohesion: 0.25
Nodes (7): compilerOptions, module, moduleResolution, noEmit, strict, target, include

### Community 156 - "Community 156"
Cohesion: 0.25
Nodes (7): compilerOptions, module, moduleResolution, noEmit, strict, target, include

### Community 157 - "Community 157"
Cohesion: 0.25
Nodes (7): contexts, exposedPackages, id, packages, profiles, roots, schemaVersion

### Community 158 - "Community 158"
Cohesion: 0.25
Nodes (7): compilerOptions, module, moduleResolution, noEmit, strict, target, include

### Community 159 - "Community 159"
Cohesion: 0.25
Nodes (7): language, profiles, roles, APPLICATION, INBOUND_ADAPTER, roots, schemaVersion

### Community 160 - "Community 160"
Cohesion: 0.25
Nodes (7): language, profiles, roles, APPLICATION, INBOUND_ADAPTER, roots, schemaVersion

### Community 161 - "Community 161"
Cohesion: 0.25
Nodes (7): language, profiles, roles, DOMAIN, roots, schemaVersion, unknownKey

### Community 162 - "Community 162"
Cohesion: 0.25
Nodes (7): language, profiles, roles, DOMAIN, roots, schemaVersion, unknownKey

### Community 163 - "Community 163"
Cohesion: 0.25
Nodes (7): language, profiles, requireClassification, roles, DOMAIN, roots, schemaVersion

### Community 164 - "Community 164"
Cohesion: 0.25
Nodes (7): language, profiles, requireClassification, roles, DOMAIN, roots, schemaVersion

### Community 165 - "Community 165"
Cohesion: 0.29
Nodes (7): steps, id, if, run, shell, uses, working-directory

### Community 166 - "Community 166"
Cohesion: 0.52
Nodes (6): endgroup(), finish(), group(), is_archguard(), retry(), run.sh script

### Community 171 - "Community 171"
Cohesion: 0.29
Nodes (6): profiles, requireClassification, roles, INBOUND_ADAPTER, roots, schemaVersion

### Community 172 - "Community 172"
Cohesion: 0.29
Nodes (6): profiles, requireClassification, roles, INBOUND_ADAPTER, roots, schemaVersion

### Community 173 - "Community 173"
Cohesion: 0.33
Nodes (3): leaves_site(), main(), rewrite()

### Community 174 - "Community 174"
Cohesion: 0.29
Nodes (6): description, files, keywords, license, name, version

### Community 175 - "Community 175"
Cohesion: 0.48
Nodes (4): declared(), main(), pom_version(), search()

### Community 176 - "Community 176"
Cohesion: 0.29
Nodes (6): profiles, roles, APPLICATION, INBOUND_ADAPTER, roots, schemaVersion

### Community 177 - "Community 177"
Cohesion: 0.29
Nodes (6): profiles, roles, DOMAIN, roots, schemaVersion, unknownKey

### Community 178 - "Community 178"
Cohesion: 0.29
Nodes (6): profiles, requireClassification, roles, DOMAIN, roots, schemaVersion

### Community 179 - "Community 179"
Cohesion: 0.29
Nodes (6): analysisProcessSeconds, classes, compileSeconds, dependencies, maxRssKiB, note

### Community 190 - "Community 190"
Cohesion: 0.33
Nodes (5): activates, description, id, includes, title

### Community 191 - "Community 191"
Cohesion: 0.33
Nodes (5): activates, description, id, includes, title

### Community 197 - "Community 197"
Cohesion: 0.40
Nodes (5): example:company-rules, io.archguard:archguard-api, io.archguard:archguard-cli, io.archguard:archguard-core, io.archguard:archguard-maven-plugin

### Community 199 - "Community 199"
Cohesion: 0.40
Nodes (4): infrastructure, profiles, rules, specVersion

### Community 200 - "Community 200"
Cohesion: 0.40
Nodes (4): description, entries, language, matching

### Community 201 - "Community 201"
Cohesion: 0.40
Nodes (4): description, entries, language, matching

### Community 202 - "Community 202"
Cohesion: 0.40
Nodes (4): description, entries, language, matching

### Community 203 - "Community 203"
Cohesion: 0.40
Nodes (4): activates, description, id, title

### Community 204 - "Community 204"
Cohesion: 0.50
Nodes (4): inputs, suppressions, default, description

### Community 205 - "Community 205"
Cohesion: 0.83
Nodes (3): extend_policy(), preset_case(), local_e2e.sh script

### Community 216 - "Community 216"
Cohesion: 0.50
Nodes (4): contact_links, about, name, url

### Community 217 - "Community 217"
Cohesion: 0.50
Nodes (3): name, private, type

### Community 220 - "Community 220"
Cohesion: 0.67
Nodes (3): default, description, annotations

### Community 221 - "Community 221"
Cohesion: 0.67
Nodes (3): default, description, archguard-version

### Community 222 - "Community 222"
Cohesion: 0.67
Nodes (3): default, description, artifact-name

### Community 223 - "Community 223"
Cohesion: 0.67
Nodes (3): default, description, baseline

### Community 224 - "Community 224"
Cohesion: 0.67
Nodes (3): default, description, changed-files-only

### Community 225 - "Community 225"
Cohesion: 0.67
Nodes (3): default, description, cli-command

### Community 226 - "Community 226"
Cohesion: 0.67
Nodes (3): default, description, cli-jar

### Community 227 - "Community 227"
Cohesion: 0.67
Nodes (3): default, description, config

### Community 228 - "Community 228"
Cohesion: 0.67
Nodes (3): default, description, extensions

### Community 229 - "Community 229"
Cohesion: 0.67
Nodes (3): default, description, fail-on

### Community 230 - "Community 230"
Cohesion: 0.67
Nodes (3): java-version, default, description

### Community 231 - "Community 231"
Cohesion: 0.67
Nodes (3): language, default, description

### Community 232 - "Community 232"
Cohesion: 0.67
Nodes (3): node-version, default, description

### Community 233 - "Community 233"
Cohesion: 0.67
Nodes (3): python-version, default, description

### Community 234 - "Community 234"
Cohesion: 0.67
Nodes (3): setup-java, default, description

### Community 235 - "Community 235"
Cohesion: 0.67
Nodes (3): setup-node, default, description

### Community 236 - "Community 236"
Cohesion: 0.67
Nodes (3): setup-python, default, description

### Community 237 - "Community 237"
Cohesion: 0.67
Nodes (3): upload-artifact, default, description

### Community 238 - "Community 238"
Cohesion: 0.67
Nodes (3): upload-sarif, default, description

### Community 239 - "Community 239"
Cohesion: 0.67
Nodes (3): working-directory, default, description

### Community 240 - "Community 240"
Cohesion: 0.67
Nodes (3): status, description, value

## Knowledge Gaps
- **37 isolated node(s):** `APPLICATION`, `COMPOSITION_ROOT`, `DOMAIN`, `INBOUND_ADAPTER`, `INBOUND_PORT` (+32 more)
  These have ≤1 connection - possible missing edges. (Counts symbols only; 1679 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **105 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `EngineTest` connect `Community 22` to `Community 71`, `Community 39`, `Community 43`, `Community 13`, `Community 115`, `Community 183`?**
  _High betweenness centrality (0.010) - this node is a cross-community bridge._
- **What connects `APPLICATION`, `COMPOSITION_ROOT`, `DOMAIN` to the rest of the system?**
  _37 weakly-connected nodes found - possible missing edges._
- **Should `Community 0` be split into smaller, more focused modules?**
  _Cohesion score 0.07868852459016394 - nodes in this community are weakly interconnected._
- **Why does `Policies` connect `Community 0` to `Community 57`, `Community 13`?**
  _High betweenness centrality (0.009) - this node is a cross-community bridge._
- **Should `Community 1` be split into smaller, more focused modules?**
  _Cohesion score 0.07922077922077922 - nodes in this community are weakly interconnected._
- **Why does `SpecCatalog` connect `Community 44` to `Community 4`, `Community 72`, `Community 13`, `Community 184`, `Community 57`?**
  _High betweenness centrality (0.007) - this node is a cross-community bridge._
- **Should `Community 2` be split into smaller, more focused modules?**
  _Cohesion score 0.0899854862119013 - nodes in this community are weakly interconnected._