package io.archguard.api;

import java.util.Set;

public record TypeInfo(
    String name,
    String packageName,
    Role role,
    String context,
    Set<String> annotations,
    Set<String> frameworkTags,
    boolean interfaceType,
    Location location) {
  public TypeInfo {
    annotations = Set.copyOf(annotations);
    frameworkTags = Set.copyOf(frameworkTags);
  }
}
