package io.archguard.report;

import io.archguard.api.*;
import io.archguard.engine.Debt;
import java.io.*;
import java.net.URI;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.*;

public final class Reports {
  private Reports() {}

  public static void write(Path directory, AnalysisResult result) throws IOException {
    Files.createDirectories(directory);
    atomic(directory.resolve("archguard.json"), Debt.JSON.writeValueAsBytes(result));
    atomic(directory.resolve("archguard.sarif"), Debt.JSON.writeValueAsBytes(sarif(result)));
    atomic(directory.resolve("index.html"), html(result).getBytes(StandardCharsets.UTF_8));
  }

  public static void atomic(Path path, byte[] bytes) throws IOException {
    Path absolute = path.toAbsolutePath();
    Files.createDirectories(absolute.getParent());
    Path temporary = Files.createTempFile(absolute.getParent(), ".archguard-", ".tmp");
    try {
      Files.write(temporary, bytes);
      try {
        Files.move(
            temporary,
            absolute,
            StandardCopyOption.ATOMIC_MOVE,
            StandardCopyOption.REPLACE_EXISTING);
      } catch (AtomicMoveNotSupportedException e) {
        Files.move(temporary, absolute, StandardCopyOption.REPLACE_EXISTING);
      }
    } finally {
      Files.deleteIfExists(temporary);
    }
  }

  public static String console(AnalysisResult r) {
    StringBuilder s =
        new StringBuilder(
            "ArchGuard "
                + r.engineVersion()
                + ": "
                + r.analyzedClasses()
                + " classes, "
                + r.dependencies()
                + " dependencies, "
                + r.findings().size()
                + " findings\n");
    for (var f : r.findings()) {
      if (f.severity() == Severity.INFO) continue;
      s.append(f.severity())
          .append(" ")
          .append(f.ruleId())
          .append(" [")
          .append(f.status())
          .append("] ")
          .append(f.location().symbol())
          .append(":")
          .append(f.location().line())
          .append(" — ")
          .append(f.message())
          .append("\n  ")
          .append(f.remediation())
          .append('\n');
    }
    return s.toString();
  }

  private static Map<String, Object> sarif(AnalysisResult r) {
    Map<String, Map<String, Object>> rules = new TreeMap<>();
    List<Object> results = new ArrayList<>();
    for (var f : r.findings()) {
      rules.putIfAbsent(
          f.ruleId(),
          Map.of(
              "id",
              f.ruleId(),
              "shortDescription",
              Map.of("text", f.ruleId()),
              "help",
              Map.of("text", f.remediation())));
      Map<String, Object> entry = new LinkedHashMap<>();
      entry.put("ruleId", f.ruleId());
      entry.put(
          "level",
          switch (f.severity()) {
            case ERROR -> "error";
            case WARNING -> "warning";
            case INFO -> "note";
          });
      entry.put(
          "message",
          Map.of(
              "text",
              f.message()
                  + "\nEvidence: "
                  + f.evidence()
                  + "\nSuggested correction: "
                  + f.remediation()));
      entry.put("partialFingerprints", Map.of("archguard/v1", f.fingerprint()));
      entry.put("baselineState", f.status().equals("EXISTING") ? "unchanged" : "new");
      Map<String, Object> location = new LinkedHashMap<>();
      location.put(
          "logicalLocations",
          List.of(Map.of("fullyQualifiedName", f.location().symbol(), "kind", "type")));
      if (!f.location().path().isEmpty()) {
        Map<String, Object> physical = new LinkedHashMap<>();
        physical.put(
            "artifactLocation", Map.of("uri", uri(f.location().path()), "uriBaseId", "%SRCROOT%"));
        if (f.location().line() > 0)
          physical.put("region", Map.of("startLine", f.location().line()));
        location.put("physicalLocation", physical);
      }
      entry.put("locations", List.of(location));
      entry.put(
          "properties",
          Map.of("module", f.location().module(), "target", f.target(), "status", f.status()));
      if (f.status().equals("SUPPRESSED"))
        entry.put(
            "suppressions",
            List.of(
                Map.of(
                    "kind",
                    "external",
                    "status",
                    "accepted",
                    "justification",
                    "Reviewed suppression; see report diagnostics for owner, reason and expiry")));
      results.add(entry);
    }
    return Map.of(
        "version",
        "2.1.0",
        "$schema",
        "https://json.schemastore.org/sarif-2.1.0.json",
        "runs",
        List.of(
            Map.of(
                "tool",
                Map.of(
                    "driver",
                    Map.of(
                        "name",
                        "ArchGuard",
                        "version",
                        r.engineVersion(),
                        "rules",
                        new ArrayList<>(rules.values()))),
                "results",
                results,
                "invocations",
                List.of(Map.of("executionSuccessful", true)),
                "properties",
                Map.of("policyHash", r.policyHash(), "diagnostics", r.diagnostics()))));
  }

  private static String uri(String path) {
    try {
      return new URI(null, null, path, null).toASCIIString();
    } catch (Exception e) {
      throw new IllegalArgumentException("Invalid source path", e);
    }
  }

  public static String html(AnalysisResult r) {
    StringBuilder s =
        new StringBuilder(
            "<!doctype html><html lang=\"en\"><meta charset=\"utf-8\"><meta name=\"viewport\""
                + " content=\"width=device-width, initial-scale=1\"><meta"
                + " http-equiv=\"Content-Security-Policy\" content=\"default-src 'none'; style-src"
                + " 'unsafe-inline'\"><title>ArchGuard architecture"
                + " report</title><style>body{font:16px system-ui;max-width:1100px;margin:40px"
                + " auto;padding:0"
                + " 24px;background:#f5f7fb;color:#19243a}article{background:white;border:1px solid"
                + " #dce3ee;border-left:5px solid #375dd3;padding:20px;margin:18px"
                + " 0;border-radius:8px}code,pre{white-space:pre-wrap;overflow-wrap:anywhere}small{color:#526078}h1{letter-spacing:-1px}.ERROR{border-left-color:#be3030}.WARNING{border-left-color:#b8860b}summary{cursor:pointer}</style><body><h1>ArchGuard</h1>");
    s.append("<p>Engine ")
        .append(escape(r.engineVersion()))
        .append(" · ")
        .append(r.analyzedClasses())
        .append(" classes · ")
        .append(r.dependencies())
        .append(" static dependencies · ")
        .append(r.findings().size())
        .append(
            " findings</p><p>Analysis completed. Gate outcome depends on configured severity and"
                + " baseline policy.</p>");
    s.append("<details><summary>Scope and diagnostics</summary><ul>");
    for (String d : r.diagnostics()) s.append("<li>").append(escape(d)).append("</li>");
    s.append("</ul><small>Policy: ").append(escape(r.policyHash())).append("</small></details>");
    for (var f : r.findings())
      s.append("<article class=\"")
          .append(f.severity())
          .append("\"><small>")
          .append(escape(f.ruleId()))
          .append(" · ")
          .append(f.severity())
          .append(" · ")
          .append(escape(f.status()))
          .append("</small><h2>")
          .append(escape(f.message()))
          .append("</h2><p><code>")
          .append(
              escape(
                  f.location().module()
                      + " / "
                      + f.location().path()
                      + ":"
                      + f.location().line()
                      + " — "
                      + f.location().symbol()))
          .append("</code></p><p><strong>Evidence</strong></p><pre>")
          .append(escape(f.evidence()))
          .append("</pre><p><strong>Suggested correction</strong></p><p>")
          .append(escape(f.remediation()))
          .append("</p><small>Fingerprint: ")
          .append(escape(f.fingerprint()))
          .append("</small></article>");
    return s.append("</body></html>").toString();
  }

  private static String escape(String s) {
    return s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace("\"", "&quot;")
        .replace("'", "&#39;");
  }
}
