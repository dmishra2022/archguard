# Custom Java rules

See the buildable `examples/custom-rule` module. It implements `ArchitectureRule`, has a unique ID and returns `Finding` objects based on the immutable graph. Register providers in:

```
META-INF/services/io.archguard.api.ArchitectureRule
```

The file contains one fully qualified provider class per line. A public no-argument constructor is required by ServiceLoader.

Install the example:

```bash
cd examples/custom-rule
mvn install
```

Then add the rule pack as a **plugin dependency** in the consuming project:

```xml
<plugin>
  <groupId>io.archguard</groupId>
  <artifactId>archguard-maven-plugin</artifactId>
  <version>0.1.0</version>
  <dependencies>
    <dependency>
      <groupId>example</groupId>
      <artifactId>company-rules</artifactId>
      <version>1.0</version>
    </dependency>
  </dependencies>
  <executions>
    <execution><goals><goal>check</goal></goals></execution>
  </executions>
</plugin>
```

For SDK embedding, pass explicit rule instances to `ArchitectureEngine.analyze`. The SDK does not automatically scan the embedding application's classloader.

Use `Finding.create(...)` to generate stable fingerprints and provide concrete remediation. Avoid source-line-dependent custom evidence text unless intentional: the normalizer only strips conventional `(File.java:line)` locations. Use unique, stable IDs; version published rule packs. Do not overwrite released rule-pack artifacts.

The model provides direct structural dependencies. A custom rule cannot conclude that a missing runtime edge does not exist. Do not interpret informational framework tags as active bean registrations. If a rule requires unavailable evidence, fail the analysis explicitly rather than returning an empty findings list.

Providers execute trusted Java code in the build process. Keep them thread-safe and deterministic. Do not load providers from untrusted repositories.
