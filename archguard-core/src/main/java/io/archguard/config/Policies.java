package io.archguard.config;

import com.fasterxml.jackson.core.*;
import com.fasterxml.jackson.databind.*;
import com.fasterxml.jackson.databind.node.*;
import com.fasterxml.jackson.dataformat.yaml.*;
import com.tngtech.archunit.core.domain.PackageMatcher;
import io.archguard.spec.SpecCatalog;
import java.io.*;
import java.nio.file.*;
import java.util.*;

public final class Policies {
  private Policies() {}

  public static final String LANGUAGE = "java";
  static final String PRESET_ROOT = "META-INF/archguard/presets/";
  private static final int MAX_BYTES = 1_048_576;
  private static final int MAX_DEPTH = 16;
  private static final Set<String> V2_KEYS =
      Set.of(
          "kind",
          "language",
          "extends",
          "sourceRoots",
          "typeOnlyImports",
          "unresolvedImports");

  private static final ObjectMapper YAML =
      YAMLMapper.builder(
              YAMLFactory.builder().enable(StreamReadFeature.STRICT_DUPLICATE_DETECTION).build())
          .disable(MapperFeature.ALLOW_COERCION_OF_SCALARS)
          .enable(DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES)
          .enable(DeserializationFeature.FAIL_ON_TRAILING_TOKENS)
          .build();

  public static Policy read(Path path) throws IOException {
    return read(path, Policies.class.getClassLoader());
  }

  /**
   * Reads a policy and resolves {@code extends}. {@code org:} and {@code classpath:} parents are
   * loaded from {@code loader}; for Maven, add preset artifacts as plugin dependencies.
   */
  public static Policy read(Path path, ClassLoader loader) throws IOException {
    JsonNode tree = resolve(Source.file(path), loader, new ArrayDeque<>());
    Policy p = YAML.treeToValue(tree, Policy.class);
    validate(p);
    return p;
  }

  private record Source(String label, Path file, String resource) {
    static Source file(Path path) {
      Path absolute = path.toAbsolutePath().normalize();
      return new Source(absolute.toString(), absolute, null);
    }

    static Source resource(String name) {
      return new Source("classpath:" + name, null, name);
    }

    Source relative(String reference) {
      if (file != null) return file(file.getParent().resolve(reference));
      String base = resource.contains("/") ? resource.substring(0, resource.lastIndexOf('/') + 1) : "";
      return resource(Path.of(base + reference).normalize().toString().replace('\\', '/'));
    }

    byte[] bytes(ClassLoader loader) throws IOException {
      if (file != null) {
        if (Files.size(file) > MAX_BYTES) throw new IOException("Policy exceeds 1 MiB: " + label);
        return Files.readAllBytes(file);
      }
      try (InputStream in = loader.getResourceAsStream(resource)) {
        if (in == null) throw new FileNotFoundException("Policy resource not found: " + label);
        byte[] bytes = in.readNBytes(MAX_BYTES + 1);
        if (bytes.length > MAX_BYTES) throw new IOException("Policy exceeds 1 MiB: " + label);
        return bytes;
      }
    }
  }

  private static Source parentSource(Source child, String reference) {
    if (reference.startsWith("org:")) {
      var m = java.util.regex.Pattern.compile("org:([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)@([0-9][A-Za-z0-9.+-]*)")
          .matcher(reference);
      if (!m.matches()) throw new IllegalArgumentException("Invalid preset reference: " + reference);
      return Source.resource(PRESET_ROOT + m.group(1) + "/" + m.group(2) + "/" + m.group(3) + ".yml");
    }
    if (reference.startsWith("classpath:")) return Source.resource(reference.substring(10));
    if (reference.startsWith("/")) return Source.file(Path.of(reference));
    if (reference.startsWith("./") || reference.startsWith("../")) return child.relative(reference);
    throw new IllegalArgumentException("Invalid extends reference: " + reference);
  }

  private static ObjectNode resolve(Source source, ClassLoader loader, Deque<String> chain)
      throws IOException {
    if (chain.contains(source.label()))
      throw new IllegalArgumentException("Cyclic policy extends: " + chain + " -> " + source.label());
    if (chain.size() >= MAX_DEPTH) throw new IllegalArgumentException("Policy extends too deep");
    JsonNode parsed;
    try {
      parsed = YAML.readTree(source.bytes(loader));
    } catch (FileNotFoundException e) {
      if (source.resource() != null && source.resource().startsWith(PRESET_ROOT))
        throw new FileNotFoundException(
            "Policy preset not found on the analyzer classpath: "
                + source.resource()
                + ". Add the preset artifact (for Maven: as a plugin dependency).");
      throw e;
    }
    rejectNulls(parsed);
    if (!(parsed instanceof ObjectNode tree))
      throw new IllegalArgumentException("Policy must be a mapping: " + source.label());
    int version = tree.path("schemaVersion").asInt(-1);
    if (version == 1)
      for (String key : V2_KEYS)
        if (tree.has(key))
          throw new IllegalArgumentException("'" + key + "' requires schemaVersion 2");
    if (!tree.has("extends")) return tree;
    chain.push(source.label());
    try {
      ObjectNode inherited = JsonNodeFactory.instance.objectNode();
      for (JsonNode reference : tree.path("extends")) {
        ObjectNode parent = resolve(parentSource(source, reference.asText()), loader, chain);
        if (parent.path("schemaVersion").asInt() != 2
            || !Policy.KIND_PRESET.equals(parent.path("kind").asText()))
          throw new IllegalArgumentException(
              "Extended policy must be schemaVersion 2 with kind: preset: " + reference.asText());
        if (tree.has("language")
            && parent.has("language")
            && !tree.path("language").equals(parent.path("language")))
          throw new IllegalArgumentException("Extended preset language differs: " + reference.asText());
        rejectLockedChanges(inherited, parent, reference.asText());
        inherited = merge(inherited, parent);
      }
      rejectLockedChanges(inherited, tree, source.label());
      ObjectNode merged = merge(inherited, tree);
      merged.remove("kind");
      if (tree.has("kind")) merged.set("kind", tree.get("kind"));
      merged.set("extends", tree.get("extends"));
      return merged;
    } finally {
      chain.pop();
    }
  }

  /** Maps merge by key, lists of objects with an id merge by id, everything else is replaced. */
  static ObjectNode merge(ObjectNode parent, ObjectNode child) {
    ObjectNode out = parent.deepCopy();
    child
        .fields()
        .forEachRemaining(
            e -> {
              JsonNode existing = out.get(e.getKey());
              JsonNode value = e.getValue();
              if (existing instanceof ObjectNode a && value instanceof ObjectNode b)
                out.set(e.getKey(), merge(a, b));
              else if (existing instanceof ArrayNode a && value instanceof ArrayNode b && byId(a) && byId(b))
                out.set(e.getKey(), mergeById(a, b));
              else out.set(e.getKey(), value.deepCopy());
            });
    return out;
  }

  private static boolean byId(ArrayNode array) {
    for (JsonNode n : array) if (!n.isObject() || !n.path("id").isTextual()) return false;
    return !array.isEmpty();
  }

  private static ArrayNode mergeById(ArrayNode parent, ArrayNode child) {
    Map<String, JsonNode> entries = new LinkedHashMap<>();
    parent.forEach(n -> entries.put(n.path("id").asText(), n.deepCopy()));
    child.forEach(n -> entries.put(n.path("id").asText(), n.deepCopy()));
    ArrayNode out = JsonNodeFactory.instance.arrayNode();
    entries.values().forEach(out::add);
    return out;
  }

  private static void rejectLockedChanges(ObjectNode inherited, ObjectNode child, String label) {
    inherited
        .path("rules")
        .fields()
        .forEachRemaining(
            e -> {
              if (!e.getValue().path("locked").asBoolean(false)) return;
              JsonNode mine = child.path("rules").path(e.getKey());
              if (mine.isMissingNode()) return;
              for (String key : List.of("enabled", "severity", "locked"))
                if (mine.has(key) && !mine.get(key).equals(e.getValue().get(key)))
                  throw new IllegalArgumentException(
                      "Rule " + e.getKey() + " is locked by an extended preset; " + label
                          + " cannot change '" + key + "'");
            });
  }

  private static void rejectNulls(JsonNode node) {
    if (node == null || node.isNull())
      throw new IllegalArgumentException("Explicit null configuration values are not allowed");
    if (node.isContainerNode()) node.forEach(Policies::rejectNulls);
  }

  public static void validate(Policy p) {
    if (p == null || (p.schemaVersion() != 1 && p.schemaVersion() != 2))
      throw new IllegalArgumentException("schemaVersion must be 1 or 2");
    if (p.schemaVersion() == 1) {
      if (p.kind() != null
          || p.language() != null
          || !p.parents().isEmpty()
          || !p.sourceRoots().isEmpty()
          || p.typeOnlyImports() != null
          || p.unresolvedImports() != null
          || p.rules().values().stream().anyMatch(r -> r != null && r.locked() != null))
        throw new IllegalArgumentException("schemaVersion 2 settings used with schemaVersion 1");
      if (!Set.of("hexagonal", "ddd").containsAll(p.profiles()))
        throw new IllegalArgumentException("Unknown architecture profile");
    } else {
      if (p.kind() != null && !Set.of(Policy.KIND_PROJECT, Policy.KIND_PRESET).contains(p.kind()))
        throw new IllegalArgumentException("kind must be project or preset");
      if (p.preset())
        throw new IllegalArgumentException(
            "A preset policy cannot be analyzed directly; extend it from a project policy");
      if (p.language() == null)
        throw new IllegalArgumentException("schemaVersion 2 requires language");
      if (!LANGUAGE.equals(p.language()))
        throw new IllegalArgumentException(
            "Policy language '" + p.language() + "' cannot be analyzed by the Java analyzer");
      if (p.typeOnlyImports() != null && !Set.of("count", "ignore").contains(p.typeOnlyImports()))
        throw new IllegalArgumentException("typeOnlyImports must be count or ignore");
      if (p.unresolvedImports() != null && !Set.of("fail", "warn").contains(p.unresolvedImports()))
        throw new IllegalArgumentException("unresolvedImports must be fail or warn");
      var known = SpecCatalog.get().profiles().keySet();
      for (String profile : p.profiles())
        if (!known.contains(profile))
          throw new IllegalArgumentException("Unknown architecture profile: " + profile);
    }
    if (p.roots().isEmpty())
      throw new IllegalArgumentException("At least one root package selector is required");
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
    if (s == null || s.isBlank() || s.length() > 512 || s.contains("/"))
      throw new IllegalArgumentException("Invalid package selector");
    PackageMatcher.of(toArchUnit(s));
  }

  /** Converts the neutral glob syntax ({@code a.**}, {@code **.b.**}) to ArchUnit's {@code ..}. */
  public static String toArchUnit(String selector) {
    if (!selector.contains("**")) return selector;
    if (selector.equals("**")) return "..";
    String s = selector.replace(".**.", "..");
    if (s.startsWith("**.")) s = ".." + s.substring(3);
    if (s.endsWith(".**")) s = s.substring(0, s.length() - 3) + "..";
    if (s.contains("**")) throw new IllegalArgumentException("Invalid selector: " + selector);
    return s;
  }

  public static boolean matches(List<String> patterns, String pkg) {
    return patterns.stream().anyMatch(p -> PackageMatcher.of(toArchUnit(p)).matches(pkg));
  }
}
