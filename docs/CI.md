# ArchGuard in CI

The CI contract is generic: run `archguard check`, treat exit code **1** as a policy violation and **2** as a broken pipeline (never a pass), and publish `archguard.sarif` with whatever viewer the platform offers. Only shell commands are needed; the GitHub Action is a convenience wrapper over the same steps.

For Maven projects, the simplest gate is the plugin itself: bind the `check` goal (see the [README](../README.md)) and `mvn verify` fails on violations. Use the CLI when you want the same gate for Gradle or other builds, changed-files scoping, or the agent format.

## GitHub Actions

```yaml
permissions:
  contents: read
  security-events: write        # only for upload-sarif

jobs:
  architecture:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
        with:
          fetch-depth: 0        # precise merge base for changed-files-only
      - uses: dmishra2022/archguard/action@main   # pin a release tag once published
        with:
          working-directory: .
          # baseline: architecture-baseline.json   (used automatically when present)
          # changed-files-only: "true"             (PRs: gate only files the PR touches)
          # upload-sarif: "false"                  (private repos without code scanning)
```

The same step works for Java, TypeScript/JavaScript and Python projects. For a monorepo, add one step per project with its own `working-directory` and a unique `artifact-name`.

What the action does:
1. It picks the language: the `language` input, else the policy's `language:` key, else the build files (`pom.xml`/`build.gradle` for Java, `tsconfig.json`/`package.json` for TypeScript, `pyproject.toml`/`setup.py`/`setup.cfg` for Python).
2. It installs the runtime: JDK (`java-version`, default 17), Node.js (`node-version`, default 20) or Python (`python-version`, default `3.x`). Set `setup-java`, `setup-node` or `setup-python` to `false` if the job already did.
3. It gets the analyzer:
   - Java: from Maven Central, or built from the action's source if that version is not published. It then compiles the project and runs `mvn archguard:classpath` (Gradle projects get the same through the bundled init script, with no build changes).
   - TypeScript: the project's own `archguard-cli` devDependency when `node_modules` is installed, otherwise built from the action's source. No project build or `npm install` is needed. Run code generators (Prisma, GraphQL codegen) in an earlier step.
   - Python: an `archguard` already on `PATH` (for example the project's dev environment), otherwise installed from the action's source into a private virtual environment. The project's dependencies are not needed; the Python version must be able to parse the project's syntax.
   - `extensions` adds organisation presets and rule packs, one per line. Java entries are jar paths passed as `--extension`. Python entries are pip requirements installed next to the analyzer, for example `acme-archguard-presets==1.0.0`. TypeScript resolves presets from the project's `node_modules`, so run `npm ci` before the action.
   - `cli-command` overrides all of this, for example `npx archguard` or `.venv/bin/archguard`. The action checks with `--version` that the command is the ArchGuard analyzer for the language before trusting its exit code.
4. It runs `archguard check` with the policy, the baseline and suppressions (when present), and the `fail-on` override.
5. It writes a job summary and an annotation for each NEW finding, with repository-relative paths. Annotations work without code scanning.
6. It uploads SARIF to code scanning (`upload-sarif`) and the report directory as an artifact (`upload-artifact`, `artifact-name`). Reports are in `target/archguard` (Maven), `build/archguard` (Gradle) or `reports/archguard` (TypeScript, Python) under the working directory.
7. It fails the job with exit 1 (violation) or 2 (analysis error).

The TypeScript and Python analyzers are distributed as `archguard-cli` on npm and PyPI. The unrelated packages `@archguard/cli` (npm) and `archguard` (PyPI) belong to other projects. The action never installs either of them.

Outputs: `exit-code`, `status` (`passed`, `failed`, `error`), `new-findings`, `report-dir`, `sarif`. If you want to post-process before failing, use `continue-on-error: true` and read `exit-code`.

To try the action's scripts locally without GitHub, run `action/tests/local_e2e.sh`. It runs the clean and violating examples for every language plus the pull-request scope, in a scratch copy of the repository.

With `changed-files-only`, the whole project is still analyzed, but only findings located in files changed since the merge base are reported and gated. Run the full check on the default branch so nothing escapes.

## Any other CI: plain shell

Java (Maven):

```bash
mvn -B -q -DskipTests compile io.archguard:archguard-maven-plugin:0.1.0:classpath
args=(); for f in $(find . -path '*/target/archguard.classpath'); do args+=(--classpath-file "$f"); done
java -jar archguard-cli-0.1.0.jar check "${args[@]}" --format json,sarif,html,console
status=$?   # 0 pass, 1 violation, 2 analysis error
exit $status
```

Get the jar from Maven Central (`io.archguard:archguard-cli`) or build it with `mvn -pl archguard-cli -am package`.

TypeScript (with `archguard-cli` in `devDependencies`):

```bash
npm ci
npx archguard check --format json,sarif,html,console   # reports in reports/archguard
```

Python (with `archguard-cli` in the dev dependencies, or installed on its own):

```bash
pip install archguard-cli==0.1.0
archguard check --format json,sarif,html,console        # reports in reports/archguard
```

The GitLab, Jenkins and Azure examples below use Java paths. For TypeScript and Python, use a Node or Python image and publish `reports/archguard/` instead of `target/archguard/`.

### GitLab CI

```yaml
architecture:
  image: maven:3.9-eclipse-temurin-17
  script:
    - ./ci/archguard.sh          # the shell snippet above
  artifacts:
    when: always
    paths: [target/archguard/]
    # GitLab Ultimate can ingest SARIF through a converter; otherwise publish index.html
```

### Jenkins (declarative)

```groovy
stage('Architecture') {
  steps {
    sh './ci/archguard.sh'
  }
  post {
    always {
      archiveArtifacts artifacts: 'target/archguard/**', allowEmptyArchive: true
      recordIssues tool: sarif(pattern: 'target/archguard/archguard.sarif')   // Warnings Next Generation plugin
    }
  }
}
```

### Azure Pipelines

```yaml
- script: ./ci/archguard.sh
  displayName: ArchGuard
- task: PublishBuildArtifacts@1
  condition: always()
  inputs:
    PathtoPublish: target/archguard
    ArtifactName: CodeAnalysisLogs     # the SARIF SAST Scans Tab extension reads this artifact name
```

## Baselines and gating

- Adopting on an existing codebase: run `archguard baseline`, review and commit `architecture-baseline.json`, and set `newOnly: true` in the policy. Legacy findings show as baselined; only new ones fail.
- The baseline is bound to the policy hash. Changing the policy requires regenerating the baseline (`--overwrite-baseline`) in a reviewed PR.
- Protect `architecture.yml`, `architecture-baseline.json` and `architecture-suppressions.json` with CODEOWNERS so gate changes need architecture-owner review.
