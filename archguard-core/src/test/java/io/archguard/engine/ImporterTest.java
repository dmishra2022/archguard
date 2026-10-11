package io.archguard.engine;

import static org.junit.jupiter.api.Assertions.*;

import io.archguard.api.*;
import io.archguard.config.*;
import java.nio.file.*;
import java.util.*;
import org.junit.jupiter.api.*;
import org.junit.jupiter.api.io.TempDir;

class ImporterTest {
  @TempDir Path temp;
  static ArchitectureModel model;

  static Policy policy() {
    return new Policy(
        1,
        List.of("io.archguard.fixtures.."),
        Set.of("hexagonal"),
        Map.of(
            Role.DOMAIN,
            List.of("io.archguard.fixtures.domain.."),
            Role.OUTBOUND_ADAPTER,
            List.of("io.archguard.fixtures.out.."),
            Role.INBOUND_ADAPTER,
            List.of("io.archguard.fixtures.inbound.."),
            Role.OUTBOUND_PORT,
            List.of("io.archguard.fixtures.port..")),
        List.of(),
        List.of(),
        Map.of(),
        Severity.ERROR,
        false,
        true,
        false,
        false);
  }

  static ModuleInput input() {
    return new ModuleInput(
        "fixture", Path.of("target/test-classes"), List.of(Path.of("src/test/java")), Path.of(""));
  }

  @BeforeAll
  static void load() throws Exception {
    model =
        new ModelImporter()
            .read(
                List.of(input()),
                Arrays.stream(
                        System.getProperty("java.class.path").split(java.io.File.pathSeparator))
                    .map(Path::of)
                    .toList(),
                policy());
  }

  @Test
  void realBytecodeDetectsDependency() {
    assertTrue(
        model.dependencies().stream()
            .anyMatch(
                d -> d.origin().endsWith("domain.Order") && d.target().endsWith("JpaAdapter")));
  }

  @Test
  void springEndpointClassified() {
    assertTrue(
        model
            .types()
            .get("io.archguard.fixtures.inbound.WebEndpoint")
            .frameworkTags()
            .contains("spring.endpoint"));
  }

  @Test
  void composedSpringEndpointClassified() {
    assertTrue(
        model
            .types()
            .get("io.archguard.fixtures.inbound.ComposedEndpoint")
            .frameworkTags()
            .contains("spring.endpoint"));
  }

  @Test
  void jaxRsEndpointClassified() {
    assertTrue(
        model
            .types()
            .get("io.archguard.fixtures.inbound.RestResource")
            .frameworkTags()
            .contains("jaxrs.endpoint"));
  }

  @Test
  void bothPersistenceNamespacesClassified() {
    assertTrue(
        model
            .types()
            .get("io.archguard.fixtures.domain.JpaEntity")
            .frameworkTags()
            .contains("persistence.entity"));
    assertTrue(
        model
            .types()
            .get("io.archguard.fixtures.domain.LegacyEntity")
            .frameworkTags()
            .contains("persistence.entity"));
  }

  @Test
  void genericPortLeakDetected() {
    var result = new ArchitectureEngine().evaluate(model, policy(), List.of());
    assertTrue(
        result.findings().stream()
            .anyMatch(
                f -> f.ruleId().equals("HEX-003") && f.location().symbol().endsWith("LeakyPort")));
  }

  @Test
  void httpGenericEntityLeakDetected() {
    var result = new ArchitectureEngine().evaluate(model, policy(), List.of());
    var leaks = result.findings().stream().filter(f -> f.ruleId().equals("FW-002")).toList();
    // One leak from the Spring WebEndpoint.load() (List<JpaEntity>), one from the Micronaut
    // MicronautEndpoint.load() (MicronautEntity). Both must be detected end-to-end.
    assertEquals(2, leaks.size());
    assertTrue(
        leaks.stream()
            .anyMatch(
                f ->
                    f.location().symbol().contains("WebEndpoint")
                        && f.location().symbol().contains("load()")));
    assertTrue(
        leaks.stream()
            .anyMatch(
                f ->
                    f.location().symbol().contains("MicronautEndpoint")
                        && f.location().symbol().contains("load(")));
  }

  @Test
  void micronautEndpointClassified() {
    assertTrue(
        model
            .types()
            .get("io.archguard.fixtures.inbound.MicronautEndpoint")
            .frameworkTags()
            .contains("micronaut.endpoint"));
  }

  @Test
  void micronautEntityClassified() {
    assertTrue(
        model
            .types()
            .get("io.archguard.fixtures.domain.MicronautEntity")
            .frameworkTags()
            .contains("persistence.entity"));
  }

  @Test
  void micronautRepositoryClassified() {
    assertTrue(
        model
            .types()
            .get("io.archguard.fixtures.out.MicronautRepository")
            .frameworkTags()
            .contains("micronaut.repository"));
  }

  @Test
  void micronautHttpEntityLeakDetected() {
    var result = new ArchitectureEngine().evaluate(model, policy(), List.of());
    var micronautLeaks =
        result.findings().stream()
            .filter(f -> f.ruleId().equals("FW-002"))
            .filter(f -> f.location().symbol().contains("MicronautEndpoint"))
            .toList();
    assertEquals(1, micronautLeaks.size());
    assertTrue(micronautLeaks.get(0).location().symbol().contains("load("));
    assertTrue(
        micronautLeaks.get(0).message().contains("MicronautEntity")
            || micronautLeaks.get(0).evidence().contains("MicronautEntity"));
  }

  @Test
  void shadedAsmSupportsJava25Bytecode() throws Exception {
    // Guards against a silent regression in the shaded ASM inside ArchUnit: if the Opcodes
    // constant V25 is ever lost, ArchGuard cannot analyse Java 25 (class file v69) projects
    // such as the ddd order-management-service.
    Class<?> opcodes =
        Class.forName("com.tngtech.archunit.thirdparty.org.objectweb.asm.Opcodes");
    int v25 = opcodes.getField("V25").getInt(null);
    assertEquals(0x45, v25 & 0xFFFF, "ASM Opcodes.V25 must equal class file major version 69");
  }

  @Test
  void sourcePathIsReal() {
    assertTrue(
        model
            .types()
            .get("io.archguard.fixtures.domain.Order")
            .location()
            .path()
            .endsWith("src/test/java/io/archguard/fixtures/domain/Order.java"));
  }

  @Test
  void missingDirectDependencyFails() {
    assertThrows(
        java.io.IOException.class,
        () -> new ModelImporter().read(List.of(input()), List.of(), policy()));
  }

  @Test
  void missingCompiledOutputFails() {
    assertThrows(
        java.io.IOException.class,
        () ->
            new ModelImporter()
                .read(
                    List.of(new ModuleInput("missing", temp.resolve("none"), List.of(), temp)),
                    List.of(),
                    policy()));
  }

  @Test
  void duplicateClassesFail() {
    assertThrows(
        java.io.IOException.class,
        () ->
            new ModelImporter()
                .read(
                    List.of(
                        input(),
                        new ModuleInput(
                            "second",
                            input().classes(),
                            input().sourceRoots(),
                            input().workspaceRoot())),
                    List.of(),
                    policy()));
  }

  @Test
  void unmatchedRootsFail() {
    var p =
        new Policy(
            1,
            List.of("absent.."),
            Set.of(),
            Map.of(),
            List.of(),
            List.of(),
            Map.of(),
            Severity.ERROR,
            false,
            false,
            false,
            false);
    assertThrows(
        IllegalArgumentException.class,
        () -> new ModelImporter().read(List.of(input()), List.of(), p));
  }

  @Test
  void ambiguousMappingsFail() {
    var p =
        new Policy(
            1,
            List.of("io.archguard.fixtures.."),
            Set.of(),
            Map.of(
                Role.DOMAIN,
                List.of("io.archguard.fixtures.."),
                Role.APPLICATION,
                List.of("io.archguard.fixtures..")),
            List.of(),
            List.of(),
            Map.of(),
            Severity.ERROR,
            false,
            false,
            false,
            false);
    assertThrows(
        IllegalArgumentException.class,
        () -> new ModelImporter().read(List.of(input()), List.of(), p));
  }

  @Test
  void emptyRoleSelectorFails() {
    var p =
        new Policy(
            1,
            List.of("io.archguard.fixtures.."),
            Set.of(),
            Map.of(Role.DOMAIN, List.of("absent..")),
            List.of(),
            List.of(),
            Map.of(),
            Severity.ERROR,
            false,
            false,
            false,
            false);
    assertThrows(
        IllegalArgumentException.class,
        () -> new ModelImporter().read(List.of(input()), List.of(), p));
  }

  @Test
  void corruptedCompiledClassCannotBeSkipped() throws Exception {
    Path pkg = temp.resolve("io/archguard/fixtures/domain");
    Files.createDirectories(pkg);
    Files.copy(
        Path.of("target/test-classes/io/archguard/fixtures/domain/Order.class"),
        pkg.resolve("Order.class"));
    Files.write(pkg.resolve("Corrupt.class"), new byte[] {0, 1, 2, 3});
    var p =
        new Policy(
            1,
            List.of("io.archguard.fixtures.."),
            Set.of(),
            Map.of(),
            List.of(),
            List.of(),
            Map.of(),
            Severity.ERROR,
            false,
            false,
            true,
            false);
    assertThrows(
        java.io.IOException.class,
        () ->
            new ModelImporter()
                .read(List.of(new ModuleInput("bad", temp, List.of(), temp)), List.of(), p));
  }

  @Test
  void importsAreIsolatedAcrossThreads() throws Exception {
    var pool = java.util.concurrent.Executors.newFixedThreadPool(2);
    try {
      var cp =
          Arrays.stream(System.getProperty("java.class.path").split(java.io.File.pathSeparator))
              .map(Path::of)
              .toList();
      var first = pool.submit(() -> new ModelImporter().read(List.of(input()), cp, policy()));
      var second = pool.submit(() -> new ModelImporter().read(List.of(input()), cp, policy()));
      assertEquals(first.get().types(), second.get().types());
    } finally {
      pool.shutdownNow();
    }
  }
}
