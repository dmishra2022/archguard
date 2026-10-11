package io.archguard.engine;

import com.fasterxml.jackson.databind.*;
import io.archguard.api.*;
import io.archguard.config.*;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.*;

public final class ArchitectureEngine {
    public static final String VERSION = "0.1.0";

    public AnalysisResult evaluate(
            ArchitectureModel model, Policy policy, List<ArchitectureRule> extensions) {
        Policies.validate(policy);
        Set<String> ids = new HashSet<>(BuiltinRules.IDS);
        for (var c : policy.constraints())
            if (!ids.add(c.id())) throw new IllegalArgumentException("Duplicate rule ID: " + c.id());
        for (var rule : extensions)
            if (rule.id() == null || rule.id().isBlank() || !ids.add(rule.id()))
                throw new IllegalArgumentException("Invalid/duplicate custom rule ID: " + rule.id());
        for (String configured : policy.rules().keySet())
            if (!ids.contains(configured))
                throw new IllegalArgumentException("Unknown rule ID: " + configured);
        List<Finding> findings = new ArrayList<>(BuiltinRules.evaluate(model, policy));
        for (var rule : extensions) {
            var setting = policy.rules().get(rule.id());
            if (setting != null && Boolean.FALSE.equals(setting.enabled())) continue;
            var result = Objects.requireNonNull(rule.evaluate(model), "Rule returned null: " + rule.id());
            for (var f : result) {
                if (!f.ruleId().equals(rule.id()))
                    throw new IllegalArgumentException("Custom rule emitted another rule ID");
                findings.add(
                        setting != null && setting.severity() != null ? f.withSeverity(setting.severity()) : f);
            }
        }
        TreeMap<String, Finding> unique = new TreeMap<>();
        for (var f : findings) unique.putIfAbsent(f.fingerprint(), f);
        findings = new ArrayList<>(unique.values());
        findings.sort(
                Comparator.comparing(Finding::ruleId)
                        .thenComparing(f -> f.location().module())
                        .thenComparing(f -> f.location().symbol())
                        .thenComparing(Finding::fingerprint));
        List<String> diagnostics = new ArrayList<>(model.diagnostics());
        diagnostics.add(
                "Scope: supplied compiled modules and root selectors only; external service behavior is not"
                        + " analyzed.");
        return new AnalysisResult(
                "1",
                VERSION,
                hash(policy),
                model.types().size(),
                model.dependencies().size(),
                findings,
                diagnostics);
    }

    public AnalysisResult analyze(
            List<ModuleInput> modules,
            List<java.nio.file.Path> classpath,
            Policy policy,
            List<ArchitectureRule> extensions)
            throws java.io.IOException {
        return evaluate(new ModelImporter().read(modules, classpath, policy), policy, extensions);
    }

    public static String hash(Policy p) {
        try {
            var mapper =
                    new ObjectMapper()
                            .enable(
                                    SerializationFeature
                                            .ORDER_MAP_ENTRIES_BY_KEYS); // sort unordered sets through a canonical tree
            JsonNode tree = mapper.valueToTree(p);
            ((com.fasterxml.jackson.databind.node.ObjectNode) tree)
                    .set("profiles", mapper.valueToTree(new TreeSet<>(p.profiles())));
            return HexFormat.of()
                    .formatHex(
                            MessageDigest.getInstance("SHA-256")
                                    .digest(
                                            (VERSION + "\n" + mapper.writeValueAsString(tree))
                                                    .getBytes(StandardCharsets.UTF_8)));
        } catch (Exception e) {
            throw new IllegalStateException("Cannot fingerprint policy", e);
        }
    }
}
