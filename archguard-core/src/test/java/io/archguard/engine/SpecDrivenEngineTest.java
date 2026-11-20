package io.archguard.engine;

import static org.junit.jupiter.api.Assertions.*;

import io.archguard.api.*;
import io.archguard.config.*;
import java.nio.file.*;
import java.util.*;
import org.junit.jupiter.api.*;

class SpecDrivenEngineTest {
  /** policyHash of examples/clean/architecture.yml produced by ArchGuard 0.1.0 before the refactor. */
  static final String CLEAN_V1_HASH =
      "becf11f3d3708c4d9f1aa0659da89ac1fce2865e4666e60000f1b3012e3c80ff";

  static Policy v2(Set<String> profiles, Map<String, Policy.RuleSetting> rules) {
    return new Policy(
        2,
        List.of("example.**"),
        profiles,
        Map.of(),
        List.of(),
        List.of(),
        rules,
        Severity.ERROR,
        false,
        false,
        true,
        false,
        null,
        "java",
        null,
        null,
        null,
        null);
  }

  @Test
  void v1PolicyHashIsUnchangedSoBaselinesStayValid() throws Exception {
    assertEquals(
        CLEAN_V1_HASH,
        ArchitectureEngine.hash(Policies.read(Path.of("..", "examples", "clean", "architecture.yml"))));
  }

  @Test
  void v2HashIncludesV2Settings() {
    var a = v2(Set.of("hexagonal"), Map.of());
    var b = v2(Set.of("hexagonal"), Map.of("HEX-001", new Policy.RuleSetting(null, null, true)));
    assertNotEquals(ArchitectureEngine.hash(a), ArchitectureEngine.hash(b));
  }

  @Test
  void includedProfilesActivateTheirRules() {
    var clean = v2(Set.of("clean"), Map.of());
    assertTrue(BuiltinRules.active("HEX-002", clean));
    assertTrue(BuiltinRules.active("CYCLE-001", clean));
    assertFalse(BuiltinRules.active("DDD-001", clean));
    var monolith = v2(Set.of("modular-monolith"), Map.of());
    assertTrue(BuiltinRules.active("DDD-001", monolith));
    assertTrue(BuiltinRules.active("DDD-002", monolith));
    assertTrue(BuiltinRules.active("CYCLE-001", monolith));
    assertFalse(BuiltinRules.active("HEX-001", monolith));
    var disabled = v2(Set.of("clean"), Map.of("CYCLE-001", new Policy.RuleSetting(false, null)));
    assertFalse(BuiltinRules.active("CYCLE-001", disabled));
  }

  @Test
  void layeredProfileReportsUpwardDependencyWithCatalogTexts() {
    var persistence = EngineTest.type("example.persistence.Dao", Role.OUTBOUND_ADAPTER, "");
    var service = EngineTest.type("example.service.OrderService", Role.APPLICATION, "");
    var result =
        new ArchitectureEngine()
            .evaluate(EngineTest.model(persistence, service), v2(Set.of("layered"), Map.of()), List.of());
    var finding =
        result.findings().stream().filter(f -> f.ruleId().equals("LAYER-001")).findFirst().orElseThrow();
    assertEquals("Lower layer depends on a higher layer", finding.message());
    assertTrue(finding.remediation().startsWith("Invert the dependency"));
    assertEquals("2.0.0", result.specVersion());
    assertEquals("java", result.language());
    assertTrue(result.findings().stream().noneMatch(f -> f.ruleId().startsWith("HEX-")));
  }

  @Test
  void layeredAllowsBusinessToPersistenceWhichHexagonalForbids() {
    var service = EngineTest.type("example.service.OrderService", Role.APPLICATION, "");
    var persistence = EngineTest.type("example.persistence.Dao", Role.OUTBOUND_ADAPTER, "");
    var model = EngineTest.model(service, persistence);
    var engine = new ArchitectureEngine();
    assertFalse(engine.evaluate(model, v2(Set.of("layered"), Map.of()), List.of()).fails(Severity.ERROR, false));
    assertTrue(engine.evaluate(model, v2(Set.of("hexagonal"), Map.of()), List.of()).fails(Severity.ERROR, false));
  }

  @Test
  void describeListsCatalogAndCustomRules() {
    ArchitectureRule custom =
        new ArchitectureRule() {
          public String id() {
            return "ACME-001";
          }

          public List<Finding> evaluate(ArchitectureModel m) {
            return List.of();
          }

          public RuleDescriptor descriptor() {
            return new RuleDescriptor("ACME-001", "No vendor SDK", Severity.WARNING, "", Set.of());
          }
        };
    var rules = new ArchitectureEngine().describe(List.of(custom));
    assertTrue(rules.stream().anyMatch(r -> r.id().equals("LAYER-002") && r.title().contains("bypasses")));
    assertEquals("No vendor SDK", rules.get(rules.size() - 1).title());
  }

  @Test
  void customDescriptorMustMatchId() {
    ArchitectureRule custom =
        new ArchitectureRule() {
          public String id() {
            return "ACME-001";
          }

          public List<Finding> evaluate(ArchitectureModel m) {
            return List.of();
          }

          public RuleDescriptor descriptor() {
            return RuleDescriptor.of("OTHER-001");
          }
        };
    assertThrows(
        IllegalArgumentException.class,
        () ->
            new ArchitectureEngine()
                .evaluate(
                    new ArchitectureModel(Map.of(), List.of(), List.of()),
                    EngineTest.policy(),
                    List.of(custom)));
  }

  @Test
  void globSelectorsInConstraintsMatch() {
    var c =
        new Policy.Constraint(
            "ORG-001", List.of("**.domain.**"), List.of("java.sql.**"), Severity.ERROR, "r", "fix");
    var p =
        new Policy(
            2, List.of("example.**"), Set.of(), Map.of(), List.of(), List.of(c), Map.of(),
            Severity.ERROR, false, false, true, false, null, "java", null, null, null, null);
    var a = EngineTest.type("example.orders.domain.Order", Role.DOMAIN, "");
    var m =
        new ArchitectureModel(
            Map.of(a.name(), a), List.of(EngineTest.edge(a.name(), "java.sql.Connection")), List.of());
    assertTrue(EngineTest.has(new ArchitectureEngine().evaluate(m, p, List.of()), "ORG-001"));
  }
}
