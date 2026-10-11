package io.archguard.maven;

import org.apache.maven.plugins.annotations.*;

/** Analyze all selected compiled modules. Invoke explicitly after compilation. */
@Mojo(
    name = "check-reactor",
    aggregator = true,
    requiresDependencyResolution = ResolutionScope.COMPILE_PLUS_RUNTIME,
    threadSafe = true)
public final class ReactorMojo extends AbstractArchitectureMojo {
  @Override
  protected boolean reactor() {
    return true;
  }

  @Override
  protected boolean enforce() {
    return true;
  }
}
