package io.archguard.api;

import java.util.*;

/** {@code specVersion} and {@code language} are null for results built by pre-2.0 callers. */
public record AnalysisResult(
    String schemaVersion,
    String engineVersion,
    String policyHash,
    int analyzedClasses,
    int dependencies,
    List<Finding> findings,
    List<String> diagnostics,
    String specVersion,
    String language) {
  public AnalysisResult {
    findings = List.copyOf(findings);
    diagnostics = List.copyOf(diagnostics);
  }

  public AnalysisResult(
      String schemaVersion,
      String engineVersion,
      String policyHash,
      int analyzedClasses,
      int dependencies,
      List<Finding> findings,
      List<String> diagnostics) {
    this(
        schemaVersion,
        engineVersion,
        policyHash,
        analyzedClasses,
        dependencies,
        findings,
        diagnostics,
        null,
        null);
  }

  public AnalysisResult withFindingsAndDiagnostics(List<Finding> f, List<String> d) {
    return new AnalysisResult(
        schemaVersion, engineVersion, policyHash, analyzedClasses, dependencies, f, d, specVersion,
        language);
  }

  public boolean fails(Severity minimum, boolean newOnly) {
    return findings.stream()
        .anyMatch(
            f ->
                f.status() != Finding.Status.SUPPRESSED
                    && (!newOnly || f.status() == Finding.Status.NEW)
                    && f.severity().atLeast(minimum));
  }
}
