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
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0        # precise merge base for changed-files-only
      - uses: dmishra2022/archguard/action@main   # pin a release tag once published
        with:
          working-directory: .
          # baseline: architecture-baseline.json   (used automatically when present)
          # changed-files-only: "true"             (PRs: gate only files the PR touches)
          # upload-sarif: "false"                  (private repos without code scanning)
```

What the action does:
1. It detects the language from the build file and installs JDK 17.
2. It gets the analyzer from Maven Central, or builds it from the action's source if that version is not published.
3. It compiles the project and runs `mvn archguard:classpath` (or the Gradle task from [CLI.md](CLI.md)).
4. It runs `archguard check` with the policy, the baseline and suppressions (when present), and the `fail-on` override.
5. It writes a job summary and an annotation for each NEW finding. Annotations work without code scanning.
6. It uploads SARIF to code scanning (`upload-sarif`) and the report directory as an artifact (`upload-artifact`, `artifact-name`).
7. It fails the job with exit 1 (violation) or 2 (analysis error).

Outputs: `exit-code`, `status` (`passed`, `failed`, `error`), `new-findings`, `report-dir`, `sarif`. If you want to post-process before failing, use `continue-on-error: true` and read `exit-code`.

With `changed-files-only`, the whole project is still analyzed, but only findings located in files changed since the merge base are reported and gated. Run the full check on the default branch so nothing escapes.

## Any other CI: plain shell

```bash
mvn -B -q -DskipTests compile io.archguard:archguard-maven-plugin:0.1.0:classpath
args=(); for f in $(find . -path '*/target/archguard.classpath'); do args+=(--classpath-file "$f"); done
java -jar archguard-cli-0.1.0.jar check "${args[@]}" --format json,sarif,html,console
status=$?   # 0 pass, 1 violation, 2 analysis error
exit $status
```

Get the jar from Maven Central (`io.archguard:archguard-cli`) or build it with `mvn -pl archguard-cli -am package`.

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
