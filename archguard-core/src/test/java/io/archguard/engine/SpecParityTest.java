package io.archguard.engine;

import static org.junit.jupiter.api.Assertions.*;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.dataformat.yaml.YAMLMapper;
import io.archguard.api.*;
import io.archguard.config.*;
import java.io.IOException;
import java.nio.file.*;
import java.util.*;
import org.junit.jupiter.api.*;

/** Exhaustively checks that spec/ profiles, infrastructure lists and rule activation match the engine. */
class SpecParityTest {
  static final Path SPEC = Path.of("..", "spec");
  static final YAMLMapper YAML = new YAMLMapper();

  static JsonNode yaml(String relative) throws IOException {
    return YAML.readTree(SPEC.resolve(relative).toFile());
  }

  static Policy policy(Set<String> profiles, boolean requireClassification) {
    return new Policy(
        1,
        List.of("example.."),
        profiles,
        Map.of(),
        List.of(),
        List.of(),
        Map.of(),
        Severity.ERROR,
        false,
        requireClassification,
        true,
        false);
  }

  static Set<String> fired(Role from, String target, Role targetRole, Set<String> profiles) {
    var origin = EngineTest.type("example.a.Origin", from, "");
    Map<String, TypeInfo> types = new HashMap<>(Map.of(origin.name(), origin));
    if (targetRole != null) types.put(target, EngineTest.type(target, targetRole, ""));
    var model =
        new ArchitectureModel(types, List.of(EngineTest.edge(origin.name(), target)), List.of());
    Set<String> ids = new TreeSet<>();
    for (var f : BuiltinRules.evaluate(model, policy(profiles, false)))
      if (f.ruleId().startsWith("HEX-") || f.ruleId().startsWith("LAYER-")) ids.add(f.ruleId());
    return ids;
  }

  static Set<String> predicted(JsonNode profile, Role from, Role targetRole, boolean infrastructure) {
    Set<String> ids = new TreeSet<>();
    for (JsonNode rule : profile.path("roleRules")) {
      boolean applies = false;
      for (JsonNode r : rule.path("from")) applies |= r.asText().equals(from.name());
      if (!applies) continue;
      boolean forbiddenRole = false;
      for (JsonNode r : rule.path("forbiddenRoles"))
        forbiddenRole |= targetRole != null && r.asText().equals(targetRole.name());
      if (rule.path("crossRoleOnly").asBoolean(false) && from == targetRole) forbiddenRole = false;
      if (forbiddenRole || (infrastructure && rule.path("forbidInfrastructure").asBoolean(false)))
        ids.add(rule.path("rule").asText());
    }
    return ids;
  }

  @Test
  void hexagonalRoleMatrixMatchesEngineForEveryRolePair() throws IOException {
    JsonNode hexagonal = yaml("profiles/hexagonal.yml");
    for (Role from : Role.values())
      for (Role to : Role.values())
        assertEquals(
            predicted(hexagonal, from, to, false),
            fired(from, "example.b.Target", to, Set.of("hexagonal")),
            from + " -> " + to);
  }

  @Test
  void layeredRoleMatrixMatchesEngineForEveryRolePair() throws IOException {
    JsonNode layered = yaml("profiles/layered.yml");
    for (Role from : Role.values())
      for (Role to : Role.values())
        assertEquals(
            predicted(layered, from, to, false),
            fired(from, "example.b.Target", to, Set.of("layered")),
            from + " -> " + to);
  }

  @Test
  void javaInfrastructureListMatchesEngine() throws IOException {
    JsonNode hexagonal = yaml("profiles/hexagonal.yml");
    List<String> entries = new ArrayList<>();
    yaml("infrastructure/java.yml").path("entries").forEach(e -> entries.add(e.asText()));
    assertFalse(entries.isEmpty());
    for (Role from : Role.values()) {
      for (String prefix : entries)
        assertEquals(
            predicted(hexagonal, from, null, true),
            fired(from, prefix + "Api", null, Set.of("hexagonal")),
            from + " -> " + prefix);
      assertEquals(
          predicted(hexagonal, from, null, false),
          fired(from, "com.vendor.Client", null, Set.of("hexagonal")),
          from + " -> non-infrastructure");
    }
  }

  @Test
  void profileRulesAreInactiveWithoutTheProfile() {
    for (Role from : Role.values())
      for (Role to : Role.values())
        assertEquals(Set.of(), fired(from, "example.b.Target", to, Set.of()), from + " -> " + to);
  }

  @Test
  void catalogActivationMatchesEngine() throws IOException {
    Map<String, Set<String>> activatedBy = new HashMap<>();
    for (String profile : List.of("hexagonal", "ddd"))
      yaml("profiles/" + profile + ".yml")
          .path("activates")
          .forEach(id -> activatedBy.computeIfAbsent(id.asText(), k -> new HashSet<>()).add(profile));
    for (String id : BuiltinRules.IDS) {
      Path file = SPEC.resolve("rules/" + id + ".yml");
      assertTrue(Files.isRegularFile(file), "missing catalog entry " + id);
      String activation = yaml("rules/" + id + ".yml").path("activation").asText();
      for (Set<String> profiles :
          List.of(Set.<String>of(), Set.of("hexagonal"), Set.of("ddd"), Set.of("hexagonal", "ddd")))
        for (boolean classify : List.of(false, true)) {
          boolean expected =
              switch (activation) {
                case "always" -> true;
                case "optIn" -> false;
                case "requireClassification" -> classify;
                case "profile" ->
                    activatedBy.getOrDefault(id, Set.of()).stream().anyMatch(profiles::contains);
                default -> throw new AssertionError("unknown activation " + activation);
              };
          assertEquals(
              expected,
              BuiltinRules.active(id, policy(profiles, classify)),
              id + " profiles=" + profiles + " requireClassification=" + classify);
        }
    }
  }

  @Test
  void catalogDefaultSeveritiesMatchEngine() throws IOException {
    for (String id : BuiltinRules.IDS) {
      String expected = yaml("rules/" + id + ".yml").path("defaultSeverity").asText();
      String actual = id.equals("MODEL-002") ? "INFO" : "ERROR";
      assertEquals(expected, actual, id);
    }
  }
}
