package io.archguard.engine;

import io.archguard.api.*;
import io.archguard.config.*;
import io.archguard.spec.SpecCatalog;
import java.util.*;

/**
 * Built-in rules driven by the spec catalog: role boundaries come from every profile's role matrix,
 * activation from the selected profiles, and texts from the rule catalog.
 */
public final class BuiltinRules {
  private static final SpecCatalog CATALOG = SpecCatalog.get();
  public static final Set<String> IDS = CATALOG.ruleIds(Policies.LANGUAGE);
  private static final List<String> INFRASTRUCTURE = CATALOG.infrastructure(Policies.LANGUAGE);
  private static final Set<String> ENDPOINT_TAGS =
      Set.of("spring.endpoint", "jaxrs.endpoint", "micronaut.endpoint");

  private BuiltinRules() {}

  public static boolean active(String id, Policy p) {
    var setting = p.rules().get(id);
    if (setting != null && setting.enabled() != null) return setting.enabled();
    if (CATALOG.activatedBy(id, p.profiles())) return true;
    return switch (CATALOG.rule(id).activation()) {
      case "always" -> true;
      case "requireClassification" -> p.requireClassification();
      default -> false;
    };
  }

  public static List<Finding> evaluate(ArchitectureModel model, Policy p) {
    List<Finding> out = new ArrayList<>();
    for (TypeInfo t : model.types().values()) {
      var roleValues = Map.of("role", String.valueOf(t.role()));
      var d =
          new Dependency(
              t.name(), t.name(), CATALOG.rule("MODEL-001").evidence(roleValues), t.location());
      if (t.role() == Role.UNCLASSIFIED) add(out, p, "MODEL-001", Map.of(), d);
      if (!t.frameworkTags().isEmpty()) {
        var tags = Map.of("tags", new TreeSet<>(t.frameworkTags()).toString());
        add(
            out,
            p,
            "MODEL-002",
            tags,
            new Dependency(
                t.name(), t.name(), CATALOG.rule("MODEL-002").evidence(tags), t.location()));
      }
      if (t.frameworkTags().stream().anyMatch(ENDPOINT_TAGS::contains)
          && t.role() != Role.INBOUND_ADAPTER
          && t.role() != Role.UNCLASSIFIED)
        add(
            out,
            p,
            "FW-001",
            Map.of(),
            new Dependency(
                t.name(), t.name(), CATALOG.rule("FW-001").evidence(roleValues), t.location()));
    }
    for (Dependency d : model.dependencies()) {
      if (d.kind() == Dependency.Kind.HTTP_ENTITY_EXPOSURE) {
        add(out, p, "FW-002", Map.of(), d);
        continue;
      }
      var from = model.types().get(d.origin());
      if (from == null) continue;
      var to = model.types().get(d.target());
      Role targetRole = to == null ? roleFor(d.target(), p) : to.role();
      boolean infrastructure = isInfrastructure(d.target());
      Set<String> boundary = new LinkedHashSet<>();
      for (var rule : CATALOG.roleRules())
        if (rule.forbids(from.role(), targetRole, infrastructure)) boundary.add(rule.rule());
      for (String id : boundary) add(out, p, id, Map.of(), d);
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
          add(out, p, "DDD-001", Map.of("targetContext", targetContext), d);
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
    String id = context ? "DDD-002" : "CYCLE-001";
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
        var values =
            Map.of("component", component.toString(), "edges", String.join(", ", edges));
        var evidence =
            new Dependency(
                first.origin(), first.target(), CATALOG.rule(id).evidence(values), first.location());
        add(out, p, id, values, evidence);
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
    return INFRASTRUCTURE.stream().anyMatch(n::startsWith);
  }

  private static void add(
      List<Finding> out, Policy p, String id, Map<String, String> values, Dependency d) {
    var rule = CATALOG.rule(id);
    add(out, p, id, rule.defaultSeverity(), rule.message(values), d, rule.remediation(values));
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
