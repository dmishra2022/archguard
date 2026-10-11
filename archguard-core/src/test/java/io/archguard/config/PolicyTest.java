package io.archguard.config;

import static org.junit.jupiter.api.Assertions.*;

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
}
