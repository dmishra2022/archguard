# Changelog

All notable changes are recorded here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow [Compatibility and versioning](docs/reference/compatibility.md).

## Unreleased

## 0.1.0

First polyglot release.

### Added

- ArchGuard Spec 2.0: language-neutral policy schema (`schemaVersion: 2`), roles, data-driven profiles (`hexagonal`, `clean`, `layered`, `ddd`, `modular-monolith`), rule catalog with examples, fingerprints, exit codes and a cross-language conformance suite.
- Java: build-tool-independent CLI jar, `agent` output format, `--changed-files`, Gradle init script; the Maven plugin moved onto the spec without changing existing fingerprints.
- TypeScript/JavaScript analyzer, published as `archguard-cli` on npm.
- Python analyzer, published as `archguard-cli` on PyPI, with a pre-commit hook.
- GitHub Action for all three languages with annotations, job summary, SARIF upload and changed-files scoping.
- Agent skill with placement guides, templates and a check script for all three languages.
- Organisation presets (`extends: ["org:<org>/<name>@<version>"]`) with locked rules, and the `presets/acme` template.
- Documentation site: quickstarts, onboarding guide, adoption playbook, troubleshooting and FAQ.
