package io.archguard.cli;

import io.archguard.engine.ModuleInput;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.*;

/**
 * Analyzed modules and dependency classpath, from command-line options and classpath files.
 *
 * <p>Classpath file format (written by {@code mvn archguard:classpath}): UTF-8 {@code key=value}
 * lines; {@code #} comments. {@code module=<id>} starts a module, followed by its {@code
 * classes=<dir>} and any {@code source=<dir>} lines. {@code classpath=<jar or dir>} lines add
 * dependencies. Relative paths resolve against the file's directory.
 */
record Inputs(List<ModuleInput> modules, List<Path> classpath) {
  static Inputs resolve(Main.Options o) throws IOException {
    Path workspace = real(o.project);
    List<ModuleInput> modules = new ArrayList<>();
    Set<Path> classpath = new LinkedHashSet<>();
    for (Path file : o.classpathFiles) read(file, workspace, modules, classpath);
    List<Path> classes = new ArrayList<>(o.classes.stream().map(Inputs::real).toList());
    List<Path> sources = new ArrayList<>(o.sourceRoots.stream().map(Inputs::real).toList());
    if (classes.isEmpty() && o.classpathFiles.isEmpty()) {
      Path defaultClasses = workspace.resolve("target/classes");
      if (!Files.isDirectory(defaultClasses))
        throw new IllegalArgumentException(
            "No compiled classes found at "
                + defaultClasses
                + "; compile first or pass --classes / --classpath-file");
      classes.add(defaultClasses);
      if (sources.isEmpty() && Files.isDirectory(workspace.resolve("src/main/java")))
        sources.add(workspace.resolve("src/main/java"));
    }
    for (Path dir : classes) {
      if (!Files.isDirectory(dir))
        throw new IllegalArgumentException("Classes directory not found: " + dir);
      String id =
          classes.size() == 1
              ? Objects.requireNonNullElse(o.moduleId, name(workspace))
              : workspace.relativize(dir).toString().replace('\\', '/');
      modules.add(new ModuleInput(id, dir, sources, workspace));
    }
    for (Path entry : o.classpath) classpath.add(dependency(real(entry)));
    for (ModuleInput m : modules) classpath.remove(m.classes());
    Set<String> ids = new HashSet<>();
    for (ModuleInput m : modules)
      if (!ids.add(m.id())) throw new IllegalArgumentException("Duplicate module id: " + m.id());
    return new Inputs(modules, new ArrayList<>(classpath));
  }

  private static void read(
      Path file, Path workspace, List<ModuleInput> modules, Set<Path> classpath)
      throws IOException {
    if (!Files.isRegularFile(file)) throw new IOException("Classpath file not found: " + file);
    Path base = file.toAbsolutePath().getParent();
    String id = null;
    Path classes = null;
    List<Path> sources = new ArrayList<>();
    int n = 0;
    for (String raw : Files.readAllLines(file, StandardCharsets.UTF_8)) {
      n++;
      String line = raw.strip();
      if (line.isEmpty() || line.startsWith("#")) continue;
      int eq = line.indexOf('=');
      if (eq <= 0) throw new IOException(file + ":" + n + ": expected key=value");
      String key = line.substring(0, eq);
      String value = line.substring(eq + 1);
      Path path = key.equals("module") ? null : real(base.resolve(value).normalize());
      switch (key) {
        case "module" -> {
          if (id != null) modules.add(module(file, id, classes, sources, workspace));
          id = value;
          classes = null;
          sources = new ArrayList<>();
        }
        case "classes" -> {
          if (id == null || classes != null)
            throw new IOException(file + ":" + n + ": 'classes' must follow exactly one 'module'");
          classes = path;
        }
        case "source" -> {
          if (id == null) throw new IOException(file + ":" + n + ": 'source' before 'module'");
          sources.add(path);
        }
        case "classpath" -> classpath.add(dependency(path));
        default -> throw new IOException(file + ":" + n + ": unknown key '" + key + "'");
      }
    }
    if (id != null) modules.add(module(file, id, classes, sources, workspace));
  }

  private static ModuleInput module(
      Path file, String id, Path classes, List<Path> sources, Path workspace) throws IOException {
    if (classes == null) throw new IOException(file + ": module '" + id + "' has no 'classes'");
    if (!Files.isDirectory(classes))
      throw new IOException("Classes directory not found for module " + id + ": " + classes);
    return new ModuleInput(id, classes, sources, workspace);
  }

  private static Path dependency(Path entry) throws IOException {
    if (Files.isDirectory(entry) || entry.getFileName().toString().endsWith(".jar")) {
      if (!Files.exists(entry)) throw new IOException("Unresolved classpath entry: " + entry);
      return entry;
    }
    throw new IOException("Classpath entry is neither a directory nor a jar: " + entry);
  }

  /** Canonical form, so source files under symlinked directories still map into the project. */
  static Path real(Path path) {
    try {
      return Files.exists(path) ? path.toRealPath() : path.toAbsolutePath().normalize();
    } catch (IOException e) {
      return path.toAbsolutePath().normalize();
    }
  }

  private static String name(Path workspace) {
    Path name = workspace.getFileName();
    return name == null ? "root" : name.toString();
  }
}
