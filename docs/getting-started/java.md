# Quickstart: Java

Time: about 10 minutes. You will run ArchGuard on a sample project, see a violation, and then add it to your own Maven or Gradle project.

**Requirements:** JDK 17 or later, Maven 3.9 (or Gradle for the CLI route), Git.

!!! note "Where the Java artifacts come from"
    The Java artifacts (`io.archguard:*`) are not on Maven Central yet. Install them from source as below, download `archguard-cli-<version>.jar` from the [GitHub releases](https://github.com/dmishra2022/archguard/releases) once a version is tagged, or use your organisation's internal Maven repository if it mirrors them.

## 1. Build ArchGuard and try the samples

```bash
git clone https://github.com/dmishra2022/archguard.git
cd archguard
mvn -B -q install -DskipTests        # installs io.archguard:* 0.1.0 into ~/.m2
```

Run the compliant sample, then the one with a deliberate violation:

```bash
cd examples/clean && mvn -q verify          # passes
cd ../violating && mvn -q verify            # fails with HEX-002
```

The violating build fails with:

```text
ERROR HEX-002 [NEW] example.orders.application.OrderService:11 — Application depends on a concrete outer component
```

The application service imports a concrete adapter instead of an outbound port. Open `target/archguard/index.html` for the full report, with the evidence and the suggested fix.

## 2. Add ArchGuard to your project

=== "Maven"

    Add the plugin to the root `pom.xml`. The `check` goal runs in the `verify` phase:

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

    For a multi-module build, run the aggregate goal from the reactor root instead:
    `mvn -B compile io.archguard:archguard-maven-plugin:0.1.0:check-reactor`.

=== "Gradle or any other build"

    Use the CLI jar with the Gradle init script; no change to your build files is needed:

    ```bash
    ./gradlew -q -I archguard.init.gradle classes archguardClasspath
    java -jar archguard-cli-0.1.0.jar check \
      $(for f in $(find . -name archguard.classpath -path '*/build/*'); do echo --classpath-file $f; done)
    ```

    The init script is [`skills/archguard/scripts/archguard.init.gradle`](../../skills/archguard/scripts/archguard.init.gradle). See the [CLI reference](../CLI.md) for other builds.

## 3. Write a starter policy

Copy [`architecture.java.yml`](../../skills/archguard/templates/architecture.java.yml) to `architecture.yml` at the project root and replace the example package `com.acme.orders` with yours. Selectors match **packages**: `com.acme.orders.domain.**` covers the package and everything below it.

```yaml
schemaVersion: 2
language: java
roots: ["com.acme.orders.**"]
profiles: [hexagonal]
roles:
  DOMAIN: ["com.acme.orders.domain.**"]
  APPLICATION: ["com.acme.orders.application.**"]
  OUTBOUND_PORT: ["com.acme.orders.application.port.out.**"]
  INBOUND_ADAPTER: ["com.acme.orders.adapter.in.**"]
  OUTBOUND_ADAPTER: ["com.acme.orders.adapter.out.**"]
  COMPOSITION_ROOT: ["com.acme.orders"]
requireClassification: true
newOnly: true
```

## 4. Run it in report-only mode

```bash
mvn compile io.archguard:archguard-maven-plugin:0.1.0:analyze
```

`analyze` writes the same reports as `check` but never fails. Adjust the role selectors until no class is reported as unclassified (`MODEL-001`).

## Next steps

- Record existing violations as a baseline and add the CI gate: [Onboarding a project](../ONBOARDING.md#4-capture-existing-debt).
- Understand each rule: [Rules](../RULES.md).
- Where new code should go, per framework: [Java placement guide](../../skills/archguard/reference/java-placement.md).
