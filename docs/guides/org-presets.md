# Organisation presets

A preset is a shared base policy that every service extends. It lets an organisation set one architecture standard, such as locked rule severities, mandatory classification and company-wide constraints, while each team keeps its own role mapping.

```yaml
# a service's architecture.yml
schemaVersion: 2
language: python
extends: ["org:acme/base@1.0.0"]
roots: ["orders.**"]
roles:
  ...
```

## Write a preset

A preset is a policy file with `kind: preset`. It may omit `language`, so the same file serves Java, TypeScript and Python services:

```yaml
schemaVersion: 2
kind: preset
requireClassification: true
failOn: ERROR
newOnly: true
rules:
  HEX-001: { severity: ERROR, locked: true }
  HEX-002: { severity: ERROR, locked: true }
  CYCLE-001: { enabled: true, severity: WARNING }
```

Rules marked `locked: true` cannot be changed by a service; trying to fails analysis. Merge semantics: maps merge by key (`roles`, `rules`), lists of objects merge by `id` (`contexts`, `constraints`), other values are replaced by the service's file. Details are in [Policy configuration](../CONFIGURATION.md).

## Publish it

One set of YAML files is published three ways, so every language resolves `org:<org>/<name>@<version>` to the same file. [`presets/acme`](https://github.com/dmishra2022/archguard/blob/main/presets/acme/README.md) is a complete template with all three packaging files:

| Language | Package | File location inside the package |
|---|---|---|
| Java | Maven artifact, for example `com.acme.architecture:archguard-presets` | `META-INF/archguard/presets/<org>/<name>/<version>.yml` |
| TypeScript | npm package `@<org>/archguard-presets` | `presets/<name>/<version>.yml` |
| Python | Python package `<org>-archguard-presets` (import name `<org>_archguard_presets`) | `presets/<name>/<version>.yml` |

Publish to your internal registries. Never overwrite a released version; publish a new one.

## Consume it

| Language | Install | GitHub Action input |
|---|---|---|
| Java (Maven plugin) | Add the preset artifact as a `<dependency>` of `archguard-maven-plugin` | — |
| Java (CLI) | `--extension acme-archguard-presets-1.0.0.jar` | `extensions: path/to/presets.jar` |
| TypeScript | `npm install --save-dev @acme/archguard-presets@1.0.0` | none; run `npm ci` before the action |
| Python | add `acme-archguard-presets==1.0.0` to the dev dependencies | `extensions: acme-archguard-presets==1.0.0` |

A missing package or version is an analysis error (exit 2), never a silent fallback.

## Upgrade it

The policy hash covers the merged policy, so a new preset version invalidates baselines. Upgrade like any dependency: bump the version in a pull request, regenerate the baseline in the same pull request, and have architecture owners review both.
