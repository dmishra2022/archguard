package io.archguard.config;

import io.archguard.api.*;
import java.util.*;

/** Strictly decoded YAML. Collections default only when omitted, not when structurally invalid. */
public record Policy(
    int schemaVersion,
    List<String> roots,
    Set<String> profiles,
    Map<Role, List<String>> roles,
    List<Context> contexts,
    List<Constraint> constraints,
    Map<String, RuleSetting> rules,
    Severity failOn,
    boolean newOnly,
    boolean requireClassification,
    boolean allowEmptySelectors,
    boolean allowEmptyAnalysis) {
  public Policy {
    roots = roots == null ? List.of() : List.copyOf(roots);
    profiles = profiles == null ? Set.of() : Set.copyOf(profiles);
    var roleCopy = new EnumMap<Role, List<String>>(Role.class);
    if (roles != null) roles.forEach((k, v) -> roleCopy.put(k, List.copyOf(v)));
    roles = Collections.unmodifiableMap(roleCopy);
    contexts = contexts == null ? List.of() : List.copyOf(contexts);
    constraints = constraints == null ? List.of() : List.copyOf(constraints);
    rules = rules == null ? Map.of() : Map.copyOf(rules);
    failOn = failOn == null ? Severity.ERROR : failOn;
  }

  public record Context(String id, List<String> packages, List<String> exposedPackages) {
    public Context {
      packages = packages == null ? List.of() : List.copyOf(packages);
      exposedPackages = exposedPackages == null ? List.of() : List.copyOf(exposedPackages);
    }
  }

  public record Constraint(
      String id,
      List<String> from,
      List<String> forbidden,
      Severity severity,
      String rationale,
      String remediation) {
    public Constraint {
      from = from == null ? List.of() : List.copyOf(from);
      forbidden = forbidden == null ? List.of() : List.copyOf(forbidden);
      severity = severity == null ? Severity.ERROR : severity;
    }
  }

  public record RuleSetting(Boolean enabled, Severity severity) {}
}
