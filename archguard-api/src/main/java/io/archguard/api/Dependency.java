package io.archguard.api;

/** Direct static dependency. Does not assert runtime reachability or DI resolution. */
public record Dependency(
    String origin, String target, String evidence, Location location, Kind kind) {
  public enum Kind {
    STATIC,
    HTTP_ENTITY_EXPOSURE
  }

  public Dependency(String origin, String target, String evidence, Location location) {
    this(origin, target, evidence, location, Kind.STATIC);
  }
}
