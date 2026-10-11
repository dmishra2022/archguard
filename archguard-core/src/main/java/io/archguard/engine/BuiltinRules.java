package io.archguard.engine;

import io.archguard.api.*;
import io.archguard.config.*;
import java.util.*;

public final class BuiltinRules {
  public static final Set<String> IDS =
      Set.of(
          "HEX-001",
          "HEX-002",
          "HEX-003",
          "HEX-004",
          "DDD-001",
          "DDD-002",
          "CYCLE-001",
          "FW-001",
          "FW-002",
          "MODEL-001",
          "MODEL-002");

  private BuiltinRules() {}

  public static boolean active(String id, Policy p) {
    var setting = p.rules().get(id);
    if (setting != null && setting.enabled() != null) return setting.enabled();
    if (id.startsWith("HEX-")) return p.profiles().contains("hexagonal");
    if (id.startsWith("DDD-")) return p.profiles().contains("ddd");
    if (id.equals("CYCLE-001")) return false;
    if (id.equals("MODEL-001")) return p.requireClassification();
    return true;
  }

  public static List<Finding> evaluate(ArchitectureModel model, Policy p) {
    List<Finding> out = new ArrayList<>();
    for (TypeInfo t : model.types().values()) {
      var d =
          new Dependency(
              t.name(), t.name(), "Declared architectural role: " + t.role(), t.location());
      if (t.role() == Role.UNCLASSIFIED)
        add(
            out,
            p,
            "MODEL-001",
            Severity.ERROR,
            "Application class has no declared architectural role",
            d,
            "Map this package to a role in architecture.yml, or explicitly exclude it from analysis"
                + " roots.");
      if (!t.frameworkTags().isEmpty())
        add(
            out,
            p,
            "MODEL-002",
            Severity.INFO,
            "Framework classification signals: " + new TreeSet<>(t.frameworkTags()),
            new Dependency(
                t.name(),
                t.name(),
                "Static framework metadata: " + new TreeSet<>(t.frameworkTags()),
                t.location()),
            "Review these signals when declaring roles. They do not prove active beans or runtime"
                + " wiring.");
      if ((t.frameworkTags().contains("spring.endpoint")
              || t.frameworkTags().contains("jaxrs.endpoint")
              || t.frameworkTags().contains("micronaut.endpoint"))
          && t.role() != Role.INBOUND_ADAPTER
          && t.role() != Role.UNCLASSIFIED)
        add(
            out,
            p,
            "FW-001",
            Severity.ERROR,
            "HTTP endpoint is outside an inbound adapter",
            d,
            "Move transport handling to an inbound adapter and delegate use-case execution through"
                + " the application boundary.");
    }
    for (Dependency d : model.dependencies()) {
      if (d.kind() == Dependency.Kind.HTTP_ENTITY_EXPOSURE) {
        add(
            out,
            p,
            "FW-002",
            Severity.ERROR,
            "HTTP contract exposes a persistence entity",
            d,
            "Introduce a transport DTO for this endpoint signature and map to/from the entity"
                + " inside the adapter or application boundary. Update the documented API contract"
                + " and its tests.");
        continue;
      }
      var from = model.types().get(d.origin());
      if (from == null) continue;
      var to = model.types().get(d.target());
      Role targetRole = to == null ? roleFor(d.target(), p) : to.role();
      boolean infrastructure = isInfrastructure(d.target());
      if (from.role() == Role.DOMAIN
          && (infrastructure
              || Set.of(
                      Role.APPLICATION,
                      Role.INBOUND_ADAPTER,
                      Role.OUTBOUND_ADAPTER,
                      Role.COMPOSITION_ROOT)
                  .contains(targetRole)))
        add(
            out,
            p,
            "HEX-001",
            Severity.ERROR,
            "Domain depends on an outer layer or framework",
            d,
            "Remove this dependency from the domain. Move integration or orchestration outward;"
                + " keep domain behavior in domain types and pass domain-oriented values.");
      if (from.role() == Role.APPLICATION
          && (Set.of(Role.INBOUND_ADAPTER, Role.OUTBOUND_ADAPTER, Role.COMPOSITION_ROOT)
              .contains(targetRole)))
        add(
            out,
            p,
            "HEX-002",
            Severity.ERROR,
            "Application depends on a concrete outer component",
            d,
            "Replace the concrete adapter dependency with an outbound port owned by the core."
                + " Implement the port in the adapter and wire it in the composition root.");
      if (Set.of(Role.INBOUND_PORT, Role.OUTBOUND_PORT).contains(from.role())
          && (infrastructure
              || Set.of(Role.INBOUND_ADAPTER, Role.OUTBOUND_ADAPTER, Role.COMPOSITION_ROOT)
                  .contains(targetRole)))
        add(
            out,
            p,
            "HEX-003",
            Severity.ERROR,
            "Port depends on an infrastructure or transport type",
            d,
            "Change the port contract to core-owned inputs and outputs. Map persistence, transport"
                + " and vendor types inside the adapter.");
      if (Set.of(Role.INBOUND_ADAPTER, Role.OUTBOUND_ADAPTER).contains(from.role())
          && Set.of(Role.INBOUND_ADAPTER, Role.OUTBOUND_ADAPTER).contains(targetRole)
          && from.role() != targetRole)
        add(
            out,
            p,
            "HEX-004",
            Severity.ERROR,
            "Inbound and outbound adapters depend directly on each other",
            d,
            "Route the operation through the application use case and its ports instead of coupling"
                + " transport directly to persistence or another outbound adapter.");
      String targetContext = to == null ? contextFor(d.target(), p) : to.context();
      if (!from.context().isEmpty()
          && !targetContext.isEmpty()
          && !from.context().equals(targetContext)) {
        var ctx =
            p.contexts().stream()
                .filter(c -> c.id().equals(targetContext))
                .findFirst()
                .orElseThrow();
        if (!Policies.matches(ctx.exposedPackages(), packageName(d.target())))
          add(
              out,
              p,
              "DDD-001",
              Severity.ERROR,
              "Cross-context access to internal type in " + targetContext,
              d,
              "Use an explicitly exposed API or integration contract of "
                  + targetContext
                  + ". Keep its domain internals private to that context.");
      }
      for (var constraint : p.constraints())
        if (Policies.matches(constraint.from(), from.packageName())
            && Policies.matches(constraint.forbidden(), packageName(d.target())))
          add(
              out,
              p,
              constraint.id(),
              constraint.severity(),
              constraint.rationale(),
              d,
              constraint.remediation());
    }
    if (active("DDD-002", p)) cycleFindings(out, model, p, true);
    if (active("CYCLE-001", p)) cycleFindings(out, model, p, false);
    return out;
  }

  private static void cycleFindings(
      List<Finding> out, ArchitectureModel m, Policy p, boolean context) {
    Map<String, Set<String>> graph = new TreeMap<>();
    Map<String, Dependency> witnesses = new HashMap<>();
    for (Dependency d : m.dependencies()) {
      var a = m.types().get(d.origin());
      var b = m.types().get(d.target());
      if (a == null || b == null) continue;
      String x = context ? a.context() : a.packageName(),
          y = context ? b.context() : b.packageName();
      if (x.isEmpty() || y.isEmpty() || x.equals(y)) continue;
      graph.computeIfAbsent(x, k -> new TreeSet<>()).add(y);
      witnesses.putIfAbsent(x + "\n" + y, d);
    }
    for (var component : Cycles.components(graph)) {
      Set<String> members = new HashSet<>(component);
      List<String> edges = new ArrayList<>();
      Dependency first = null;
      for (String x : component)
        for (String y : graph.getOrDefault(x, Set.of()))
          if (members.contains(y)) {
            edges.add(x + " -> " + y);
            if (first == null) first = witnesses.get(x + "\n" + y);
          }
      if (first != null) {
        String label = context ? "bounded contexts" : "packages";
        var evidence =
            new Dependency(
                first.origin(),
                first.target(),
                "Strongly connected " + label + ": " + String.join(", ", edges),
                first.location());
        add(
            out,
            p,
            context ? "DDD-002" : "CYCLE-001",
            Severity.ERROR,
            "Dependency cycle among " + label + ": " + component,
            evidence,
            "Break at least one dependency in this component. Move a shared contract to an"
                + " appropriate owner or invert a dependency through a port; verify that the full"
                + " cycle is eliminated.");
      }
    }
  }

  private static Role roleFor(String name, Policy p) {
    var roles =
        p.roles().entrySet().stream()
            .filter(e -> Policies.matches(e.getValue(), packageName(name)))
            .map(Map.Entry::getKey)
            .toList();
    if (roles.size() > 1) throw new IllegalArgumentException("Ambiguous target role: " + name);
    return roles.isEmpty() ? Role.UNCLASSIFIED : roles.get(0);
  }

  private static String contextFor(String name, Policy p) {
    var contexts =
        p.contexts().stream()
            .filter(c -> Policies.matches(c.packages(), packageName(name)))
            .toList();
    if (contexts.size() > 1)
      throw new IllegalArgumentException("Ambiguous target context: " + name);
    return contexts.isEmpty() ? "" : contexts.get(0).id();
  }

  private static String packageName(String name) {
    int index = name.lastIndexOf('.');
    return index < 0 ? "" : name.substring(0, index);
  }

  private static boolean isInfrastructure(String n) {
    return List.of(
            "org.springframework.",
            "io.quarkus.",
            "io.micronaut.",
            "jakarta.persistence.",
            "javax.persistence.",
            "jakarta.ws.rs.",
            "javax.ws.rs.",
            "jakarta.enterprise.",
            "javax.enterprise.",
            "jakarta.servlet.",
            "javax.servlet.",
            "org.hibernate.",
            "java.sql.",
            "javax.sql.")
        .stream()
        .anyMatch(n::startsWith);
  }

  private static void add(
      List<Finding> out,
      Policy p,
      String id,
      Severity severity,
      String message,
      Dependency d,
      String fix) {
    if (IDS.contains(id) && !active(id, p)) return;
    var setting = p.rules().get(id);
    if (setting != null) {
      if (Boolean.FALSE.equals(setting.enabled())) return;
      if (setting.severity() != null) severity = setting.severity();
    }
    out.add(Finding.create(id, severity, message, d, fix));
  }
}
