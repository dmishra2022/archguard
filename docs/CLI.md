# ArchGuard command line (Java)

For TypeScript and JavaScript projects, use [`archguard-cli`](https://github.com/dmishra2022/archguard/blob/main/typescript/archguard-ts/README.md). For Python projects, use the [`archguard-cli`](https://github.com/dmishra2022/archguard/blob/main/python/archguard-py/README.md) distribution. Both implement the same command contract.

`archguard-cli-<version>.jar` is a single runnable jar that implements the shared [command contract](https://github.com/dmishra2022/archguard/blob/main/spec/CLI.md). It works with any build tool: Maven, Gradle, Bazel or plain `javac`. It produces the same findings, fingerprints and policy hash as the Maven plugin for the same modules.

```bash
java -jar archguard-cli-0.1.0.jar check            # analyze ./target/classes with ./architecture.yml
java -jar archguard-cli-0.1.0.jar check --format agent,json,sarif,html
java -jar archguard-cli-0.1.0.jar validate --config architecture.yml
java -jar archguard-cli-0.1.0.jar rules --json
```

Build it with `mvn -pl archguard-cli -am package`. The jar is written to `archguard-cli/target/`.

## Commands and exit codes

| Command | Purpose |
|---|---|
| `check` | Analyze, apply baseline and suppressions, write reports, exit 1 on violation |
| `analyze` | Same reports, never fails on violations |
| `baseline` | Write `architecture-baseline.json` from current findings (refuses to overwrite without `--overwrite-baseline`) |
| `validate` | Validate the policy, including `extends` resolution, and print its hash |
| `rules` | List the rule catalog, including rule packs passed with `--extension` |

Exit codes: `0` pass, `1` policy violation, `2` analysis error (invalid policy, missing classes, unresolved dependencies, rule failure; never a pass), `64` usage error. On exit 2, `archguard.json`, `archguard.sarif` and `index.html` are overwritten with explicit failure reports.

## Inputs

Default values are resolved against `--project` (default: current directory). Explicit relative paths are resolved against the current directory.

| Option | Meaning |
|---|---|
| `--classes <dir>` | Compiled classes of an analyzed module (repeatable). Default `target/classes` |
| `--source-root <dir>` | Source root used to map classes to files (repeatable). Default `src/main/java` |
| `--module-id <id>` | Module id for `--classes`. Default: the project directory name |
| `--classpath <path-list>` | Dependency jars and directories, separated by the platform path separator |
| `--classpath-file <file>` | Module and dependency description (see below); repeatable for multi-module builds |
| `--extension <jar or dir>` | Rule packs (`ArchitectureRule` service implementations) and `org:` policy presets (repeatable) |

Fingerprints include the module id. To share a baseline between the Maven plugin and the CLI, use `--classpath-file` (which records Maven's `groupId:artifactId`) or pass the same id with `--module-id`.

### Classpath file

UTF-8 `key=value` lines; `#` starts a comment; relative paths resolve against the file's directory.

```text
module=com.acme:orders
classes=/repo/orders/target/classes
source=/repo/orders/src/main/java
classpath=/home/me/.m2/repository/org/slf4j/slf4j-api/2.0.17/slf4j-api-2.0.17.jar
```

`module` starts a module and must be followed by exactly one `classes` line. Class directories of analyzed modules are removed from the dependency classpath automatically.

**Maven** writes it per module:

```bash
mvn -q compile io.archguard:archguard-maven-plugin:0.1.0:classpath     # target/archguard.classpath
java -jar archguard-cli.jar check $(for f in $(find . -name archguard.classpath -path '*/target/*'); do echo --classpath-file $f; done)
```

**Gradle** needs no build changes: the init script [`skills/archguard/scripts/archguard.init.gradle`](https://github.com/dmishra2022/archguard/blob/main/skills/archguard/scripts/archguard.init.gradle) adds an `archguardClasspath` task to every Java project and writes `build/archguard.classpath`:

```bash
./gradlew -q -I archguard.init.gradle classes archguardClasspath
java -jar archguard-cli.jar check $(for f in $(find . -name archguard.classpath -path '*/build/*'); do echo --classpath-file $f; done)
```

## Reports and formats

`--format` takes any subset of `json`, `sarif`, `html`, `agent`, `console` (default `json,sarif,html`), written to `--out` (default `target/archguard`).

`agent` writes `archguard.agent.jsonl` and prints the same lines to stdout. There is one compact JSON object per non-INFO finding (rule, severity, status, file, line, symbol, target, message, fix, fingerprint), followed by a summary line `{"summary":true,"status":"PASSED|FAILED|ERROR",...}`. Progress messages go to stderr, so stdout stays machine-readable.

## Changed files

`--changed-files <file>` (or `-` for stdin) takes newline-separated paths relative to the project. The whole project is still analyzed. Only findings located in the listed files are reported and gated, so a change that introduces a violation against unchanged code is still caught.

```bash
git diff --name-only origin/main...HEAD | java -jar archguard-cli.jar check --changed-files - --format agent
```

Use this for fast local and pull-request feedback; keep a full `check` on the main branch.
