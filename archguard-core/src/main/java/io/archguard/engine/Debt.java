package io.archguard.engine;

import com.fasterxml.jackson.core.*;
import com.fasterxml.jackson.databind.*;
import io.archguard.api.*;
import java.io.*;
import java.nio.file.*;
import java.time.*;
import java.util.*;

public final class Debt {
  private Debt() {}

  public static final ObjectMapper JSON =
      new ObjectMapper()
          .enable(SerializationFeature.INDENT_OUTPUT)
          .enable(DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES)
          .enable(DeserializationFeature.FAIL_ON_TRAILING_TOKENS)
          .enable(JsonParser.Feature.STRICT_DUPLICATE_DETECTION);

  public record Baseline(int schemaVersion, String policyHash, Set<String> fingerprints) {
    public Baseline {
      fingerprints = Set.copyOf(fingerprints);
    }
  }

  public record Suppression(String fingerprint, String owner, String reason, String expires) {}

  public record Suppressions(int schemaVersion, List<Suppression> entries) {}

  public static void writeBaseline(Path path, AnalysisResult result) throws IOException {
    var fingerprints = new TreeSet<String>();
    result.findings().stream()
        .filter(f -> f.severity() != Severity.INFO)
        .forEach(f -> fingerprints.add(f.fingerprint()));
    io.archguard.report.Reports.atomic(
        path, JSON.writeValueAsBytes(new Baseline(1, result.policyHash(), fingerprints)));
  }

  public static AnalysisResult apply(
      AnalysisResult r, Path baseline, Path suppressions, Clock clock) throws IOException {
    Set<String> accepted = Set.of();
    Map<String, Suppression> ignored = new HashMap<>();
    if (baseline != null) {
      var b = JSON.readValue(baseline.toFile(), Baseline.class);
      if (b.schemaVersion() != 1 || !r.policyHash().equals(b.policyHash()))
        throw new IOException(
            "Baseline schema, engine or policy does not match; review and explicitly regenerate"
                + " it");
      accepted = b.fingerprints();
    }
    if (suppressions != null) {
      var file = JSON.readValue(suppressions.toFile(), Suppressions.class);
      if (file.schemaVersion() != 1 || file.entries() == null)
        throw new IOException("Invalid suppression schema");
      for (var s : file.entries()) {
        if (s.fingerprint() == null
            || !s.fingerprint().matches("[a-f0-9]{64}")
            || s.owner() == null
            || s.owner().isBlank()
            || s.reason() == null
            || s.reason().isBlank())
          throw new IOException("Suppression requires fingerprint, owner and reason");
        try {
          if (LocalDate.parse(s.expires()).isBefore(LocalDate.now(clock)))
            throw new IOException("Expired suppression: " + s.fingerprint());
        } catch (DateTimeException | NullPointerException e) {
          throw new IOException("Invalid suppression expiry", e);
        }
        if (ignored.putIfAbsent(s.fingerprint(), s) != null)
          throw new IOException("Duplicate suppression: " + s.fingerprint());
      }
    }
    List<Finding> findings = new ArrayList<>();
    for (var f : r.findings())
      findings.add(
          f.withStatus(
              ignored.containsKey(f.fingerprint())
                  ? "SUPPRESSED"
                  : accepted.contains(f.fingerprint()) ? "EXISTING" : "NEW"));
    List<String> diagnostics = new ArrayList<>(r.diagnostics());
    Set<String> current = new HashSet<>();
    findings.forEach(f -> current.add(f.fingerprint()));
    long stale = accepted.stream().filter(f -> !current.contains(f)).count();
    diagnostics.add(
        "Baseline entries no longer observed in this scope: " + stale + " (baseline not modified)");
    for (var s : ignored.values())
      diagnostics.add(
          "Suppression "
              + s.fingerprint()
              + " owner="
              + s.owner()
              + " expires="
              + s.expires()
              + " reason="
              + s.reason());
    return new AnalysisResult(
        r.schemaVersion(),
        r.engineVersion(),
        r.policyHash(),
        r.analyzedClasses(),
        r.dependencies(),
        findings,
        diagnostics);
  }
}
