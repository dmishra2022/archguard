package io.archguard.api;

import java.nio.charset.StandardCharsets;
import java.security.*;
import java.util.*;

public record Finding(
    String fingerprint,
    String ruleId,
    Severity severity,
    String message,
    String evidence,
    Location location,
    String target,
    String remediation,
    String status) {
  public static Finding create(
      String rule, Severity severity, String message, Dependency d, String remediation) {
    // Source line movement does not create new debt; distinct semantic accesses remain distinct.
    String semantic = d.evidence().replaceAll("\\([^()]*\\.java:[0-9]+\\)", "(source)");
    String key =
        rule
            + "\n"
            + d.location().module()
            + "\n"
            + d.origin()
            + "\n"
            + d.target()
            + "\n"
            + semantic;
    try {
      return new Finding(
          HexFormat.of()
              .formatHex(
                  MessageDigest.getInstance("SHA-256")
                      .digest(key.getBytes(StandardCharsets.UTF_8))),
          rule,
          severity,
          message,
          d.evidence(),
          d.location(),
          d.target(),
          remediation,
          "NEW");
    } catch (NoSuchAlgorithmException e) {
      throw new IllegalStateException(e);
    }
  }

  public Finding withStatus(String s) {
    return new Finding(
        fingerprint, ruleId, severity, message, evidence, location, target, remediation, s);
  }

  public Finding withSeverity(Severity s) {
    return new Finding(
        fingerprint, ruleId, s, message, evidence, location, target, remediation, status);
  }
}
