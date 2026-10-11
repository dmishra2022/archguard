package io.archguard.engine;

import java.nio.file.Path;
import java.util.List;

public record ModuleInput(String id, Path classes, List<Path> sourceRoots, Path workspaceRoot) {
  public ModuleInput {
    if (id == null || id.isBlank()) throw new IllegalArgumentException("Module ID is required");
    classes = classes.toAbsolutePath().normalize();
    sourceRoots = List.copyOf(sourceRoots);
    workspaceRoot = workspaceRoot.toAbsolutePath().normalize();
  }
}
