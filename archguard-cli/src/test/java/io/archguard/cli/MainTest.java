package io.archguard.cli;

import static org.junit.jupiter.api.Assertions.*;

import com.fasterxml.jackson.databind.JsonNode;
import io.archguard.engine.Debt;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.*;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

class MainTest {
  private static final Path PROJECT = Path.of("").toAbsolutePath();
  private static final Path CLASSES = PROJECT.resolve("target/test-classes");
  private static final Path SOURCES = PROJECT.resolve("src/test/java");
  private static final String VIOLATING =
      "src/test/java/io/archguard/cli/fixtures/orders/application/PlaceOrder.java";
  private static final String POLICY =
      """
      schemaVersion: 2
      language: java
      roots: ["io.archguard.cli.fixtures.orders.**"]
      profiles: [hexagonal]
      roles:
        DOMAIN: ["io.archguard.cli.fixtures.orders.domain.**"]
        APPLICATION: ["io.archguard.cli.fixtures.orders.application.**"]
        OUTBOUND_PORT: ["io.archguard.cli.fixtures.orders.port.**"]
        OUTBOUND_ADAPTER: ["io.archguard.cli.fixtures.orders.adapter.**"]
      requireClassification: true
      """;

  @TempDir Path dir;

  record Run(int code, String out, String err) {}

  private Run run(String stdin, String... args) {
    var out = new ByteArrayOutputStream();
    var err = new ByteArrayOutputStream();
    int code =
        Main.run(
            args,
            new ByteArrayInputStream(stdin.getBytes(StandardCharsets.UTF_8)),
            new PrintStream(out, true, StandardCharsets.UTF_8),
            new PrintStream(err, true, StandardCharsets.UTF_8));
    return new Run(code, out.toString(StandardCharsets.UTF_8), err.toString(StandardCharsets.UTF_8));
  }

  private Path policy(String text) throws IOException {
    return Files.writeString(Files.createTempFile(dir, "architecture", ".yml"), text);
  }

  private List<String> analysis(String command, String... extra) throws IOException {
    List<String> args =
        new ArrayList<>(
            List.of(
                command,
                "--project",
                PROJECT.toString(),
                "--config",
                policy(POLICY).toString(),
                "--out",
                dir.resolve("out").toString(),
                "--classes",
                CLASSES.toString(),
                "--source-root",
                SOURCES.toString()));
    args.addAll(List.of(extra));
    return args;
  }

  private Run run(List<String> args) {
    return run("", args.toArray(String[]::new));
  }

  private JsonNode report() throws IOException {
    return Debt.JSON.readTree(dir.resolve("out/archguard.json").toFile());
  }

  @Test
  void checkFailsWithExitOneAndWritesAllReports() throws IOException {
    Run r = run(analysis("check"));
    assertEquals(Main.VIOLATION, r.code(), r.err());
    for (String f : List.of("archguard.json", "archguard.sarif", "index.html"))
      assertTrue(Files.exists(dir.resolve("out").resolve(f)), f);
    JsonNode hex =
        findFirst(report().get("findings"), "HEX-002");
    assertEquals(VIOLATING, hex.get("location").get("path").asText());
    assertEquals("java", report().get("language").asText());
    assertTrue(r.err().contains("Architecture policy violated"));
  }

  @Test
  void analyzeNeverGates() throws IOException {
    assertEquals(Main.OK, run(analysis("analyze")).code());
  }

  @Test
  void agentFormatPrintsFindingsAndSummary() throws IOException {
    Run r = run(analysis("check", "--format", "agent"));
    assertEquals(Main.VIOLATION, r.code());
    List<String> lines = r.out().lines().toList();
    JsonNode first = Debt.JSON.readTree(lines.get(0));
    assertEquals("HEX-002", first.get("rule").asText());
    assertEquals(VIOLATING, first.get("file").asText());
    assertEquals("io.archguard.cli.fixtures.orders.adapter.SqlOrderStore", first.get("target").asText());
    assertTrue(first.get("fix").asText().contains("outbound port"));
    JsonNode summary = Debt.JSON.readTree(lines.get(lines.size() - 1));
    assertEquals("FAILED", summary.get("status").asText());
    assertEquals(lines.size() - 1, summary.get("new").asInt());
    assertTrue(lines.size() > 1);
    assertEquals(r.out(), Files.readString(dir.resolve("out/archguard.agent.jsonl")));
    assertFalse(Files.exists(dir.resolve("out/archguard.json")));
  }

  @Test
  void failOnOverrideChangesTheGate() throws IOException {
    Path p = policy(POLICY + "rules:\n  HEX-002: { severity: WARNING }\n");
    List<String> args = analysis("check");
    args.set(args.indexOf("--config") + 1, p.toString());
    assertEquals(Main.OK, run(args).code());
    args.addAll(List.of("--fail-on", "warning"));
    assertEquals(Main.VIOLATION, run(args).code());
  }

  @Test
  void baselineAcceptsExistingDebtAndRefusesSilentOverwrite() throws IOException {
    Path baseline = dir.resolve("architecture-baseline.json");
    Path p = policy(POLICY + "newOnly: true\n");
    List<String> capture = analysis("baseline", "--baseline-output", baseline.toString());
    capture.set(capture.indexOf("--config") + 1, p.toString());
    assertEquals(Main.OK, run(capture).code());
    assertTrue(Files.exists(baseline));
    assertEquals(Main.ERROR, run(capture).code());
    capture.add("--overwrite-baseline");
    assertEquals(Main.OK, run(capture).code());

    List<String> check = analysis("check", "--baseline", baseline.toString());
    check.set(check.indexOf("--config") + 1, p.toString());
    Run r = run(check);
    assertEquals(Main.OK, r.code(), r.err());
    assertEquals("EXISTING", findFirst(report().get("findings"), "HEX-002").get("status").asText());
  }

  @Test
  void changedFilesScopeReportsOnlyListedFiles() throws IOException {
    Path other = dir.resolve("changed.txt");
    Files.writeString(other, "src/test/java/io/archguard/cli/fixtures/orders/domain/Order.java\n");
    Run r = run(analysis("check", "--changed-files", other.toString()));
    assertEquals(Main.OK, r.code(), r.err());
    assertEquals(0, report().get("findings").size());
    assertTrue(report().get("diagnostics").toString().contains("Changed-files scope"));

    Run stdin = run("./" + VIOLATING + "\n", analysis("check", "--changed-files", "-").toArray(String[]::new));
    assertEquals(Main.VIOLATION, stdin.code(), stdin.err());
  }

  @Test
  void symlinkedProjectStillMapsSourceFiles() throws IOException {
    Path link = Files.createSymbolicLink(dir.resolve("link"), PROJECT);
    List<String> args = analysis("check");
    args.set(args.indexOf("--project") + 1, link.toString());
    args.set(args.indexOf("--source-root") + 1, link.resolve("src/test/java").toString());
    assertEquals(Main.VIOLATION, run(args).code());
    assertEquals(VIOLATING, findFirst(report().get("findings"), "HEX-002").get("location").get("path").asText());
  }

  @Test
  void invalidPolicyIsAnAnalysisErrorWithFailureReports() throws IOException {
    List<String> args = analysis("check", "--format", "json,agent");
    args.set(args.indexOf("--config") + 1, policy("schemaVersion: 2\nlanguage: java\nroots: []\n").toString());
    Run r = run(args);
    assertEquals(Main.ERROR, r.code());
    assertEquals("FAILED", report().get("analysisStatus").asText());
    assertTrue(Files.exists(dir.resolve("out/archguard.sarif")));
    assertEquals("ERROR", Debt.JSON.readTree(r.out().strip()).get("status").asText());
    assertTrue(r.err().contains("not a policy pass"));
  }

  @Test
  void missingClassesIsAnAnalysisError() throws IOException {
    List<String> args = analysis("check");
    args.set(args.indexOf("--classes") + 1, dir.resolve("nope").toString());
    assertEquals(Main.ERROR, run(args).code());
  }

  @Test
  void classpathFileDefinesModules() throws IOException {
    Path file = dir.resolve("archguard.classpath");
    Files.writeString(
        file,
        "# test\nmodule=io.archguard:fixtures\nclasses=" + CLASSES + "\nsource=" + SOURCES + "\n");
    List<String> args =
        List.of(
            "check",
            "--project", PROJECT.toString(),
            "--config", policy(POLICY).toString(),
            "--out", dir.resolve("out").toString(),
            "--classpath-file", file.toString());
    assertEquals(Main.VIOLATION, run(args).code());
    assertEquals(
        "io.archguard:fixtures",
        findFirst(report().get("findings"), "HEX-002").get("location").get("module").asText());

    Files.writeString(file, "module=x\nclasses=" + CLASSES + "\nbogus=1\n");
    assertEquals(Main.ERROR, run(args).code());
    Files.writeString(file, "classes=" + CLASSES + "\n");
    assertEquals(Main.ERROR, run(args).code());
  }

  @Test
  void validateAndRules() throws IOException {
    Run v = run("", "validate", "--config", policy(POLICY).toString());
    assertEquals(Main.OK, v.code(), v.err());
    assertTrue(v.out().contains("policyHash"));
    assertEquals(Main.ERROR, run("", "validate", "--config", dir.resolve("missing.yml").toString()).code());

    Run rules = run("", "rules", "--json");
    assertEquals(Main.OK, rules.code());
    Set<String> ids = new HashSet<>();
    Debt.JSON.readTree(rules.out()).forEach(n -> ids.add(n.get("id").asText()));
    assertTrue(ids.containsAll(Set.of("HEX-002", "LAYER-001", "DDD-001", "FW-002")), ids.toString());
  }

  @Test
  void usageErrorsExitSixtyFour() {
    assertEquals(Main.USAGE, run("").code());
    assertEquals(Main.USAGE, run("", "frobnicate").code());
    assertEquals(Main.USAGE, run("", "check", "--nope").code());
    assertEquals(Main.USAGE, run("", "check", "--format", "xml").code());
    assertEquals(Main.USAGE, run("", "check", "--fail-on", "fatal").code());
    assertEquals(Main.USAGE, run("", "check", "--config").code());
    assertEquals(Main.OK, run("", "--help").code());
    assertTrue(run("", "--version").out().contains("spec 2.0.0"));
  }

  private static JsonNode findFirst(JsonNode findings, String rule) {
    for (JsonNode f : findings) if (rule.equals(f.get("ruleId").asText())) return f;
    throw new AssertionError(rule + " not found in " + findings);
  }
}
