package io.archguard.engine;

import com.tngtech.archunit.ArchConfiguration;
import com.tngtech.archunit.core.domain.*;
import com.tngtech.archunit.core.importer.ClassFileImporter;
import io.archguard.api.*;
import io.archguard.config.*;
import io.archguard.framework.FrameworkClassifier;
import java.io.*;
import java.net.URL;
import java.net.URLClassLoader;
import java.nio.file.*;
import java.util.*;
import java.util.stream.*;

public final class ModelImporter {
  public ArchitectureModel read(List<ModuleInput> modules, List<Path> classpath, Policy policy)
      throws IOException {
    Policies.validate(policy);
    Map<String, ModuleInput> ownership = new HashMap<>();
    Set<String> ids = new HashSet<>();
    List<Path> paths = new ArrayList<>();
    for (ModuleInput module : modules) {
      if (!ids.add(module.id()))
        throw new IllegalArgumentException("Duplicate module ID: " + module.id());
      if (!Files.isDirectory(module.classes()))
        throw new IOException(
            "Missing compiled output: "
                + module.classes()
                + ". Compile all selected modules first.");
      paths.add(module.classes());
      try (var files = Files.walk(module.classes())) {
        for (Path file : files.filter(p -> p.toString().endsWith(".class")).sorted().toList()) {
          String name =
              module
                  .classes()
                  .relativize(file)
                  .toString()
                  .replace(File.separatorChar, '.')
                  .replaceAll("\\.class$", "");
          if (name.equals("module-info") || name.endsWith("package-info")) continue;
          var previous = ownership.putIfAbsent(name, module);
          if (previous != null)
            throw new IOException(
                "Duplicate class " + name + " in " + previous.id() + " and " + module.id());
        }
      }
    }
    for (Path p : classpath) {
      if (!Files.exists(p)) throw new IOException("Missing analysis classpath entry: " + p);
    }
    // Explicit dependency inputs avoid relying on the plugin's unrelated classloader.
    var resolutionPaths = new LinkedHashSet<Path>(paths);
    resolutionPaths.addAll(classpath);
    List<URL> urls = new ArrayList<>();
    for (Path p : resolutionPaths) urls.add(p.toUri().toURL());
    JavaClasses imported;
    ClassLoader previous = AnalysisClassResolver.LOADER.get();
    try (URLClassLoader loader =
        new URLClassLoader(urls.toArray(URL[]::new), ClassLoader.getPlatformClassLoader())) {
      AnalysisClassResolver.LOADER.set(loader);
      imported =
          ArchConfiguration.withThreadLocalScope(
              configuration -> {
                configuration.setClassResolver(AnalysisClassResolver.class);
                return new ClassFileImporter().importPaths(paths.stream().distinct().toList());
              });
    } finally {
      if (previous == null) AnalysisClassResolver.LOADER.remove();
      else AnalysisClassResolver.LOADER.set(previous);
    }

    Map<String, TypeInfo> types = new TreeMap<>();
    List<String> diagnostics = new ArrayList<>();
    for (JavaClass c : imported) {
      ModuleInput module = ownership.get(c.getName());
      if (module == null || !Policies.matches(policy.roots(), c.getPackageName())) continue;
      List<Role> roles =
          policy.roles().entrySet().stream()
              .filter(e -> Policies.matches(e.getValue(), c.getPackageName()))
              .map(Map.Entry::getKey)
              .toList();
      if (roles.size() > 1)
        throw new IllegalArgumentException(
            "Ambiguous role mapping for " + c.getName() + ": " + roles);
      var contexts =
          policy.contexts().stream()
              .filter(ctx -> Policies.matches(ctx.packages(), c.getPackageName()))
              .toList();
      if (contexts.size() > 1)
        throw new IllegalArgumentException("Ambiguous context mapping for " + c.getName());
      Role role = roles.isEmpty() ? Role.UNCLASSIFIED : roles.get(0);
      String source = sourcePath(c, module);
      Set<String> annotations =
          c.getAnnotations().stream()
              .map(a -> a.getRawType().getName())
              .collect(Collectors.toCollection(TreeSet::new));
      types.put(
          c.getName(),
          new TypeInfo(
              c.getName(),
              c.getPackageName(),
              role,
              contexts.isEmpty() ? "" : contexts.get(0).id(),
              annotations,
              FrameworkClassifier.tags(c),
              c.isInterface(),
              new Location(module.id(), source, c.getName(), 0)));
    }
    for (String name : ownership.keySet()) {
      int dot = name.lastIndexOf('.');
      String pkg = dot < 0 ? "" : name.substring(0, dot);
      if (Policies.matches(policy.roots(), pkg) && !types.containsKey(name))
        throw new IOException("Compiled class could not be imported: " + name);
    }
    if (types.isEmpty() && !policy.allowEmptyAnalysis())
      throw new IllegalArgumentException(
          "No application classes matched roots; refusing a vacuous pass");
    if (!policy.allowEmptySelectors()) {
      for (var e : policy.roles().entrySet())
        requireMatch(types, e.getValue(), "role " + e.getKey());
      for (var c : policy.contexts()) requireMatch(types, c.packages(), "context " + c.id());
      for (var c : policy.constraints()) requireMatch(types, c.from(), "constraint " + c.id());
    }
    List<io.archguard.api.Dependency> dependencies = new ArrayList<>();
    for (JavaClass c : imported) {
      var origin = types.get(c.getName());
      if (origin == null) continue;
      if (origin.frameworkTags().contains("spring.endpoint")
          || origin.frameworkTags().contains("jaxrs.endpoint")
          || origin.frameworkTags().contains("micronaut.endpoint")) {
        for (var method : c.getMethods()) {
          boolean endpoint =
              method.isAnnotatedWith("org.springframework.web.bind.annotation.RequestMapping")
                  || method.isMetaAnnotatedWith(
                      "org.springframework.web.bind.annotation.RequestMapping")
                  || method.isMetaAnnotatedWith("jakarta.ws.rs.HttpMethod")
                  || method.isMetaAnnotatedWith("javax.ws.rs.HttpMethod")
                  || isMicronautHttpMethod(method);
          if (!endpoint) continue;
          Set<JavaClass> exposed = new HashSet<>(method.getReturnType().getAllInvolvedRawTypes());
          method.getParameterTypes().forEach(t -> exposed.addAll(t.getAllInvolvedRawTypes()));
          for (JavaClass target : exposed)
            if (FrameworkClassifier.tags(target).contains("persistence.entity")) {
              var loc =
                  new Location(
                      origin.location().module(),
                      origin.location().path(),
                      method.getFullName(),
                      Math.max(0, method.getSourceCodeLocation().getLineNumber()));
              dependencies.add(
                  new io.archguard.api.Dependency(
                      c.getName(),
                      target.getName(),
                      "HTTP method <"
                          + method.getFullName()
                          + "> exposes persistence entity <"
                          + target.getName()
                          + ">",
                      loc,
                      io.archguard.api.Dependency.Kind.HTTP_ENTITY_EXPOSURE));
            }
        }
      }
      for (var d : c.getDirectDependenciesFromSelf()) {
        if (!d.getTargetClass().isPrimitive()
            && !d.getTargetClass().isArray()
            && !d.getTargetClass().isFullyImported()) {
          throw new IOException(
              "Unresolved direct application dependency: "
                  + c.getName()
                  + " -> "
                  + d.getTargetClass().getName()
                  + ". Supply its bytecode on the analysis classpath.");
        }
        var loc =
            new Location(
                origin.location().module(),
                origin.location().path(),
                c.getName(),
                Math.max(0, d.getSourceCodeLocation().getLineNumber()));
        dependencies.add(
            new io.archguard.api.Dependency(
                c.getName(), d.getTargetClass().getName(), d.getDescription(), loc));
      }
    }
    dependencies.sort(
        Comparator.comparing(io.archguard.api.Dependency::origin)
            .thenComparing(io.archguard.api.Dependency::target)
            .thenComparing(io.archguard.api.Dependency::evidence));
    diagnostics.add(
        "Static dependencies only: reflection, dynamic DI, profiles and runtime paths are not"
            + " resolved.");
    diagnostics.add(
        "Dependency metadata is resolved on demand from the explicit classpath; only owned"
            + " root-matched classes are evaluated.");
    long unclassified = types.values().stream().filter(t -> t.role() == Role.UNCLASSIFIED).count();
    diagnostics.add("Unclassified application classes: " + unclassified + " / " + types.size());
    if (types.values().stream().anyMatch(t -> t.location().path().isEmpty()))
      diagnostics.add(
          "Some source files are unavailable; those findings have symbol-only locations.");
    return new ArchitectureModel(types, dependencies, diagnostics);
  }

  private static void requireMatch(
      Map<String, TypeInfo> types, List<String> patterns, String label) {
    if (types.values().stream().noneMatch(t -> Policies.matches(patterns, t.packageName())))
      throw new IllegalArgumentException("Empty selector for " + label);
  }

  /**
   * Recognises Micronaut HTTP routing annotations. Micronaut models the HTTP method binding through
   * {@code @AliasFor(annotation = HttpMethodMapping.class)} rather than a direct meta-annotation,
   * so a direct annotation check against the known routing types is the deterministic signal.
   */
  private static boolean isMicronautHttpMethod(com.tngtech.archunit.core.domain.JavaMethod method) {
    return method.isAnnotatedWith("io.micronaut.http.annotation.Get")
        || method.isAnnotatedWith("io.micronaut.http.annotation.Post")
        || method.isAnnotatedWith("io.micronaut.http.annotation.Put")
        || method.isAnnotatedWith("io.micronaut.http.annotation.Delete")
        || method.isAnnotatedWith("io.micronaut.http.annotation.Patch")
        || method.isAnnotatedWith("io.micronaut.http.annotation.Options")
        || method.isAnnotatedWith("io.micronaut.http.annotation.Head")
        || method.isAnnotatedWith("io.micronaut.http.annotation.Trace")
        || method.isAnnotatedWith("io.micronaut.http.annotation.CustomHttpMethod")
        || method.isAnnotatedWith("io.micronaut.http.annotation.UriMapping");
  }

  private static String sourcePath(JavaClass c, ModuleInput m) {
    String simple =
        c.getName()
                .substring(c.getPackageName().isEmpty() ? 0 : c.getPackageName().length() + 1)
                .split("\\$")[0]
            + ".java";
    Path relative = Path.of(c.getPackageName().replace('.', '/')).resolve(simple);
    for (Path root : m.sourceRoots())
      if (Files.isRegularFile(root.resolve(relative))) {
        Path file = root.resolve(relative).toAbsolutePath().normalize();
        if (file.startsWith(m.workspaceRoot()))
          return m.workspaceRoot().relativize(file).toString().replace(File.separatorChar, '/');
      }
    return "";
  }
}
