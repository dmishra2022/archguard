# Configuration

`architecture.yml` uses schemaVersion 1. An editor schema is available in `docs/architecture.schema.json`; the runtime also performs semantic checks that JSON Schema cannot express. Keys and enum values are case-sensitive. Unknown properties, duplicate YAML keys, trailing YAML documents, explicit null values, unknown rule IDs, duplicate IDs, conflicting mappings and invalid selectors fail analysis.

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
