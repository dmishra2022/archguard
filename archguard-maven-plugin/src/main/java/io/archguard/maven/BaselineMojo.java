package io.archguard.maven;

import org.apache.maven.plugins.annotations.*;

/** Analyze all selected compiled modules. Invoke explicitly after compilation. */
@Mojo(
    name = "baseline",
    aggregator = true,
    requiresDependencyResolution = ResolutionScope.COMPILE_PLUS_RUNTIME,
    threadSafe = true)
public final class BaselineMojo extends AbstractArchitectureMojo {
  @Override
  protected boolean reactor() {
    return true;
  }

  @Override
  protected boolean enforce() {
    return false;
  }

  @Override
  protected boolean captureBaseline() {
    return true;
  }
}
