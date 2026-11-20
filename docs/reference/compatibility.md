# Compatibility and versioning

## Supported environments

| Analyzer | Package | Runtime | Tested in CI |
|---|---|---|---|
| Java | `io.archguard:archguard-maven-plugin`, `archguard-cli-<version>.jar` | JDK 17 to 27 (both to run the analyzer and for the analyzed class files); Maven 3.9; Gradle through the init script | JDK 17, 21, 25 and 27 |
| TypeScript / JavaScript | `archguard-cli` (npm) | Node.js 18 or later | Node.js 18, 20, 22 and 24 |
| Python | `archguard-cli` (PyPI) | Python 3.9 or later | Python 3.9 to 3.14 |

CI runs on Linux, and development happens on macOS. Windows is not tested yet. The GitHub Action runs on GitHub-hosted Linux runners.

The Python analyzer parses code with the interpreter it runs on, so use a Python version that supports your project's syntax. The TypeScript analyzer bundles its own TypeScript compiler.

## Versions

ArchGuard has two version numbers:

- **The spec version** (currently 2.0.0) describes the policy format, rules, fingerprints, report formats and exit codes. It follows semantic versioning; see [spec/VERSIONING.md](../../spec/VERSIONING.md).
- **The analyzer version** (currently 0.1.0) is shared by the Java, TypeScript and Python analyzers. All three are released together with the same version number.

`archguard --version` prints both: `archguard 0.1.0 (python analyzer, spec 2.0.0)`.

### What can change between releases

| Change | Spec version | Effect on your project |
|---|---|---|
| Incompatible policy schema, fingerprint algorithm, exit codes or rule meaning | Major | New `schemaVersion`; migrate the policy and regenerate baselines |
| New rules, profiles, optional policy keys, infrastructure entries | Minor | New rules are off unless a profile you use activates them; check the changelog |
| A rule detects more or fewer cases | Minor (called out in the changelog) | May change findings; regenerate the baseline in the upgrade pull request |
| Messages, remediation text, documentation | Patch | None. Messages are not part of fingerprints |

Rule IDs are permanent and never reused.

Before 1.0.0, the analyzer versions may include changes that require baseline regeneration in any minor release. Pin exact versions (`archguard-cli==0.1.0`, `"archguard-cli": "0.1.0"`, the plugin `<version>`) and upgrade through a reviewed pull request.

## Baselines across versions

Baselines record the analyzer's engine version and the policy hash. A different analyzer version or policy is refused with an explicit error instead of being compared silently; regenerate the baseline as part of the upgrade.

## Policy schema versions

| `schemaVersion` | Languages | Status |
|---|---|---|
| 1 | Java | Original format; still accepted and keeps its policy hash |
| 2 | Java, TypeScript, Python | Current |
