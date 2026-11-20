package io.archguard.api;

import java.util.*;

/**
 * Catalog metadata for a rule: shown in reports, SARIF and rule listings. Built-in descriptors come
 * from the ArchGuard spec rule catalog.
 */
public record RuleDescriptor(
    String id, String title, Severity defaultSeverity, String helpUri, Set<String> tags) {
  public RuleDescriptor {
    Objects.requireNonNull(id, "id");
    title = title == null || title.isBlank() ? id : title;
    defaultSeverity = defaultSeverity == null ? Severity.ERROR : defaultSeverity;
    helpUri = helpUri == null ? "" : helpUri;
    tags = tags == null ? Set.of() : Set.copyOf(tags);
  }

  public static RuleDescriptor of(String id) {
    return new RuleDescriptor(id, id, Severity.ERROR, "", Set.of());
  }
}
