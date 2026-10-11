package io.archguard.engine;

import com.tngtech.archunit.core.domain.JavaClass;
import com.tngtech.archunit.core.importer.resolvers.ClassResolver;
import java.net.*;
import java.util.*;

/**
 * Reads resources from the supplied analysis classpath. Never loads application classes. The loader
 * is closed by ModelImporter and isolated per analysis thread.
 */
public final class AnalysisClassResolver implements ClassResolver {
  static final ThreadLocal<ClassLoader> LOADER = new ThreadLocal<>();
  private ClassUriImporter importer;

  public AnalysisClassResolver() {}

  @Override
  public void setClassUriImporter(ClassUriImporter importer) {
    this.importer = importer;
  }

  @Override
  public Optional<JavaClass> tryResolve(String typeName) {
    ClassLoader loader = LOADER.get();
    if (loader == null) throw new IllegalStateException("No analysis classpath scope");
    URL resource = loader.getResource(typeName.replace('.', '/') + ".class");
    if (resource == null) return Optional.empty();
    try {
      return importer.tryImport(resource.toURI());
    } catch (URISyntaxException e) {
      throw new IllegalStateException("Invalid class resource URI", e);
    }
  }
}
