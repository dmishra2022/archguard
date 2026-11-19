package io.archguard.maven;

import io.archguard.report.Reports;
import java.io.File;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import org.apache.maven.plugin.AbstractMojo;
import org.apache.maven.plugin.MojoExecutionException;
import org.apache.maven.plugins.annotations.*;
import org.apache.maven.project.MavenProject;

/**
 * Write the module's compiled classes, source roots and resolved dependencies to a classpath file
 * for {@code archguard check --classpath-file}. Invoke after compilation.
 */
@Mojo(
    name = "classpath",
    requiresDependencyResolution = ResolutionScope.COMPILE_PLUS_RUNTIME,
    threadSafe = true)
public final class ClasspathMojo extends AbstractMojo {
  @Parameter(defaultValue = "${project}", readonly = true, required = true)
  private MavenProject project;

  @Parameter(
      property = "archguard.classpathFile",
      defaultValue = "${project.build.directory}/archguard.classpath")
  private File classpathFile;

  @Override
  public void execute() throws MojoExecutionException {
    if ("pom".equals(project.getPackaging())) {
      getLog().info("POM-only module: no classpath file");
      return;
    }
    StringBuilder s = new StringBuilder("# ArchGuard classpath file v1\n");
    s.append("module=").append(project.getGroupId()).append(':').append(project.getArtifactId());
    s.append("\nclasses=").append(project.getBuild().getOutputDirectory()).append('\n');
    for (String root : project.getCompileSourceRoots()) s.append("source=").append(root).append('\n');
    for (var a : project.getArtifacts())
      if (!"test".equals(a.getScope())) {
        if (a.getFile() == null)
          throw new MojoExecutionException("Unresolved artifact: " + a);
        if (a.getFile().isDirectory() || a.getFile().getName().endsWith(".jar"))
          s.append("classpath=").append(a.getFile().getAbsolutePath()).append('\n');
      }
    try {
      Reports.atomic(classpathFile.toPath(), s.toString().getBytes(StandardCharsets.UTF_8));
    } catch (IOException e) {
      throw new MojoExecutionException("Cannot write " + classpathFile, e);
    }
    getLog().info("ArchGuard classpath file: " + classpathFile);
  }
}
