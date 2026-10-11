package io.archguard.maven;

import io.archguard.api.*;
import io.archguard.config.*;
import io.archguard.engine.*;
import io.archguard.report.Reports;
import java.io.*;
import java.nio.file.*;
import java.time.Clock;
import java.util.*;
import org.apache.maven.execution.MavenSession;
import org.apache.maven.plugin.*;
import org.apache.maven.plugin.MojoExecution;
import org.apache.maven.plugins.annotations.Parameter;
import org.apache.maven.project.MavenProject;

public abstract class AbstractArchitectureMojo extends AbstractMojo {
  @Parameter(defaultValue = "${project}", readonly = true, required = true)
  protected MavenProject project;

  @Parameter(defaultValue = "${session}", readonly = true, required = true)
  protected MavenSession session;

  @Parameter(defaultValue = "${mojoExecution}", readonly = true, required = true)
  protected MojoExecution execution;

  @Parameter(
      property = "archguard.config",
      defaultValue = "${maven.multiModuleProjectDirectory}/architecture.yml")
  protected File config;

  @Parameter(
      property = "archguard.outputDirectory",
      defaultValue = "${project.build.directory}/archguard")
  protected File outputDirectory;

  @Parameter(property = "archguard.baseline")
  protected File baseline;

  @Parameter(property = "archguard.suppressions")
  protected File suppressions;

  @Parameter(property = "archguard.skip", defaultValue = "false")
  protected boolean skip;

  @Parameter(property = "archguard.allowPartialReactor", defaultValue = "false")
  protected boolean allowPartialReactor;

  @Parameter(
      property = "archguard.baselineOutput",
      defaultValue = "${maven.multiModuleProjectDirectory}/architecture-baseline.json")
  protected File baselineOutput;

  @Parameter(property = "archguard.overwriteBaseline", defaultValue = "false")
  protected boolean overwriteBaseline;

  @Parameter protected List<String> excludedModules;

  protected abstract boolean reactor();

  protected abstract boolean enforce();

  protected boolean captureBaseline() {
    return false;
  }

  @Override
  public final void execute() throws MojoExecutionException, MojoFailureException {
    if (skip) {
      getLog().warn("ArchGuard explicitly skipped; no architecture verification performed");
      return;
    }
    if (!reactor() && "pom".equals(project.getPackaging())) {
      getLog().info("POM-only module: no local class analysis");
      return;
    }
    Path output = outputDirectory.toPath();
    try {
      if (reactor() && execution != null && execution.getLifecyclePhase() != null)
        throw new IllegalArgumentException(
            "Reactor goals must be invoked explicitly after compile/package, not bound to a parent"
                + " lifecycle phase");
      Policy policy = Policies.read(config.toPath());
      List<MavenProject> projects = reactor() ? session.getProjects() : List.of(project);
      if (reactor() && !allowPartialReactor) {
        if (session.getAllProjects().size() != projects.size())
          throw new IllegalArgumentException(
              "Partial reactor selected; use the full reactor or explicitly acknowledge"
                  + " archguard.allowPartialReactor=true");
        Set<Path> selected = new HashSet<>();
        projects.forEach(p -> selected.add(p.getBasedir().toPath().toAbsolutePath().normalize()));
        for (var p : projects)
          for (String module : p.getModules())
            if (!selected.contains(
                p.getBasedir().toPath().resolve(module).toAbsolutePath().normalize()))
              throw new IllegalArgumentException(
                  "A declared reactor module is not selected: " + module);
      }
      List<ModuleInput> inputs = new ArrayList<>();
      Set<Path> classpath = new LinkedHashSet<>();
      Set<String> owned = new HashSet<>();
      Path workspace =
          session
              .getRequest()
              .getMultiModuleProjectDirectory()
              .toPath()
              .toAbsolutePath()
              .normalize();
      for (var p : projects)
        if (!"pom".equals(p.getPackaging()) && !excluded(p)) {
          owned.add(p.getGroupId() + ":" + p.getArtifactId());
          inputs.add(
              new ModuleInput(
                  p.getGroupId() + ":" + p.getArtifactId(),
                  Path.of(p.getBuild().getOutputDirectory()),
                  p.getCompileSourceRoots().stream().map(Path::of).toList(),
                  workspace));
        }
      for (var p : projects)
        if (!excluded(p))
          for (var a : p.getArtifacts())
            if (!"test".equals(a.getScope())
                && !owned.contains(a.getGroupId() + ":" + a.getArtifactId())) {
              if (a.getFile() == null) throw new IOException("Unresolved artifact: " + a);
              if (a.getFile().isDirectory() || a.getFile().getName().endsWith(".jar"))
                classpath.add(a.getFile().toPath());
            }
      List<ArchitectureRule> custom = new ArrayList<>();
      ServiceLoader.load(ArchitectureRule.class, getClass().getClassLoader()).forEach(custom::add);
      AnalysisResult result =
          new ArchitectureEngine().analyze(inputs, new ArrayList<>(classpath), policy, custom);
      if (allowPartialReactor || excludedModules != null && !excludedModules.isEmpty()) {
        List<String> diagnostics = new ArrayList<>(result.diagnostics());
        diagnostics.add(
            "Explicit limited scope: allowPartialReactor="
                + allowPartialReactor
                + ", excludedModules="
                + excludedModules);
        result =
            new AnalysisResult(
                result.schemaVersion(),
                result.engineVersion(),
                result.policyHash(),
                result.analyzedClasses(),
                result.dependencies(),
                result.findings(),
                diagnostics);
      }
      if (captureBaseline()) {
        if (baselineOutput.exists() && !overwriteBaseline)
          throw new IOException(
              "Baseline already exists; review changes before setting"
                  + " archguard.overwriteBaseline=true");
        Debt.writeBaseline(baselineOutput.toPath(), result);
        getLog().info("Baseline written: " + baselineOutput);
      } else
        result =
            Debt.apply(
                result,
                baseline == null ? null : baseline.toPath(),
                suppressions == null ? null : suppressions.toPath(),
                Clock.systemUTC());
      Reports.write(output, result);
      getLog().info(Reports.console(result));
      getLog().info("Reports: " + output.toAbsolutePath());
      if (enforce() && result.fails(policy.failOn(), policy.newOnly()))
        throw new MojoFailureException(
            "Architecture policy violated. See " + output.resolve("index.html"));
    } catch (MojoFailureException e) {
      throw e;
    } catch (Exception | ServiceConfigurationError e) {
      try {
        writeFailure(output, e);
      } catch (IOException reporting) {
        e.addSuppressed(reporting);
      }
      throw new MojoExecutionException(
          "Architecture analysis failed (not a policy pass): " + e.getMessage(), e);
    }
  }

  private boolean excluded(MavenProject p) {
    return excludedModules != null
        && excludedModules.contains(p.getGroupId() + ":" + p.getArtifactId());
  }

  private void writeFailure(Path output, Throwable error) throws IOException {
    Reports.atomic(
        output.resolve("archguard.json"),
        Debt.JSON.writeValueAsBytes(
            Map.of(
                "schemaVersion",
                "1",
                "analysisStatus",
                "FAILED",
                "error",
                String.valueOf(error.getMessage()))));
    var notification =
        Map.of("level", "error", "message", Map.of("text", String.valueOf(error.getMessage())));
    var invocation =
        Map.of("executionSuccessful", false, "toolExecutionNotifications", List.of(notification));
    var run =
        Map.of(
            "tool",
            Map.of("driver", Map.of("name", "ArchGuard")),
            "invocations",
            List.of(invocation));
    Reports.atomic(
        output.resolve("archguard.sarif"),
        Debt.JSON.writeValueAsBytes(Map.of("version", "2.1.0", "runs", List.of(run))));
    Reports.atomic(
        output.resolve("index.html"),
        "<!doctype html><html lang=\"en\"><meta charset=\"utf-8\"><title>ArchGuard analysis failed</title><h1>Analysis failed</h1><p>No compliance result is available. See archguard.json and the Maven log for the error.</p></html>"
            .getBytes(java.nio.charset.StandardCharsets.UTF_8));
  }
}
