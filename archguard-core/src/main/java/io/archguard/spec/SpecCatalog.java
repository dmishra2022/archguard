package io.archguard.spec;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.dataformat.yaml.YAMLMapper;
import io.archguard.api.*;
import java.io.*;
import java.util.*;

/**
 * The ArchGuard spec catalog (profiles, rules, infrastructure lists) bundled under {@code
 * META-INF/archguard/spec/}. Loaded once; immutable.
 */
public final class SpecCatalog {
  public static final String RESOURCE_ROOT = "META-INF/archguard/spec/";

  public record RoleRule(
      String rule,
      Set<Role> from,
      Set<Role> forbiddenRoles,
      boolean forbidInfrastructure,
      boolean crossRoleOnly) {
    public boolean forbids(Role origin, Role target, boolean infrastructureTarget) {
      if (!from.contains(origin)) return false;
      boolean role = forbiddenRoles.contains(target) && !(crossRoleOnly && origin == target);
      return role || (forbidInfrastructure && infrastructureTarget);
    }
  }

  public record Profile(
      String id,
      String title,
      String description,
      List<String> includes,
      Set<String> activates,
      List<RoleRule> roleRules) {}

  public record RuleSpec(
      String id,
      String title,
      String category,
      Severity defaultSeverity,
      String activation,
      String message,
      String evidence,
      String remediation,
      String rationale,
      Set<String> languages) {
    public String message(Map<String, String> values) {
      return fill(message, values);
    }

    public String evidence(Map<String, String> values) {
      return fill(evidence, values);
    }

    public String remediation(Map<String, String> values) {
      return fill(remediation, values);
    }

    public RuleDescriptor descriptor() {
      return new RuleDescriptor(id, title, defaultSeverity, "", Set.of(category));
    }

    private static String fill(String template, Map<String, String> values) {
      if (template == null) return "";
      String out = template;
      for (var e : values.entrySet()) out = out.replace("{" + e.getKey() + "}", e.getValue());
      return out;
    }
  }

  private static volatile SpecCatalog instance;

  private final String specVersion;
  private final Map<String, Profile> profiles;
  private final Map<String, RuleSpec> rules;
  private final Map<String, List<String>> infrastructure;
  private final List<RoleRule> roleRules;

  private SpecCatalog(
      String specVersion,
      Map<String, Profile> profiles,
      Map<String, RuleSpec> rules,
      Map<String, List<String>> infrastructure) {
    this.specVersion = specVersion;
    this.profiles = Collections.unmodifiableMap(profiles);
    this.rules = Collections.unmodifiableMap(rules);
    this.infrastructure = Collections.unmodifiableMap(infrastructure);
    List<RoleRule> all = new ArrayList<>();
    profiles.values().forEach(p -> all.addAll(p.roleRules()));
    this.roleRules = List.copyOf(all);
  }

  public static SpecCatalog get() {
    SpecCatalog local = instance;
    if (local == null) {
      synchronized (SpecCatalog.class) {
        local = instance;
        if (local == null) instance = local = load(SpecCatalog.class.getClassLoader());
      }
    }
    return local;
  }

  static SpecCatalog load(ClassLoader loader) {
    try {
      JsonNode index = read(loader, "index.yml");
      Map<String, Profile> profiles = new TreeMap<>();
      for (JsonNode id : index.path("profiles")) {
        JsonNode p = read(loader, "profiles/" + id.asText() + ".yml");
        List<RoleRule> roleRules = new ArrayList<>();
        for (JsonNode r : p.path("roleRules"))
          roleRules.add(
              new RoleRule(
                  r.path("rule").asText(),
                  roles(r.path("from")),
                  roles(r.path("forbiddenRoles")),
                  r.path("forbidInfrastructure").asBoolean(false),
                  r.path("crossRoleOnly").asBoolean(false)));
        profiles.put(
            id.asText(),
            new Profile(
                p.path("id").asText(),
                p.path("title").asText(),
                p.path("description").asText(),
                strings(p.path("includes")),
                new TreeSet<>(strings(p.path("activates"))),
                List.copyOf(roleRules)));
      }
      Map<String, RuleSpec> rules = new TreeMap<>();
      for (JsonNode id : index.path("rules")) {
        JsonNode r = read(loader, "rules/" + id.asText() + ".yml");
        rules.put(
            id.asText(),
            new RuleSpec(
                r.path("id").asText(),
                r.path("title").asText(),
                r.path("category").asText(),
                Severity.valueOf(r.path("defaultSeverity").asText()),
                r.path("activation").asText(),
                r.path("message").asText(),
                r.hasNonNull("evidence") ? r.path("evidence").asText() : null,
                r.path("remediation").asText(),
                r.path("rationale").asText(),
                new TreeSet<>(strings(r.path("languages")))));
      }
      Map<String, List<String>> infrastructure = new TreeMap<>();
      for (JsonNode id : index.path("infrastructure"))
        infrastructure.put(
            id.asText(),
            strings(read(loader, "infrastructure/" + id.asText() + ".yml").path("entries")));
      return new SpecCatalog(index.path("specVersion").asText(), profiles, rules, infrastructure);
    } catch (IOException e) {
      throw new UncheckedIOException("Cannot load the ArchGuard spec catalog", e);
    }
  }

  private static JsonNode read(ClassLoader loader, String name) throws IOException {
    try (InputStream in = loader.getResourceAsStream(RESOURCE_ROOT + name)) {
      if (in == null) throw new FileNotFoundException("Missing spec resource " + name);
      return new YAMLMapper().readTree(in);
    }
  }

  private static List<String> strings(JsonNode node) {
    List<String> out = new ArrayList<>();
    node.forEach(n -> out.add(n.asText()));
    return List.copyOf(out);
  }

  private static Set<Role> roles(JsonNode node) {
    Set<Role> out = EnumSet.noneOf(Role.class);
    node.forEach(n -> out.add(Role.valueOf(n.asText())));
    return Collections.unmodifiableSet(out);
  }

  public String specVersion() {
    return specVersion;
  }

  public Map<String, Profile> profiles() {
    return profiles;
  }

  public Map<String, RuleSpec> rules() {
    return rules;
  }

  public RuleSpec rule(String id) {
    RuleSpec rule = rules.get(id);
    if (rule == null) throw new IllegalArgumentException("Unknown catalog rule: " + id);
    return rule;
  }

  /** Rule IDs implemented for a language. */
  public Set<String> ruleIds(String language) {
    Set<String> ids = new TreeSet<>();
    rules.values().stream().filter(r -> r.languages().contains(language)).forEach(r -> ids.add(r.id()));
    return Collections.unmodifiableSet(ids);
  }

  /** Role-matrix rules from every profile; activation is decided separately. */
  public List<RoleRule> roleRules() {
    return roleRules;
  }

  public List<String> infrastructure(String language) {
    return infrastructure.getOrDefault(language, List.of());
  }

  /** The selected profiles plus everything they include, transitively. */
  public Set<String> expand(Collection<String> selected) {
    Set<String> out = new TreeSet<>();
    Deque<String> work = new ArrayDeque<>(selected);
    while (!work.isEmpty()) {
      String id = work.pop();
      Profile p = profiles.get(id);
      if (p == null) throw new IllegalArgumentException("Unknown architecture profile: " + id);
      if (out.add(id)) work.addAll(p.includes());
    }
    return out;
  }

  public boolean activatedBy(String ruleId, Collection<String> selected) {
    return expand(selected).stream().anyMatch(id -> profiles.get(id).activates().contains(ruleId));
  }

  public List<RuleDescriptor> descriptors(String language) {
    return ruleIds(language).stream().map(id -> rules.get(id).descriptor()).toList();
  }
}
