package io.archguard.config;

import com.fasterxml.jackson.core.*;
import com.fasterxml.jackson.databind.*;
import com.fasterxml.jackson.dataformat.yaml.*;
import com.tngtech.archunit.core.domain.PackageMatcher;
import java.io.*;
import java.nio.file.*;
import java.util.*;

public final class Policies {
  private Policies() {}

  private static final ObjectMapper YAML =
      YAMLMapper.builder(
              YAMLFactory.builder().enable(StreamReadFeature.STRICT_DUPLICATE_DETECTION).build())
          .disable(MapperFeature.ALLOW_COERCION_OF_SCALARS)
          .enable(DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES)
          .enable(DeserializationFeature.FAIL_ON_TRAILING_TOKENS)
          .build();

  public static Policy read(Path path) throws IOException {
    if (Files.size(path) > 1_048_576) throw new IOException("Policy exceeds 1 MiB");
    JsonNode tree = YAML.readTree(path.toFile());
    rejectNulls(tree);
    Policy p = YAML.treeToValue(tree, Policy.class);
    validate(p);
    return p;
  }

  private static void rejectNulls(JsonNode node) {
    if (node == null || node.isNull())
      throw new IllegalArgumentException("Explicit null configuration values are not allowed");
    if (node.isContainerNode()) node.forEach(Policies::rejectNulls);
  }

  public static void validate(Policy p) {
    if (p == null || p.schemaVersion() != 1)
      throw new IllegalArgumentException("schemaVersion must be 1");
    if (p.roots().isEmpty())
      throw new IllegalArgumentException("At least one root package selector is required");
    if (!Set.of("hexagonal", "ddd").containsAll(p.profiles()))
      throw new IllegalArgumentException("Unknown architecture profile");
    if (p.roles().containsKey(io.archguard.api.Role.UNCLASSIFIED))
      throw new IllegalArgumentException("UNCLASSIFIED cannot be explicitly mapped");
    patterns(p.roots());
    p.roles().values().forEach(Policies::patterns);
    var ids = new HashSet<String>();
    for (var c : p.contexts()) {
      id(c.id());
      if (!ids.add(c.id())) throw new IllegalArgumentException("Duplicate context: " + c.id());
      patterns(c.packages());
      c.exposedPackages().forEach(Policies::pattern);
    }
    ids.clear();
    for (var c : p.constraints()) {
      id(c.id());
      if (!ids.add(c.id())) throw new IllegalArgumentException("Duplicate constraint: " + c.id());
      patterns(c.from());
      patterns(c.forbidden());
      if (c.remediation() == null
          || c.remediation().isBlank()
          || c.rationale() == null
          || c.rationale().isBlank())
        throw new IllegalArgumentException("Constraints require rationale and remediation");
    }
    p.rules()
        .forEach(
            (k, v) -> {
              id(k);
              Objects.requireNonNull(v, "Null rule setting");
            });
  }

  private static void id(String id) {
    if (id == null || !id.matches("[A-Za-z0-9][A-Za-z0-9_.-]{0,127}"))
      throw new IllegalArgumentException("Invalid identifier: " + id);
  }

  private static void patterns(List<String> patterns) {
    if (patterns.isEmpty()) throw new IllegalArgumentException("Empty selector list");
    patterns.forEach(Policies::pattern);
  }

  private static void pattern(String s) {
    if (s == null || s.isBlank() || s.length() > 512)
      throw new IllegalArgumentException("Invalid package selector");
    PackageMatcher.of(s);
  }

  public static boolean matches(List<String> patterns, String pkg) {
    return patterns.stream().anyMatch(p -> PackageMatcher.of(p).matches(pkg));
  }
}
