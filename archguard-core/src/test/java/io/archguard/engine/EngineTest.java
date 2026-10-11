package io.archguard.engine;

import static org.junit.jupiter.api.Assertions.*;

import io.archguard.api.*;
import io.archguard.config.*;
import io.archguard.report.Reports;
import java.nio.file.*;
import java.time.*;
import java.util.*;
import org.junit.jupiter.api.*;
import org.junit.jupiter.api.io.TempDir;

class EngineTest {
  @TempDir Path temp;

  static Policy policy() {
    return new Policy(
        1,
        List.of("example.."),
        Set.of("hexagonal", "ddd"),
        Map.of(),
        List.of(
            new Policy.Context(
                "orders", List.of("example.orders.."), List.of("example.orders.api..")),
            new Policy.Context(
                "billing", List.of("example.billing.."), List.of("example.billing.api.."))),
        List.of(),
        Map.of(),
        Severity.ERROR,
        false,
        true,
        true,
        false);
  }

  static TypeInfo type(String name, Role role, String ctx) {
    return new TypeInfo(
        name,
        name.substring(0, name.lastIndexOf('.')),
        role,
        ctx,
        Set.of(),
        Set.of(),
        false,
        new Location("app", "src/main/java/Example.java", name, 0));
  }

  static Dependency edge(String a, String b) {
    return new Dependency(
        a,
        b,
        "Method <" + a + ".run()> calls <" + b + ".run()> in (Example.java:12)",
        new Location("app", "src/main/java/Example.java", a, 12));
  }

  static ArchitectureModel model(TypeInfo a, TypeInfo b) {
    return new ArchitectureModel(
        Map.of(a.name(), a, b.name(), b), List.of(edge(a.name(), b.name())), List.of());
  }

  static AnalysisResult result(ArchitectureModel m) {
    return new ArchitectureEngine().evaluate(m, policy(), List.of());
  }

  static boolean has(AnalysisResult r, String id) {
    return r.findings().stream().anyMatch(f -> f.ruleId().equals(id));
  }

  @Test
  void domainToAdapterFails() {
    assertTrue(
        has(
            result(
                model(
                    type("example.orders.domain.Order", Role.DOMAIN, "orders"),
                    type("example.orders.out.Store", Role.OUTBOUND_ADAPTER, "orders"))),
            "HEX-001"));
  }

  @Test
  void domainToApplicationFails() {
    assertTrue(
        has(
            result(
                model(
                    type("example.orders.domain.Order", Role.DOMAIN, "orders"),
                    type("example.orders.app.Service", Role.APPLICATION, "orders"))),
            "HEX-001"));
  }

  @Test
  void applicationToAdapterFails() {
    assertTrue(
        has(
            result(
                model(
                    type("example.orders.app.Service", Role.APPLICATION, "orders"),
                    type("example.orders.out.Store", Role.OUTBOUND_ADAPTER, "orders"))),
            "HEX-002"));
  }

  @Test
  void applicationToPortPasses() {
    assertFalse(
        result(
                model(
                    type("example.orders.app.Service", Role.APPLICATION, "orders"),
                    type("example.orders.port.Store", Role.OUTBOUND_PORT, "orders")))
            .fails(Severity.ERROR, false));
  }

  @Test
  void outboundAdapterToPortPasses() {
    assertFalse(
        result(
                model(
                    type("example.orders.out.Store", Role.OUTBOUND_ADAPTER, "orders"),
                    type("example.orders.port.Store", Role.OUTBOUND_PORT, "orders")))
            .fails(Severity.ERROR, false));
  }

  @Test
  void portLeaksPersistenceType() {
    assertTrue(
        has(
            result(
                model(
                    type("example.orders.port.Store", Role.OUTBOUND_PORT, "orders"),
                    type("jakarta.persistence.EntityManager", Role.UNCLASSIFIED, ""))),
            "HEX-003"));
  }

  @Test
  void domainToMicronautInfrastructureFails() {
    assertTrue(
        has(
            result(
                model(
                    type("example.orders.domain.Order", Role.DOMAIN, "orders"),
                    type("io.micronaut.http.HttpResponse", Role.UNCLASSIFIED, ""))),
            "HEX-001"));
  }

  @Test
  void portLeaksMicronautType() {
    assertTrue(
        has(
            result(
                model(
                    type("example.orders.port.Store", Role.OUTBOUND_PORT, "orders"),
                    type("io.micronaut.http.HttpRequest", Role.UNCLASSIFIED, ""))),
            "HEX-003"));
  }

  @Test
  void adapterBypassFails() {
    assertTrue(
        has(
            result(
                model(
                    type("example.orders.in.Web", Role.INBOUND_ADAPTER, "orders"),
                    type("example.orders.out.Store", Role.OUTBOUND_ADAPTER, "orders"))),
            "HEX-004"));
  }

  @Test
  void crossContextInternalsFail() {
    assertTrue(
        has(
            result(
                model(
                    type("example.orders.domain.Order", Role.DOMAIN, "orders"),
                    type("example.billing.domain.Invoice", Role.DOMAIN, "billing"))),
            "DDD-001"));
  }

  @Test
  void crossContextExposedApiPasses() {
    assertFalse(
        has(
            result(
                model(
                    type("example.orders.domain.Order", Role.DOMAIN, "orders"),
                    type("example.billing.api.InvoiceId", Role.DOMAIN, "billing"))),
            "DDD-001"));
  }

  @Test
  void unclassifiedFailsWhenRequired() {
    assertTrue(
        has(
            result(
                model(
                    type("example.orders.Unknown", Role.UNCLASSIFIED, "orders"),
                    type("example.orders.Order", Role.DOMAIN, "orders"))),
            "MODEL-001"));
  }

  @Test
  void contextCycleShowsAllEdges() {
    var a = type("example.orders.Order", Role.DOMAIN, "orders");
    var b = type("example.billing.Invoice", Role.DOMAIN, "billing");
    var r =
        result(
            new ArchitectureModel(
                Map.of(a.name(), a, b.name(), b),
                List.of(edge(a.name(), b.name()), edge(b.name(), a.name())),
                List.of()));
    assertTrue(has(r, "DDD-002"));
    assertTrue(
        r.findings().stream()
            .filter(f -> f.ruleId().equals("DDD-002"))
            .findFirst()
            .orElseThrow()
            .evidence()
            .contains("orders -> billing"));
  }

  @Test
  void acyclicContextsPass() {
    assertFalse(
        has(
            result(
                model(
                    type("example.orders.Order", Role.DOMAIN, "orders"),
                    type("example.billing.Invoice", Role.DOMAIN, "billing"))),
            "DDD-002"));
  }

  @Test
  void fingerprintSurvivesLineMovement() {
    var d = edge("a.A", "b.B");
    var f = Finding.create("X", Severity.ERROR, "x", d, "fix");
    var changed =
        new Dependency(
            d.origin(),
            d.target(),
            d.evidence().replace(":12", ":99"),
            new Location("app", d.location().path(), d.origin(), 99));
    assertEquals(
        f.fingerprint(), Finding.create("X", Severity.ERROR, "x", changed, "fix").fingerprint());
  }

  @Test
  void severityGateWorks() {
    var r =
        result(
            model(
                type("example.orders.domain.Order", Role.DOMAIN, "orders"),
                type("example.orders.out.Store", Role.OUTBOUND_ADAPTER, "orders")));
    assertTrue(r.fails(Severity.ERROR, false));
  }

  @Test
  void baselineAllowsExistingButNotNew() throws Exception {
    var r =
        result(
            model(
                type("example.orders.domain.Order", Role.DOMAIN, "orders"),
                type("example.orders.out.Store", Role.OUTBOUND_ADAPTER, "orders")));
    Path b = temp.resolve("baseline.json");
    Debt.writeBaseline(b, r);
    var accepted = Debt.apply(r, b, null, Clock.systemUTC());
    assertFalse(accepted.fails(Severity.ERROR, true));
    assertTrue(accepted.fails(Severity.ERROR, false));
    var newer =
        result(
            model(
                type("example.orders.domain.NewOrder", Role.DOMAIN, "orders"),
                type("example.orders.out.Store", Role.OUTBOUND_ADAPTER, "orders")));
    assertTrue(Debt.apply(newer, b, null, Clock.systemUTC()).fails(Severity.ERROR, true));
  }

  @Test
  void baselinePolicyMismatchFails() throws Exception {
    Path b = temp.resolve("b.json");
    Debt.JSON.writeValue(b.toFile(), new Debt.Baseline(1, "bad", Set.of()));
    assertThrows(
        java.io.IOException.class,
        () ->
            Debt.apply(
                result(new ArchitectureModel(Map.of(), List.of(), List.of())),
                b,
                null,
                Clock.systemUTC()));
  }

  @Test
  void expiredSuppressionFails() throws Exception {
    var r =
        result(
            model(
                type("example.orders.domain.Order", Role.DOMAIN, "orders"),
                type("example.orders.out.Store", Role.OUTBOUND_ADAPTER, "orders")));
    Path s = temp.resolve("s.json");
    Debt.JSON.writeValue(
        s.toFile(),
        new Debt.Suppressions(
            1,
            List.of(
                new Debt.Suppression(
                    r.findings().get(0).fingerprint(), "team", "migration", "2020-01-01"))));
    assertThrows(
        java.io.IOException.class,
        () ->
            Debt.apply(
                r, null, s, Clock.fixed(Instant.parse("2026-10-06T00:00:00Z"), ZoneOffset.UTC)));
  }

  @Test
  void validSuppressionRecordsOwnerAndDoesNotGate() throws Exception {
    var r =
        result(
            model(
                type("example.orders.domain.Order", Role.DOMAIN, "orders"),
                type("example.orders.out.Store", Role.OUTBOUND_ADAPTER, "orders")));
    Path s = temp.resolve("s.json");
    Debt.JSON.writeValue(
        s.toFile(),
        new Debt.Suppressions(
            1,
            List.of(
                new Debt.Suppression(
                    r.findings().get(0).fingerprint(),
                    "orders-team",
                    "approved migration",
                    "2026-10-06"))));
    var ignored =
        Debt.apply(r, null, s, Clock.fixed(Instant.parse("2026-10-06T00:00:00Z"), ZoneOffset.UTC));
    assertFalse(ignored.fails(Severity.ERROR, false));
    assertTrue(ignored.diagnostics().stream().anyMatch(d -> d.contains("orders-team")));
  }

  @Test
  void unknownRuleFails() {
    var p = policy();
    var bad =
        new Policy(
            1,
            p.roots(),
            p.profiles(),
            p.roles(),
            p.contexts(),
            p.constraints(),
            Map.of("TYPO", new Policy.RuleSetting(true, null)),
            Severity.ERROR,
            false,
            false,
            true,
            false);
    assertThrows(
        IllegalArgumentException.class,
        () ->
            new ArchitectureEngine()
                .evaluate(new ArchitectureModel(Map.of(), List.of(), List.of()), bad, List.of()));
  }

  @Test
  void customRulesRun() {
    ArchitectureRule custom =
        new ArchitectureRule() {
          public String id() {
            return "COMPANY-001";
          }

          public List<Finding> evaluate(ArchitectureModel m) {
            return List.of(
                Finding.create(
                    id(),
                    Severity.WARNING,
                    "Company rule",
                    edge("a.A", "b.B"),
                    "Use approved API"));
          }
        };
    var r =
        new ArchitectureEngine()
            .evaluate(
                new ArchitectureModel(Map.of(), List.of(), List.of()), policy(), List.of(custom));
    assertTrue(has(r, "COMPANY-001"));
    assertFalse(r.fails(Severity.ERROR, false));
    assertTrue(r.fails(Severity.WARNING, false));
  }

  @Test
  void customRuleExceptionsAreNotPasses() {
    ArchitectureRule custom =
        new ArchitectureRule() {
          public String id() {
            return "BROKEN";
          }

          public List<Finding> evaluate(ArchitectureModel m) {
            throw new IllegalStateException("boom");
          }
        };
    assertThrows(
        IllegalStateException.class,
        () ->
            new ArchitectureEngine()
                .evaluate(
                    new ArchitectureModel(Map.of(), List.of(), List.of()),
                    policy(),
                    List.of(custom)));
  }

  @Test
  void customRuleCannotShadowBuiltin() {
    ArchitectureRule custom =
        new ArchitectureRule() {
          public String id() {
            return "HEX-001";
          }

          public List<Finding> evaluate(ArchitectureModel m) {
            return List.of();
          }
        };
    assertThrows(
        IllegalArgumentException.class,
        () ->
            new ArchitectureEngine()
                .evaluate(
                    new ArchitectureModel(Map.of(), List.of(), List.of()),
                    policy(),
                    List.of(custom)));
  }

  @Test
  void configurableDependencyRule() {
    var c =
        new Policy.Constraint(
            "ORG-001",
            List.of("example.orders.."),
            List.of("java.sql.."),
            Severity.ERROR,
            "No JDBC in orders",
            "Use persistence port");
    var p =
        new Policy(
            1,
            List.of("example.."),
            Set.of(),
            Map.of(),
            List.of(),
            List.of(c),
            Map.of(),
            Severity.ERROR,
            false,
            false,
            true,
            false);
    var a = type("example.orders.Order", Role.DOMAIN, "");
    var m =
        new ArchitectureModel(
            Map.of(a.name(), a), List.of(edge(a.name(), "java.sql.Connection")), List.of());
    assertTrue(has(new ArchitectureEngine().evaluate(m, p, List.of()), "ORG-001"));
  }

  @Test
  void disabledRuleDoesNotEmit() {
    var p = policy();
    var disabled =
        new Policy(
            1,
            p.roots(),
            p.profiles(),
            p.roles(),
            p.contexts(),
            p.constraints(),
            Map.of("HEX-001", new Policy.RuleSetting(false, null)),
            Severity.ERROR,
            false,
            false,
            true,
            false);
    assertFalse(
        has(
            new ArchitectureEngine()
                .evaluate(
                    model(
                        type("example.orders.domain.Order", Role.DOMAIN, "orders"),
                        type("example.orders.out.Store", Role.OUTBOUND_ADAPTER, "orders")),
                    disabled,
                    List.of()),
            "HEX-001"));
  }

  @Test
  void deterministicOutput() {
    var m =
        model(
            type("example.orders.domain.Order", Role.DOMAIN, "orders"),
            type("example.orders.out.Store", Role.OUTBOUND_ADAPTER, "orders"));
    assertEquals(result(m), result(m));
  }

  @Test
  void reportsEscapeUntrustedContentAndHaveSarifLocations() throws Exception {
    var f =
        Finding.create(
            "X", Severity.ERROR, "<script>alert('x')</script>", edge("a.A", "b.B"), "<b>fix</b>");
    var r = new AnalysisResult("1", "test", "hash", 2, 1, List.of(f), List.of());
    Reports.write(temp, r);
    String html = Files.readString(temp.resolve("index.html"));
    assertFalse(html.contains("<script>"));
    assertTrue(html.contains("&lt;script&gt;"));
    var sarif = Debt.JSON.readTree(temp.resolve("archguard.sarif").toFile());
    assertEquals(
        12, sarif.at("/runs/0/results/0/locations/0/physicalLocation/region/startLine").asInt());
    assertFalse(Files.list(temp).anyMatch(p -> p.getFileName().toString().endsWith(".tmp")));
  }

  @Test
  void largeGraphDoesNotOverflowStack() {
    Map<String, Set<String>> graph = new HashMap<>();
    for (int i = 0; i < 20000; i++) graph.put("n" + i, Set.of("n" + (i + 1)));
    assertTrue(Cycles.components(graph).isEmpty());
    graph.put("n20000", Set.of("n0"));
    assertEquals(20001, Cycles.components(graph).get(0).size());
  }

  @Test
  void separateCyclesRemainSeparate() {
    assertEquals(
        2,
        Cycles.components(
                Map.of("a", Set.of("b"), "b", Set.of("a"), "c", Set.of("d"), "d", Set.of("c")))
            .size());
  }
}
