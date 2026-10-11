package io.archguard.api;

import java.util.*;

public record ArchitectureModel(
    Map<String, TypeInfo> types, List<Dependency> dependencies, List<String> diagnostics) {
  public ArchitectureModel {
    types = Collections.unmodifiableMap(new TreeMap<>(types));
    dependencies = List.copyOf(dependencies);
    diagnostics = List.copyOf(diagnostics);
  }
}
