package io.archguard.maven;

import org.apache.maven.plugins.annotations.*;

/** Analyze the current compiled module. */
@Mojo(
    name = "check",
    defaultPhase = LifecyclePhase.VERIFY,
    requiresDependencyResolution = ResolutionScope.COMPILE_PLUS_RUNTIME,
    threadSafe = true)
public final class CheckMojo extends AbstractArchitectureMojo {
  @Override
  protected boolean reactor() {
    return false;
  }

  @Override
  protected boolean enforce() {
    return true;
  }
}
