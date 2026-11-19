package io.archguard.report;

import io.archguard.api.*;
import io.archguard.engine.Debt;
import io.archguard.spec.SpecCatalog;
import java.io.*;
import java.net.URI;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.*;

public final class Reports {
  private Reports() {}

  public static final Set<String> FORMATS = Set.of("json", "sarif", "html", "agent", "console");
  public static final String AGENT_FILE = "archguard.agent.jsonl";

  public static void write(Path directory, AnalysisResult result) throws IOException {
    write(directory, result, Set.of("json", "sarif", "html"), false);
  }

  /** Writes the selected file formats; {@code gateFailed} feeds the agent summary line. */
  public static void write(
      Path directory, AnalysisResult result, Set<String> formats, boolean gateFailed)
      throws IOException {
    Files.createDirectories(directory);
    if (formats.contains("json"))
      atomic(directory.resolve("archguard.json"), Debt.JSON.writeValueAsBytes(result));
    if (formats.contains("sarif"))
      atomic(directory.resolve("archguard.sarif"), Debt.JSON.writeValueAsBytes(sarif(result)));
    if (formats.contains("html"))
      atomic(directory.resolve("index.html"), html(result).getBytes(StandardCharsets.UTF_8));
    if (formats.contains("agent"))
      atomic(
          directory.resolve(AGENT_FILE),
          agent(result, gateFailed).getBytes(StandardCharsets.UTF_8));
  }

  /**
   * Overwrites the report set with explicit failure outputs so a stale pass is never left behind.
   */
  public static void writeFailure(Path directory, Throwable error, Set<String> formats)
      throws IOException {
    String message = String.valueOf(error.getMessage());
    Map<String, Object> failed = new LinkedHashMap<>();
    failed.put("schemaVersion", "1");
    failed.put("specVersion", SpecCatalog.get().specVersion());
    failed.put("analysisStatus", "FAILED");
    failed.put("error", message);
    atomic(directory.resolve("archguard.json"), Debt.JSON.writeValueAsBytes(failed));
    var notification = Map.of("level", "error", "message", Map.of("text", message));
    var invocation =
        Map.of("executionSuccessful", false, "toolExecutionNotifications", List.of(notification));
    var run =
        Map.of(
            "tool",
            Map.of("driver", Map.of("name", "ArchGuard")),
            "invocations",
            List.of(invocation));
    atomic(
        directory.resolve("archguard.sarif"),
        Debt.JSON.writeValueAsBytes(Map.of("version", "2.1.0", "runs", List.of(run))));
    atomic(
        directory.resolve("index.html"),
        "<!doctype html><html lang=\"en\"><meta charset=\"utf-8\"><title>ArchGuard analysis failed</title><h1>Analysis failed</h1><p>No compliance result is available. See archguard.json and the build log for the error.</p></html>"
            .getBytes(StandardCharsets.UTF_8));
    if (formats.contains("agent"))
      atomic(directory.resolve(AGENT_FILE), agentError(message).getBytes(StandardCharsets.UTF_8));
  }

  /** One JSON object per non-INFO finding, then a summary line (spec/CLI.md, agent format). */
  public static String agent(AnalysisResult r, boolean gateFailed) {
    StringBuilder s = new StringBuilder();
    Map<Finding.Status, Integer> counts = new EnumMap<>(Finding.Status.class);
    for (var f : r.findings()) {
      if (f.severity() == Severity.INFO) continue;
      counts.merge(f.status(), 1, Integer::sum);
      Map<String, Object> line = new LinkedHashMap<>();
      line.put("rule", f.ruleId());
      line.put("severity", f.severity().name());
      line.put("status", f.status().name());
      line.put("file", f.location().path());
      line.put("line", f.location().line());
      line.put("symbol", f.location().symbol());
      line.put("target", f.target());
      line.put("message", f.message());
      line.put("fix", f.remediation());
      line.put("fingerprint", f.fingerprint());
      s.append(compact(line)).append('\n');
    }
    Map<String, Object> summary = new LinkedHashMap<>();
    summary.put("summary", true);
    summary.put("status", gateFailed ? "FAILED" : "PASSED");
    summary.put("new", counts.getOrDefault(Finding.Status.NEW, 0));
    summary.put("existing", counts.getOrDefault(Finding.Status.EXISTING, 0));
    summary.put("suppressed", counts.getOrDefault(Finding.Status.SUPPRESSED, 0));
    return s.append(compact(summary)).append('\n').toString();
  }

  public static String agentError(String message) {
    Map<String, Object> summary = new LinkedHashMap<>();
    summary.put("summary", true);
    summary.put("status", "ERROR");
    summary.put("error", message);
    return compact(summary) + "\n";
  }

  private static String compact(Map<String, Object> value) {
    try {
      return COMPACT.writeValueAsString(value);
    } catch (IOException e) {
      throw new UncheckedIOException(e);
    }
  }

  private static final com.fasterxml.jackson.databind.ObjectMapper COMPACT =
      new com.fasterxml.jackson.databind.ObjectMapper();

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
    var catalog = SpecCatalog.get().rules();
    for (var f : r.findings()) {
      var spec = catalog.get(f.ruleId());
      rules.putIfAbsent(
          f.ruleId(),
          Map.of(
              "id",
              f.ruleId(),
              "shortDescription",
              Map.of("text", spec == null ? f.ruleId() : spec.title()),
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
      entry.put("baselineState", f.status() == Finding.Status.EXISTING ? "unchanged" : "new");
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
          Map.of(
              "module", f.location().module(), "target", f.target(), "status", f.status().name()));
      if (f.status() == Finding.Status.SUPPRESSED)
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
                Map.of(
                    "policyHash",
                    r.policyHash(),
                    "diagnostics",
                    r.diagnostics(),
                    "specVersion",
                    r.specVersion() == null ? SpecCatalog.get().specVersion() : r.specVersion()))));
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
          .append(escape(f.status().name()))
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
