package io.archguard.api;

import java.util.*;

public record AnalysisResult(
    String schemaVersion,
    String engineVersion,
    String policyHash,
    int analyzedClasses,
    int dependencies,
    List<Finding> findings,
    List<String> diagnostics) {
  public AnalysisResult {
    findings = List.copyOf(findings);
    diagnostics = List.copyOf(diagnostics);
  }

  public boolean fails(Severity minimum, boolean newOnly) {
    return findings.stream()
        .anyMatch(
            f ->
                !f.status().equals("SUPPRESSED")
                    && (!newOnly || f.status().equals("NEW"))
                    && f.severity().atLeast(minimum));
  }
}
