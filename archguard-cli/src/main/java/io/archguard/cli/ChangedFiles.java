package io.archguard.cli;

import io.archguard.api.*;
import java.nio.file.Path;
import java.util.*;

/**
 * Restricts reported and gated findings to those located in changed files. The full graph is
 * still analyzed, so violations caused by a changed file against unchanged code are kept.
 */
final class ChangedFiles {
  private ChangedFiles() {}

  static AnalysisResult restrict(AnalysisResult result, List<String> lines, Path project) {
    Set<String> files = new HashSet<>();
    for (String line : lines) {
      String entry = line.strip();
      if (entry.isEmpty() || entry.startsWith("#")) continue;
      files.add(normalize(entry, project));
    }
    List<Finding> kept = new ArrayList<>();
    for (Finding f : result.findings())
      if (files.contains(normalize(f.location().path(), project))) kept.add(f);
    List<String> diagnostics = new ArrayList<>(result.diagnostics());
    diagnostics.add(
        "Changed-files scope: "
            + files.size()
            + " file(s); "
            + (result.findings().size() - kept.size())
            + " finding(s) outside the list not reported");
    return result.withFindingsAndDiagnostics(kept, diagnostics);
  }

  static String normalize(String path, Path project) {
    Path p = Path.of(path.replace('\\', '/'));
    if (p.isAbsolute()) p = Inputs.real(project).relativize(Inputs.real(p));
    return p.normalize().toString().replace('\\', '/');
  }
}
