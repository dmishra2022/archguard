package io.archguard.cli;

import io.archguard.api.*;
import io.archguard.config.*;
import io.archguard.engine.*;
import io.archguard.report.Reports;
import io.archguard.spec.SpecCatalog;
import java.io.*;
import java.net.URL;
import java.net.URLClassLoader;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.time.Clock;
import java.util.*;

/** Build-tool-independent implementation of the shared command contract in spec/CLI.md. */
public final class Main {
  public static final int OK = 0;
  public static final int VIOLATION = 1;
  public static final int ERROR = 2;
  public static final int USAGE = 64;

  private static final Set<String> COMMANDS =
      Set.of("check", "analyze", "baseline", "validate", "rules");

  private final InputStream in;
  private final PrintStream out;
  private final PrintStream err;

  private Main(InputStream in, PrintStream out, PrintStream err) {
    this.in = in;
    this.out = out;
    this.err = err;
  }

  public static void main(String[] args) {
    System.exit(run(args, System.in, System.out, System.err));
  }

  public static int run(String[] args, InputStream in, PrintStream out, PrintStream err) {
    return new Main(in, out, err).execute(args);
  }

  private int execute(String[] args) {
    Options o;
    try {
      o = Options.parse(args);
    } catch (UsageException e) {
      err.println("archguard: " + e.getMessage());
      err.println(Options.USAGE);
      return USAGE;
    }
    if (o.help) {
      out.println(Options.USAGE);
      return OK;
    }
    if (o.version) {
      out.println(
          "archguard "
              + ArchitectureEngine.VERSION
              + " (java analyzer, spec "
              + SpecCatalog.get().specVersion()
              + ")");
      return OK;
    }
    return switch (o.command) {
      case "validate" -> validate(o);
      case "rules" -> rules(o);
      default -> analyze(o);
    };
  }

  private int validate(Options o) {
    try (var loader = extensions(o)) {
      Policy policy = Policies.read(o.config(), loader);
      out.println(
          "Policy valid: "
              + o.config()
              + " (schemaVersion "
              + policy.schemaVersion()
              + ", policyHash "
              + ArchitectureEngine.hash(policy)
              + ")");
      return OK;
    } catch (Exception | ServiceConfigurationError | LinkageError e) {
      err.println("Policy invalid: " + e.getMessage());
      return ERROR;
    }
  }

  private int rules(Options o) {
    try (var loader = extensions(o)) {
      var descriptors = new ArchitectureEngine().describe(customRules(loader));
      if (o.json) {
        List<Map<String, Object>> rows = new ArrayList<>();
        for (var d : descriptors) {
          Map<String, Object> row = new LinkedHashMap<>();
          row.put("id", d.id());
          row.put("title", d.title());
          row.put("defaultSeverity", d.defaultSeverity().name());
          row.put("helpUri", d.helpUri());
          row.put("tags", d.tags());
          rows.add(row);
        }
        out.println(Debt.JSON.writeValueAsString(rows));
      } else
        for (var d : descriptors)
          out.printf("%-10s %-8s %s%n", d.id(), d.defaultSeverity(), d.title());
      return OK;
    } catch (Exception | ServiceConfigurationError | LinkageError e) {
      err.println("Rule catalog unavailable: " + e.getMessage());
      return ERROR;
    }
  }

  private int analyze(Options o) {
    Path output = o.out();
    try (var loader = extensions(o)) {
      Policy policy = Policies.read(o.config(), loader);
      Inputs inputs = Inputs.resolve(o);
      AnalysisResult result =
          new ArchitectureEngine()
              .analyze(inputs.modules(), inputs.classpath(), policy, customRules(loader));
      if (o.command.equals("baseline")) {
        Path target = o.baselineOutput();
        if (Files.exists(target) && !o.overwriteBaseline)
          throw new IOException(
              "Baseline already exists; review changes before passing --overwrite-baseline: "
                  + target);
        Debt.writeBaseline(target, result);
        err.println("Baseline written: " + target);
      } else result = Debt.apply(result, o.baseline, o.suppressions, Clock.systemUTC());
      if (o.changedFiles != null) result = ChangedFiles.restrict(result, changedFiles(o), o.project);
      Severity gate = o.failOn != null ? o.failOn : policy.failOn();
      boolean failed = result.fails(gate, policy.newOnly());
      Reports.write(output, result, o.formats, failed);
      if (o.formats.contains("console")) out.println(Reports.console(result));
      if (o.formats.contains("agent")) out.print(Reports.agent(result, failed));
      err.println("Reports: " + output.toAbsolutePath());
      if (o.command.equals("check") && failed) {
        err.println("Architecture policy violated. See " + output.resolve("index.html"));
        return VIOLATION;
      }
      return OK;
    } catch (Exception | ServiceConfigurationError | LinkageError e) {
      try {
        Reports.writeFailure(output, e, o.formats);
      } catch (Exception reporting) {
        e.addSuppressed(reporting);
      }
      if (o.formats.contains("agent")) out.print(Reports.agentError(String.valueOf(e.getMessage())));
      err.println("Architecture analysis failed (not a policy pass): " + e.getMessage());
      return ERROR;
    }
  }

  private List<String> changedFiles(Options o) throws IOException {
    if (o.changedFiles.equals("-"))
      return new String(in.readAllBytes(), StandardCharsets.UTF_8).lines().toList();
    return Files.readAllLines(Path.of(o.changedFiles), StandardCharsets.UTF_8);
  }

  private static URLClassLoader extensions(Options o) throws IOException {
    List<URL> urls = new ArrayList<>();
    for (Path p : o.extensions) {
      if (!Files.exists(p)) throw new IOException("Extension not found: " + p);
      urls.add(p.toUri().toURL());
    }
    return new URLClassLoader(urls.toArray(URL[]::new), Main.class.getClassLoader());
  }

  private static List<ArchitectureRule> customRules(ClassLoader loader) {
    List<ArchitectureRule> rules = new ArrayList<>();
    ServiceLoader.load(ArchitectureRule.class, loader).forEach(rules::add);
    return rules;
  }

  static final class UsageException extends Exception {
    UsageException(String message) {
      super(message);
    }
  }

  static final class Options {
    static final String USAGE =
        """
        Usage: archguard <check|analyze|baseline|validate|rules> [options]

          check      Analyze, apply baseline and suppressions, write reports, gate (exit 1 on violation)
          analyze    Same analysis and reports, never fails on policy violations
          baseline   Write a baseline of current non-INFO findings
          validate   Validate the policy only (schema, semantics, extends resolution)
          rules      Print the rule catalog (--json for JSON)

        Shared options:
          --config <file>            Policy file (default <project>/architecture.yml)
          --project <dir>            Project root; report paths are relative to it (default .)
          --out <dir>                Report directory (default <project>/target/archguard)
          --format <list>            Subset of json,sarif,html,agent,console (default json,sarif,html)
          --baseline <file>          Reviewed baseline to apply
          --suppressions <file>      Reviewed suppressions to apply
          --changed-files <file|->   Report and gate only findings located in these project-relative files
          --baseline-output <file>   Destination for 'baseline' (default <project>/architecture-baseline.json)
          --overwrite-baseline       Allow replacing an existing baseline
          --fail-on <severity>       Override the policy failOn (INFO, WARNING, ERROR)

        Java options:
          --classes <dir>            Compiled classes of an analyzed module (repeatable)
          --source-root <dir>        Source root used to map classes to files (repeatable)
          --module-id <id>           Module id for --classes (default: project directory name)
          --classpath <path-list>    Dependency jars and directories
          --classpath-file <file>    File written by 'mvn archguard:classpath' (repeatable)
          --extension <jar|dir>      Rule packs (ArchitectureRule SPI) and org presets (repeatable)

        Exit codes: 0 pass, 1 policy violation, 2 analysis error (never a pass), 64 usage error.
        """;

    String command;
    boolean help;
    boolean version;
    boolean json;
    boolean overwriteBaseline;
    Path project = Path.of(".").toAbsolutePath().normalize();
    Path config;
    Path out;
    Path baseline;
    Path suppressions;
    Path baselineOutput;
    String changedFiles;
    Severity failOn;
    String moduleId;
    Set<String> formats = new LinkedHashSet<>(List.of("json", "sarif", "html"));
    final List<Path> classes = new ArrayList<>();
    final List<Path> sourceRoots = new ArrayList<>();
    final List<Path> classpath = new ArrayList<>();
    final List<Path> classpathFiles = new ArrayList<>();
    final List<Path> extensions = new ArrayList<>();

    Path config() {
      return config != null ? config : project.resolve("architecture.yml");
    }

    Path out() {
      return out != null ? out : project.resolve("target/archguard");
    }

    Path baselineOutput() {
      return baselineOutput != null ? baselineOutput : project.resolve("architecture-baseline.json");
    }

    static Options parse(String[] args) throws UsageException {
      Options o = new Options();
      Deque<String> rest = new ArrayDeque<>(Arrays.asList(args));
      while (!rest.isEmpty()) {
        String arg = rest.pop();
        String value = null;
        int eq = arg.indexOf('=');
        if (arg.startsWith("--") && eq > 0) {
          value = arg.substring(eq + 1);
          arg = arg.substring(0, eq);
        }
        switch (arg) {
          case "-h", "--help", "help" -> o.help = true;
          case "--version" -> o.version = true;
          case "--json" -> o.json = true;
          case "--overwrite-baseline" -> o.overwriteBaseline = true;
          case "--project" -> o.project = path(value(arg, value, rest)).toAbsolutePath().normalize();
          case "--config" -> o.config = path(value(arg, value, rest));
          case "--out" -> o.out = path(value(arg, value, rest));
          case "--baseline" -> o.baseline = path(value(arg, value, rest));
          case "--suppressions" -> o.suppressions = path(value(arg, value, rest));
          case "--baseline-output" -> o.baselineOutput = path(value(arg, value, rest));
          case "--changed-files" -> o.changedFiles = value(arg, value, rest);
          case "--module-id" -> o.moduleId = value(arg, value, rest);
          case "--fail-on" -> o.failOn = severity(value(arg, value, rest));
          case "--format" -> o.formats = formats(value(arg, value, rest));
          case "--classes" -> o.classes.add(path(value(arg, value, rest)));
          case "--source-root" -> o.sourceRoots.add(path(value(arg, value, rest)));
          case "--classpath" -> {
            for (String entry : value(arg, value, rest).split(File.pathSeparator))
              if (!entry.isBlank()) o.classpath.add(path(entry));
          }
          case "--classpath-file" -> o.classpathFiles.add(path(value(arg, value, rest)));
          case "--extension" -> o.extensions.add(path(value(arg, value, rest)));
          default -> {
            if (arg.startsWith("-")) throw new UsageException("Unknown option: " + arg);
            if (o.command != null) throw new UsageException("Unexpected argument: " + arg);
            if (!COMMANDS.contains(arg)) throw new UsageException("Unknown command: " + arg);
            o.command = arg;
          }
        }
      }
      if (o.command == null && !o.help && !o.version) throw new UsageException("Missing command");
      return o;
    }

    private static String value(String option, String inline, Deque<String> rest)
        throws UsageException {
      if (inline != null) {
        if (inline.isEmpty()) throw new UsageException("Empty value for " + option);
        return inline;
      }
      if (rest.isEmpty() || rest.peek().startsWith("--"))
        throw new UsageException("Missing value for " + option);
      return rest.pop();
    }

    private static Path path(String value) {
      return Path.of(value).toAbsolutePath().normalize();
    }

    private static Severity severity(String value) throws UsageException {
      try {
        return Severity.valueOf(value.toUpperCase(Locale.ROOT));
      } catch (IllegalArgumentException e) {
        throw new UsageException("Unknown severity: " + value);
      }
    }

    private static Set<String> formats(String value) throws UsageException {
      Set<String> result = new LinkedHashSet<>();
      for (String f : value.split(",")) {
        String format = f.trim().toLowerCase(Locale.ROOT);
        if (!Reports.FORMATS.contains(format)) throw new UsageException("Unknown format: " + f);
        result.add(format);
      }
      return result;
    }
  }
}
