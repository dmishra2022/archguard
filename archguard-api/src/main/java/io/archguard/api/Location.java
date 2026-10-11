package io.archguard.api;

/** Source paths are workspace-relative; line 0 means unavailable, never a fabricated line. */
public record Location(String module, String path, String symbol, int line) {
  public Location {
    if (module == null || path == null || symbol == null || line < 0)
      throw new IllegalArgumentException("Invalid location");
  }
}
