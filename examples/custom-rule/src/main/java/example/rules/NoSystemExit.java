package example.rules;

import io.archguard.api.*;
import java.util.List;

public final class NoSystemExit implements ArchitectureRule {
  public String id() {
    return "COMPANY-001";
  }

  public List<Finding> evaluate(ArchitectureModel model) {
    return model.dependencies().stream()
        .filter(
            d ->
                d.target().equals("java.lang.System")
                    && d.evidence().contains("java.lang.System.exit("))
        .map(
            d ->
                Finding.create(
                    id(),
                    Severity.ERROR,
                    "Application code terminates the JVM",
                    d,
                    "Return a failure to the application boundary; let the process owner decide"
                        + " when to terminate."))
        .toList();
  }
}
