package io.archguard.api;

import java.util.*;

/**
 * Implementations must be deterministic, read-only, and safe for concurrent independent runs.
 * Providers are trusted executable build code. Exceptions abort analysis (never become passes).
 */
public interface ArchitectureRule {
  String id();

  List<Finding> evaluate(ArchitectureModel model);

  /** Metadata for reports and rule listings; its id must equal {@link #id()}. */
  default RuleDescriptor descriptor() {
    return RuleDescriptor.of(id());
  }
}
