# Onboarding a project to ArchGuard

This guide takes a Java, TypeScript/JavaScript or Python project from nothing to an enforced architecture gate. Plan for about half a day. ArchGuard analyzes the code itself (bytecode for Java, source for TypeScript and Python), so it works the same whether people, coding agents or both write the code. The agent skill in step 8 is optional.

## What the project gets

| Item | Where | Owner |
|---|---|---|
| Policy | `architecture.yml` at the project root | Architecture owners (CODEOWNERS) |
| Analyzer | Maven plugin or CLI jar (Java), `archguard-cli` devDependency (TypeScript), `archguard-cli` dev dependency (Python) | Team |
| Baseline of existing debt | `architecture-baseline.json` | Architecture owners |
| Suppressions (optional, owned, reasoned, expiring) | `architecture-suppressions.json` | Architecture owners |
| CI gate | GitHub Action, or the CLI in any other CI | Team |
| Agent skill (optional) | `.cursor/skills/archguard/` | Team |

The analyzer exit codes are the same everywhere: `0` pass, `1` policy violation, `2` the analysis could not run (never a pass), `64` usage error. Reports go to `target/archguard/` (Maven), `build/archguard/` (Gradle) or `reports/archguard/` (TypeScript, Python): `archguard.json`, `archguard.sarif` and `index.html`.

## 1. Install the analyzer

**Java (Maven).** Add the plugin to the root `pom.xml`. `check` binds to `verify`:

```xml
<plugin>
  <groupId>io.archguard</groupId>
  <artifactId>archguard-maven-plugin</artifactId>
  <version>0.1.0</version>
  <executions>
    <execution><goals><goal>check</goal></goals></execution>
  </executions>
</plugin>
```

For multi-module builds, run `mvn -B compile io.archguard:archguard-maven-plugin:0.1.0:check-reactor` from the reactor root instead (see the [README](../README.md#multi-module-ci)). Gradle and other builds use the CLI jar with the bundled init script; see [CLI.md](CLI.md).

**TypeScript / JavaScript** (Node.js 18 or later):

```bash
npm install --save-dev archguard-cli
npm pkg set scripts.arch:check="archguard check"
```

**Python** (3.9 or later; use a Python version that can parse your code):

```bash
pip install archguard-cli          # or: uv add --dev archguard-cli / poetry add --group dev archguard-cli
```

The npm and PyPI packages are named `archguard-cli`. The packages called `@archguard/cli` (npm) and `archguard` (PyPI) are unrelated projects; do not install them. If your organisation mirrors packages internally, install from the internal registry.

## 2. Write the policy

Copy the template for your language to `architecture.yml` at the project root:

- [`skills/archguard/templates/architecture.java.yml`](../skills/archguard/templates/architecture.java.yml)
- [`skills/archguard/templates/architecture.typescript.yml`](../skills/archguard/templates/architecture.typescript.yml)
- [`skills/archguard/templates/architecture.python.yml`](../skills/archguard/templates/architecture.python.yml)

Then fill it in:

1. **`extends`**: if your organisation publishes a preset, extend it (`extends: ["org:acme/base@1.0.0"]`) and install its package next to the analyzer (see [Organisation presets](#organisation-presets)). Otherwise delete the line.
2. **`roots`**: what to analyze. Java uses packages (`com.acme.orders.**`), TypeScript uses directories relative to the project root (`src/**`), and Python uses dotted module names under the source root (`orders.**`).
3. **`profiles`**: `hexagonal`, `clean`, `layered`, `ddd` or `modular-monolith`. Combine an architecture style with `ddd` when you have bounded contexts. [RULES.md](RULES.md) lists what each profile enforces.
4. **`roles`**: map every package or directory to one role: `DOMAIN`, `APPLICATION`, `INBOUND_PORT`, `OUTBOUND_PORT`, `INBOUND_ADAPTER`, `OUTBOUND_ADAPTER` or `COMPOSITION_ROOT`. The placement guides show the usual mapping per framework: [Java](../skills/archguard/reference/java-placement.md), [TypeScript](../skills/archguard/reference/typescript-placement.md), [Python](../skills/archguard/reference/python-placement.md). A selector with `**` covers everything below it. A selector without `**` covers exactly that package, directory or module, which is how you classify a package's own `__init__.py`, an `index.ts`, or a `main` module.
5. **`contexts`** (ddd, modular-monolith): each context's `packages` and the `exposedPackages` other contexts may use.
6. **`constraints`** (optional): project-specific forbidden dependencies, for example "views must not import models" ([CONFIGURATION.md](CONFIGURATION.md)).

Check the file before analyzing:

```bash
archguard validate                 # Python;  TypeScript: npx archguard validate
java -jar archguard-cli-0.1.0.jar validate --config architecture.yml     # Java
```

Every key is validated: typos, unknown rule IDs and invalid selectors are errors, not silently ignored.

## 3. Report-only run

Run the analysis without failing the build and open `index.html`:

```bash
mvn compile io.archguard:archguard-maven-plugin:0.1.0:analyze      # Java (per module)
npx archguard analyze                                                # TypeScript
archguard analyze                                                    # Python
```

Iterate on the policy until the findings make sense:

- **MODEL-001 (unclassified)**: a unit matched no role. Add a selector for it, or narrow `roots` if it should not be analyzed. The report's diagnostics line "Unclassified application modules: N / M" ("classes" for Java) should reach 0.
- **Exit 2**: the analysis could not run. Read the error. Common causes are a selector that matches nothing (`allowEmptySelectors` is off on purpose), a Python file the interpreter cannot parse, an unresolved project import (run code generators first, or set `unresolvedImports: warn` while you investigate), or a missing preset package.
- **Findings that look wrong**: check the role mapping first. Most false positives are a package or directory in the wrong role. If the analyzer really is wrong, open an issue with the evidence line from the report.

## 4. Capture existing debt

Once the remaining findings are real, record them so that only new violations fail:

```bash
mvn compile io.archguard:archguard-maven-plugin:0.1.0:baseline     # Java
npx archguard baseline                                              # TypeScript
archguard baseline                                                  # Python
```

Set `newOnly: true` in the policy (the templates already do), review `architecture-baseline.json`, and commit both. The baseline is bound to the policy hash: changing the policy or upgrading a preset means regenerating it (`--overwrite-baseline`, or `-Darchguard.overwriteBaseline=true` for Maven) in a reviewed pull request.

## 5. Gate locally

- **Java**: `mvn verify` runs `check`. Pass the baseline with `-Darchguard.baseline=architecture-baseline.json` or configure the property in the plugin.
- **TypeScript**: `npm run arch:check -- --baseline architecture-baseline.json`. For pre-commit with lint-staged, put this in `package.json`. Only findings in the staged files are reported, but the whole import graph is still analyzed:

  ```json
  "lint-staged": {
    "*.{ts,tsx,js,jsx}": "sh -c 'printf \"%s\\n\" \"$@\" | archguard check --format console --baseline architecture-baseline.json --changed-files -' --"
  }
  ```

- **Python**: `archguard check --baseline architecture-baseline.json`. For pre-commit:

  ```yaml
  # .pre-commit-config.yaml
  repos:
    - repo: local
      hooks:
        - id: archguard-check
          name: ArchGuard architecture check
          entry: archguard-pre-commit
          language: python
          additional_dependencies: ["archguard-cli==0.1.0"]
          args: [--baseline, architecture-baseline.json]
          files: '(\.py|architecture\.yml)$'
          require_serial: true
  ```

## 6. Add the CI gate

**GitHub Actions**: one step for any language. The language comes from the policy. A baseline and suppressions file at their default names are picked up automatically.

```yaml
name: architecture
on: [push, pull_request]
permissions:
  contents: read
  security-events: write          # only for upload-sarif
jobs:
  archguard:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
        with:
          fetch-depth: 0          # merge base for changed-files-only
      # TypeScript projects that use an org preset: install dependencies first (npm ci).
      - uses: dmishra2022/archguard/action@main   # pin a release tag once published
        with:
          working-directory: .
          # changed-files-only: "true"            # PRs: gate only findings in files the PR touches
          # extensions: |                         # org presets: Java jar paths, or Python pip requirements
          #   acme-archguard-presets==1.0.0
          # upload-sarif: "false"                 # private repositories without code scanning
```

You get a job summary, an annotation on each new finding, SARIF in code scanning, and the reports as an artifact. All inputs are described in [CI.md](CI.md). For a monorepo, add one step per project with its own `working-directory` and `artifact-name`.

**Other CI** (GitLab, Jenkins, Azure): run the same `archguard check` command. Treat exit 1 as a policy failure and exit 2 as a broken pipeline, and publish the SARIF or HTML report ([CI.md](CI.md) has snippets).

## 7. Protect the gate

Add CODEOWNERS entries so that policy, baseline and suppression changes need architecture-owner review:

```
architecture.yml               @acme/architecture
architecture-baseline.json     @acme/architecture
architecture-suppressions.json @acme/architecture
```

Turn on branch protection that requires the ArchGuard check and code-owner review.

## 8. Optional: the agent skill

For teams that use AI coding agents, install the skill so agents place code in the right role up front and run the check before handing over:

```bash
mkdir -p .cursor/skills && cp -r <archguard>/skills/archguard .cursor/skills/
```

The skill reads `language` from the policy and uses the analyzer you installed in step 1. Optionally add the Cursor `stop` hook from [`skills/archguard/hooks`](../skills/archguard/hooks/README.md), which feeds new findings back to the agent automatically. The skill tells agents never to edit the policy, the baseline or suppressions. CODEOWNERS and CI enforce that.

## Day to day

- **Writing code**: the placement guide for your language tells you where new code goes. Run `arch:check` / `archguard check` / `mvn verify` before pushing. Each finding names the rule, file, line, the dependency, and a fix.
- **Pull requests**: CI gates new findings only. Reviewers see annotations and can refer to rules by ID ("this is HEX-002"). Rule rationale and compliant examples are in [RULES.md](RULES.md).
- **A finding seems wrong, or the design needs a new dependency**: change the policy in a pull request reviewed by the architecture owners. Do not work around the analyzer with reflection, computed imports or string-based wiring.
- **Paying down debt**: fix baselined findings, then regenerate the baseline in a reviewed pull request so it only shrinks. The report shows "Baseline entries no longer observed", which is your progress.

## Organisation presets

An organisation can publish its own baseline policy, for example locked rule severities, required classification and company-wide constraints, as `org:<org>/<name>@<version>`. One set of YAML files is published as a Maven artifact, an npm package and a Python package, so every language resolves the same preset. [`presets/acme`](../presets/acme/README.md) is a complete template to copy, publish and consume.

| Language | Install the preset | Action input |
|---|---|---|
| Java (Maven plugin) | Add the preset artifact as a dependency of `archguard-maven-plugin` | `extensions: path/to/presets.jar` (CLI) |
| TypeScript | `npm install --save-dev @acme/archguard-presets@1.0.0` | none; run `npm ci` before the action |
| Python | add `acme-archguard-presets==1.0.0` to the dev dependencies | `extensions: acme-archguard-presets==1.0.0` |

Projects pin a preset version. Rules the preset marks `locked: true` cannot be changed by projects. Upgrading the preset changes the policy hash, so it is a reviewed pull request that regenerates the baseline.

## Checklist

- [ ] Analyzer installed as a dev dependency (or the Maven plugin added)
- [ ] `architecture.yml` from the template, `validate` passes
- [ ] Report-only run reviewed; MODEL-001 is 0 or deliberate
- [ ] `architecture-baseline.json` reviewed and committed, `newOnly: true`
- [ ] Local gate (build, npm script or pre-commit)
- [ ] CI gate on pull requests and the default branch
- [ ] CODEOWNERS and branch protection
- [ ] (Optional) agent skill and hook
