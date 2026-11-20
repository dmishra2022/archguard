package io.archguard.config;

import static org.junit.jupiter.api.Assertions.*;

import java.io.IOException;
import java.nio.file.*;
import org.junit.jupiter.api.*;
import org.junit.jupiter.api.io.TempDir;

class PolicyTest {
  @TempDir Path temp;

  Policy read(String text) throws Exception {
    Path p = temp.resolve("architecture.yml");
    Files.writeString(p, text);
    return Policies.read(p);
  }

  @Test
  void validMinimalPolicy() throws Exception {
    assertEquals(1, read("schemaVersion: 1\nroots: ['example..']\n").schemaVersion());
  }

  @Test
  void unknownPropertyFails() {
    assertThrows(
        Exception.class, () -> read("schemaVersion: 1\nroots: ['example..']\nprofiels: [ddd]"));
  }

  @Test
  void duplicateKeyFails() {
    assertThrows(
        Exception.class, () -> read("schemaVersion: 1\nroots: ['example..']\nroots: ['other..']"));
  }

  @Test
  void missingSchemaFails() {
    assertThrows(Exception.class, () -> read("roots: ['example..']"));
  }

  @Test
  void emptyRootsFail() {
    assertThrows(Exception.class, () -> read("schemaVersion: 1\nroots: []"));
  }

  @Test
  void invalidProfileFails() {
    assertThrows(
        Exception.class, () -> read("schemaVersion: 1\nroots: ['example..']\nprofiles: [magic]"));
  }

  @Test
  void invalidSeverityFails() {
    assertThrows(
        Exception.class, () -> read("schemaVersion: 1\nroots: ['example..']\nfailOn: SEVERE"));
  }

  @Test
  void extraDocumentFails() {
    assertThrows(
        Exception.class,
        () ->
            read(
                "schemaVersion: 1\n"
                    + "roots: ['example..']\n"
                    + "---\n"
                    + "schemaVersion: 1\n"
                    + "roots: ['other..']"));
  }

  @Test
  void constraintWithoutGuidanceFails() {
    assertThrows(
        Exception.class,
        () ->
            read(
                "schemaVersion: 1\n"
                    + "roots: ['example..']\n"
                    + "constraints:\n"
                    + "  - id: ORG-001\n"
                    + "    from: ['example..']\n"
                    + "    forbidden: ['java.sql..']"));
  }

  @Test
  void patternRespectsPackageBoundaries() {
    assertTrue(Policies.matches(java.util.List.of("example.domain.."), "example.domain.model"));
    assertFalse(Policies.matches(java.util.List.of("example.domain.."), "example.domainish"));
  }

  @Test
  void quotedBooleanFails() {
    assertThrows(
        Exception.class, () -> read("schemaVersion: 1\nroots: ['example..']\nnewOnly: 'true'"));
  }

  @Test
  void explicitNullFails() {
    assertThrows(
        Exception.class, () -> read("schemaVersion: 1\nroots: ['example..']\nroles: null"));
  }

  Path write(String name, String text) throws IOException {
    Path p = temp.resolve(name);
    Files.createDirectories(p.getParent());
    Files.writeString(p, text);
    return p;
  }

  Policy readAt(String name, String text) throws Exception {
    return Policies.read(write(name, text));
  }

  static final String V2 = "schemaVersion: 2\nlanguage: java\nroots: ['example.**']\n";

  @Test
  void v2PolicyWithGlobSelectors() throws Exception {
    var p = read(V2 + "profiles: [layered, clean]\nroles:\n  DOMAIN: ['example.**.domain.**']\n");
    assertEquals(2, p.schemaVersion());
    assertEquals("java", p.language());
    assertTrue(Policies.matches(p.roles().get(io.archguard.api.Role.DOMAIN), "example.a.domain.b"));
    assertFalse(Policies.matches(p.roles().get(io.archguard.api.Role.DOMAIN), "example.a.domainx"));
  }

  @Test
  void globConversion() {
    assertEquals("com.acme..", Policies.toArchUnit("com.acme.**"));
    assertEquals("..domain..", Policies.toArchUnit("**.domain.**"));
    assertEquals("a..b", Policies.toArchUnit("a.**.b"));
    assertEquals("..", Policies.toArchUnit("**"));
    assertEquals("example..", Policies.toArchUnit("example.."));
    assertTrue(Policies.matches(java.util.List.of("com.acme.**"), "com.acme"));
    assertFalse(Policies.matches(java.util.List.of("com.acme.**"), "com.acmex"));
  }

  @Test
  void v1RejectsV2Keys() {
    assertThrows(
        Exception.class,
        () -> read("schemaVersion: 1\nroots: ['example..']\nlanguage: java\n"));
    assertThrows(
        Exception.class,
        () -> read("schemaVersion: 1\nroots: ['example..']\nprofiles: [layered]\n"));
    assertThrows(
        Exception.class,
        () ->
            read(
                "schemaVersion: 1\nroots: ['example..']\nrules:\n  HEX-001:\n    locked: true\n"));
  }

  @Test
  void v2RequiresJavaLanguageAndKnownProfiles() {
    assertThrows(Exception.class, () -> read("schemaVersion: 2\nroots: ['example.**']\n"));
    assertThrows(
        Exception.class, () -> read("schemaVersion: 2\nlanguage: python\nroots: ['a.**']\n"));
    assertThrows(Exception.class, () -> read(V2 + "profiles: [magic]\n"));
    assertThrows(Exception.class, () -> read(V2 + "roles:\n  DOMAIN: ['src/domain/**']\n"));
    assertThrows(Exception.class, () -> read(V2 + "typeOnlyImports: maybe\n"));
  }

  @Test
  void presetCannotBeAnalyzedDirectly() {
    assertThrows(
        Exception.class,
        () -> read("schemaVersion: 2\nkind: preset\nlanguage: java\nroots: ['a.**']\n"));
  }

  static final String PRESET =
      "schemaVersion: 2\n"
          + "kind: preset\n"
          + "language: java\n"
          + "profiles: [hexagonal]\n"
          + "failOn: WARNING\n"
          + "rules:\n"
          + "  HEX-001:\n"
          + "    severity: ERROR\n"
          + "    locked: true\n"
          + "  CYCLE-001:\n"
          + "    enabled: true\n"
          + "constraints:\n"
          + "  - id: ORG-001\n"
          + "    from: ['**.domain.**']\n"
          + "    forbidden: ['com.vendor.**']\n"
          + "    rationale: parent\n"
          + "    remediation: parent fix\n"
          + "  - id: ORG-002\n"
          + "    from: ['**.domain.**']\n"
          + "    forbidden: ['org.legacy.**']\n"
          + "    rationale: legacy\n"
          + "    remediation: legacy fix\n";

  @Test
  void extendsMergesParentAndChild() throws Exception {
    write("org/base.yml", PRESET);
    var p =
        readAt(
            "app/architecture.yml",
            V2
                + "extends: ['../org/base.yml']\n"
                + "rules:\n"
                + "  CYCLE-001:\n"
                + "    severity: WARNING\n"
                + "constraints:\n"
                + "  - id: ORG-001\n"
                + "    from: ['example.domain.**']\n"
                + "    forbidden: ['com.vendor.**']\n"
                + "    rationale: child\n"
                + "    remediation: child fix\n");
    assertNull(p.kind());
    assertEquals(java.util.Set.of("hexagonal"), p.profiles());
    assertEquals(io.archguard.api.Severity.WARNING, p.failOn());
    assertEquals(true, p.rules().get("CYCLE-001").enabled());
    assertEquals(io.archguard.api.Severity.WARNING, p.rules().get("CYCLE-001").severity());
    assertEquals(2, p.constraints().size());
    assertEquals("child", p.constraints().get(0).rationale());
    assertEquals("ORG-002", p.constraints().get(1).id());
    assertEquals(java.util.List.of("../org/base.yml"), p.parents());
  }

  @Test
  void lockedRuleCannotBeChanged() throws Exception {
    write("org/base.yml", PRESET);
    var e =
        assertThrows(
            IllegalArgumentException.class,
            () ->
                readAt(
                    "app/architecture.yml",
                    V2 + "extends: ['../org/base.yml']\nrules:\n  HEX-001:\n    enabled: false\n"));
    assertTrue(e.getMessage().contains("locked"));
    assertDoesNotThrow(
        () ->
            readAt(
                "app2/architecture.yml",
                V2 + "extends: ['../org/base.yml']\nrules:\n  HEX-001:\n    severity: ERROR\n"));
  }

  @Test
  void extendsRejectsNonPresetCyclesAndMissingFiles() throws Exception {
    write("org/project.yml", V2);
    assertThrows(
        Exception.class,
        () -> readAt("app/architecture.yml", V2 + "extends: ['../org/project.yml']\n"));
    write("loop/a.yml", PRESET + "extends: ['./b.yml']\n");
    write("loop/b.yml", PRESET + "extends: ['./a.yml']\n");
    var cycle =
        assertThrows(
            IllegalArgumentException.class,
            () -> readAt("app/cycle.yml", V2 + "extends: ['../loop/a.yml']\n"));
    assertTrue(cycle.getMessage().contains("Cyclic"));
    assertThrows(
        Exception.class, () -> readAt("app/missing.yml", V2 + "extends: ['./nope.yml']\n"));
    assertThrows(
        Exception.class, () -> readAt("app/v1.yml", "schemaVersion: 1\nroots: ['a..']\nextends: ['./x.yml']\n"));
  }

  @Test
  void orgAndClasspathPresetsResolveFromClassLoader() throws Exception {
    Path cp = temp.resolve("cp");
    Files.createDirectories(cp.resolve("META-INF/archguard/presets/acme/base"));
    Files.writeString(cp.resolve("META-INF/archguard/presets/acme/base/1.2.0.yml"), PRESET);
    Files.createDirectories(cp.resolve("shared"));
    Files.writeString(cp.resolve("shared/strict.yml"), PRESET.replace("failOn: WARNING", "failOn: INFO"));
    try (var loader = new java.net.URLClassLoader(new java.net.URL[] {cp.toUri().toURL()}, null)) {
      Path app = temp.resolve("architecture.yml");
      Files.writeString(app, V2 + "extends: ['org:acme/base@1.2.0']\n");
      assertEquals(io.archguard.api.Severity.WARNING, Policies.read(app, loader).failOn());
      Files.writeString(app, V2 + "extends: ['classpath:shared/strict.yml']\n");
      assertEquals(io.archguard.api.Severity.INFO, Policies.read(app, loader).failOn());
      Files.writeString(app, V2 + "extends: ['org:acme/base@9.9.9']\n");
      var missing = assertThrows(IOException.class, () -> Policies.read(app, loader));
      assertTrue(missing.getMessage().contains("plugin dependency"));
    }
  }
}
