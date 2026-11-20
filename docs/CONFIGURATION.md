# Configuration

`architecture.yml` uses schemaVersion 1 (original format) or schemaVersion 2 (the language-neutral ArchGuard Spec 2.0 format, see [spec/README.md](../spec/README.md)). The editor schema `docs/architecture.schema.json` is a copy of [spec/schemas/policy.schema.json](../spec/schemas/policy.schema.json) and covers both versions; the runtime also performs semantic checks that JSON Schema cannot express. Keys and enum values are case-sensitive. Unknown properties, duplicate YAML keys, trailing YAML documents, explicit null values, unknown rule IDs, duplicate IDs, conflicting mappings and invalid selectors fail analysis.

## schemaVersion 2

schemaVersion 2 is a superset of version 1. Existing version 1 files keep working unchanged, keep their policy hash, and therefore keep their baselines valid. Version 2 adds:

| Key | Meaning |
|---|---|
| `language: java \| typescript \| python` | Required. Each analyzer rejects a policy written for another language. |
| `kind: project \| preset` | `preset` files are reusable parents for `extends` and cannot be analyzed directly. |
| `extends: [...]` | Parent presets, applied in order before the local file (see below). |
| `profiles` | Any spec profile: `hexagonal`, `ddd`, `layered`, `clean`, `modular-monolith`. |
| `rules.<ID>.locked` | In a preset: children cannot change this rule's settings. |
| `sourceRoots`, `typeOnlyImports`, `unresolvedImports` | Used by the Python and TypeScript analyzers; ignored by Java. See the [TypeScript](../typescript/archguard-ts/README.md) and [Python](../python/archguard-py/README.md) analyzer READMEs. |

Selectors depend on the language: Java selectors match packages, TypeScript selectors match directories relative to the project root, and Python selectors match dotted module names under the source root. The rest of this page uses Java examples; apart from the three keys above, every key works the same in all three languages.

`exposedPackages: []` is valid: the context exposes nothing, so any import of it from another context is a DDD-001 finding. Code outside every context is not checked by the DDD rules.

Selectors accept the neutral glob syntax in both versions: `com.acme.**` equals `com.acme..`, `**.domain.**` equals `..domain..`, `*` is one segment. Prefer globs in policies shared with other languages. See [spec/SELECTORS.md](../spec/SELECTORS.md).

```yaml
schemaVersion: 2
language: java
extends: ["org:acme/base@1.0.0"]
roots: ["com.acme.**"]
profiles: [hexagonal, ddd]
roles:
  DOMAIN: ["com.acme.orders.domain.**"]
  APPLICATION: ["com.acme.orders.application.**"]
  OUTBOUND_PORT: ["com.acme.orders.port.**"]
  OUTBOUND_ADAPTER: ["com.acme.orders.adapter.**"]
```

### Profiles

Profiles are data in [spec/profiles](../spec/profiles). A profile sets which rules are on by default and contributes a role matrix. All matrices are always loaded, so `rules.<ID>.enabled: true` turns on a rule even without its profile.

| Profile | Activates | Summary |
|---|---|---|
| hexagonal | HEX-001..004 | Core never depends on adapters, wiring or infrastructure; adapters do not call each other across directions |
| ddd | DDD-001, DDD-002 | Contexts use each other's exposed packages only; no context cycles |
| layered | LAYER-001, LAYER-002 | Dependencies point downward; presentation does not bypass the business layer; business may use persistence |
| clean | hexagonal + CYCLE-001 | Hexagonal dependency rule plus no package cycles |
| modular-monolith | ddd + CYCLE-001 | Modules use public APIs only, no module or package cycles |

### extends and presets

```yaml
# acme-base.yml (published by the architecture team)
schemaVersion: 2
kind: preset
language: java
profiles: [hexagonal]
rules:
  HEX-001: { severity: ERROR, locked: true }
constraints:
  - id: ACME-001
    from: ["**.domain.**"]
    forbidden: ["com.vendor.**"]
    rationale: "Vendor SDKs stay in adapters."
    remediation: "Wrap the SDK in an outbound adapter behind a core-owned port."
```

References: `./file.yml` or `../file.yml` (relative to the referencing file), `/absolute.yml`, `classpath:path/in/jar.yml`, or `org:<org>/<name>@<version>`, which loads `META-INF/archguard/presets/<org>/<name>/<version>.yml` from the analyzer classpath. For Maven, add the preset artifact as a **plugin dependency**, exactly like a custom rule pack.

Merge rules: parents are applied in order, then the local file. Maps merge by key (`roles`, `rules`), lists of objects merge by `id` (`contexts`, `constraints`), and other lists and scalars are replaced. A parent rule marked `locked: true` cannot be changed by any child. Extended files must be `schemaVersion: 2` with `kind: preset`. Cycles, missing presets and language mismatches fail analysis. The policy hash covers the fully merged policy, so changing a preset version requires a reviewed baseline regeneration.

## schemaVersion 1

Package selectors use ArchUnit's package matcher: `example.orders..` includes the package and descendants; `..domain..` matches a domain segment; `*` matches a segment. Selectors apply to **package names**, not filesystem paths or class simple names. Use narrow roots. Dependency targets outside roots remain visible to boundary rules; roots control which origins are evaluated.

```yaml
schemaVersion: 1
roots: ["com.acme.."]
profiles: [hexagonal, ddd]
roles:
  DOMAIN: ["com.acme.orders.domain.."]
  APPLICATION: ["com.acme.orders.application.."]
  INBOUND_PORT: ["com.acme.orders.port.inbound.."]
  OUTBOUND_PORT: ["com.acme.orders.port.outbound.."]
  INBOUND_ADAPTER: ["com.acme.orders.adapter.inbound.."]
  OUTBOUND_ADAPTER: ["com.acme.orders.adapter.outbound.."]
  COMPOSITION_ROOT: ["com.acme.orders.bootstrap.."]
contexts:
  - id: orders
    packages: ["com.acme.orders.."]
    exposedPackages: ["com.acme.orders.api.."]
  - id: billing
    packages: ["com.acme.billing.."]
    exposedPackages: ["com.acme.billing.api.."]
constraints:
  - id: COMPANY-DB-001
    from: ["com.acme.orders.domain.."]
    forbidden: ["com.vendor.database.."]
    severity: ERROR
    rationale: "Domain code must not depend on the vendor database API."
    remediation: "Move this integration into an outbound adapter behind a core-owned port."
rules:
  CYCLE-001:
    enabled: true
    severity: WARNING
  MODEL-002:
    enabled: true
requireClassification: true
allowEmptySelectors: false
allowEmptyAnalysis: false
failOn: ERROR
newOnly: false
```

All mapped roles must have at least one matched application class unless `allowEmptySelectors` is explicitly enabled. Context package selectors and custom constraint source selectors are also checked. A selector list with several alternatives needs at least one match, not a match for every alternative. No application classes is an error unless `allowEmptyAnalysis` is explicitly enabled. Do not enable these exceptions simply to make CI green.

Configuration does not force all seven roles to exist. An application can declare only the roles it uses. If a root spans several contexts, map roles across all those contexts or leave `requireClassification` false intentionally. Annotation/suffix discovery does not override explicit role mapping.

## Maven goals

| Goal | Scope | Policy violations fail build | Usage |
|---|---|---|---|
| check | Current non-POM module | Yes | Default phase verify, or direct invocation after compile |
| analyze | Current non-POM module | No | Reports only; analysis errors still fail |
| check-reactor | Selected reactor | Yes | Explicit goal after compilation, never lifecycle-bound |
| baseline | Selected reactor | No | Explicit approved-debt capture, never lifecycle-bound |

Use fully qualified coordinates if your Maven plugin groups do not include `io.archguard`.

## Maven properties

| Property | Default | Purpose |
|---|---|---|
| archguard.config | `${maven.multiModuleProjectDirectory}/architecture.yml` | Policy file |
| archguard.outputDirectory | `${project.build.directory}/archguard` | Report directory |
| archguard.baseline | Not set | Existing reviewed baseline JSON |
| archguard.suppressions | Not set | Reviewed suppression JSON |
| archguard.skip | false | Explicit skip; logs that no verification occurred |
| archguard.allowPartialReactor | false | Acknowledge limited reactor scope |
| archguard.baselineOutput | Root `architecture-baseline.json` | Baseline capture destination |
| archguard.overwriteBaseline | false | Explicit reviewed baseline replacement |

Plugin configuration also accepts `<excludedModules><excludedModule>group:artifact</excludedModule></excludedModules>`. Exclusions are recorded in diagnostics. Do not exclude a module and claim full-reactor coverage. Each module needs its own report directory; do not configure parallel module executions to share one directory.

## Adoption and baselines

1. Run `analyze` on modules to inspect results, or run `check-reactor` and inspect its reports even when it fails.
2. Review roles, contexts and false positives.
3. Configure `newOnly: true`, then explicitly capture a baseline:

```bash
mvn compile io.archguard:archguard-maven-plugin:0.1.0:baseline
mvn compile io.archguard:archguard-maven-plugin:0.1.0:check-reactor \
  -Darchguard.baseline=architecture-baseline.json
```

INFO classification findings are not baseline debt. Baseline files bind to engine version and canonical policy hash. Changing policy or engine requires deliberate review and regeneration. Line movement does not change a fingerprint; symbol/semantic dependency changes normally do. Baselines never grow during checks. Resolved entries are reported but not removed automatically. `newOnly: false` intentionally gates existing debt too.

Custom rule implementation changes must be versioned and reviewed with the baseline; this release does not fingerprint rule-pack binary content. Pin rule-pack versions and do not overwrite released artifacts.

## Suppressions

```json
{
  "schemaVersion": 1,
  "entries": [
    {
      "fingerprint": "COPY_THE_64_CHARACTER_FINDING_FINGERPRINT",
      "owner": "orders-team",
      "reason": "Approved migration tracked in ARCH-42",
      "expires": "2026-12-31"
    }
  ]
}
```

The placeholder above is not valid until replaced with an actual fingerprint. Missing ownership/reason, duplicate suppressions and expired dates fail analysis. Dates are UTC calendar dates, valid through the stated day. Suppressed findings remain visible. Suppression files are never automatically updated.

## Offline CI

Warm your organization's Maven repository with the exact plugin, rule packs, project dependencies and build plugins required for the chosen lifecycle. Then use `mvn -o`. The analyzer itself never contacts a service. A ZIP of this source repository is not a bundled offline Maven repository.
