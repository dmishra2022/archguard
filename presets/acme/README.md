# Acme ArchGuard presets (template for an organisation preset)

This directory is a complete, publishable organisation preset for the fictional organisation `acme`. Copy it to start your own. One set of YAML files under `presets/` is published three ways, so Java, TypeScript and Python projects resolve the same `org:acme/<name>@<version>` reference to the same file:

| Ecosystem | Artifact | Where the analyzer looks |
|---|---|---|
| Maven | `com.acme.architecture:archguard-presets` (`pom.xml`) | `META-INF/archguard/presets/acme/<name>/<version>.yml` on the analyzer classpath |
| npm | `@acme/archguard-presets` (`package.json`) | `node_modules/@acme/archguard-presets/presets/<name>/<version>.yml`, resolved from the project root |
| PyPI | `acme-archguard-presets` (`pyproject.toml`) | the importable package `acme_archguard_presets/presets/<name>/<version>.yml` |

`presets/base/1.0.0.yml` is a language-neutral baseline. It requires full classification, gates new findings, and locks the severity of the core boundary rules. Projects extend it and add their own `language`, `roots`, `roles` and `contexts`.

## Make it yours

1. Copy `presets/acme` into a repository owned by the architecture team, for example `architecture-presets`.
2. Replace `acme` with your organisation id (letters, digits, `.`, `_`, `-`) in four places:
   - the `pom.xml` `groupId` and the resource `targetPath`;
   - the npm `name` (`@<org>/archguard-presets`);
   - the PyPI `name` and the package name (`<org>_archguard_presets`, with `-` and `.` replaced by `_`) in `pyproject.toml`.
3. Edit or add presets under `presets/<name>/<version>.yml`. Every file needs `schemaVersion: 2` and `kind: preset`. Leave `language` out to share a preset across languages, or set it for a language-specific preset (for example `presets/java-spring/1.0.0.yml` with Java selectors in `constraints`).
4. Never change a published version. Add `presets/base/1.1.0.yml` and bump the package versions. A project's policy hash covers its `extends` references, so moving to a new preset version is a reviewed pull request that regenerates the project's baseline.

## Publish

```bash
mvn -B deploy                                  # to the repository in your distributionManagement or settings.xml
npm publish --registry https://npm.acme.internal/
python -m build && twine upload --repository-url https://pypi.acme.internal/ dist/*
```

The release workflow in this repository (`.github/workflows/release.yml`) shows the same steps, gated on registry secrets. Publish the scoped npm package and the PyPI package to your internal registries. If a registry falls back to the public one, reserve the names there too, so nobody else can publish them (dependency confusion).

## Consume

```yaml
# architecture.yml in a project
schemaVersion: 2
extends: ["org:acme/base@1.0.0"]
language: python          # or java / typescript
roots: ["orders.**"]
roles: { ... }
```

- **Java (Maven plugin):** add `com.acme.architecture:archguard-presets:1.0.0` as a dependency of `archguard-maven-plugin`.
- **Java (CLI and the GitHub Action):** pass the jar with `--extension archguard-presets-1.0.0.jar`.
- **TypeScript:** `npm install --save-dev @acme/archguard-presets@1.0.0`.
- **Python:** add `acme-archguard-presets==1.0.0` to the dev dependencies next to `archguard-cli`.

`python3 scripts/preset_check.py` (repository root) packages this directory for all three ecosystems and checks the preset in each analyzer. It confirms that the preset resolves and its settings take effect, that locked rules cannot be overridden, and that a missing package or version fails with exit 2.
