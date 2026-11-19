---
name: archguard
description: >-
  Keeps code changes compliant with the project's ArchGuard architecture policy (architecture.yml):
  places new classes in the correct hexagonal, layered or DDD role, checks allowed dependencies, runs
  the ArchGuard check and fixes violations. Use when writing, moving or refactoring code in a
  project that has an architecture.yml, or when the user mentions ArchGuard, architecture rules,
  HEX-/LAYER-/DDD-/FW-/MODEL-/CYCLE- findings, ports and adapters, or bounded contexts.
---

# ArchGuard

The architecture policy is `architecture.yml` in the project root. The policy, `architecture-baseline.json` and `architecture-suppressions.json` belong to the architecture owners. You write code that satisfies them; you never change them to make a check pass.

## Workflow

Copy this checklist and track it:

```
- [ ] 1. Read architecture.yml
- [ ] 2. Map every file you will create or edit to a role (and context)
- [ ] 3. Place code using the placement guide; check planned imports against the matrix
- [ ] 4. Run the check
- [ ] 5. Fix every NEW finding; re-run until exit 0
- [ ] 6. Report the result
```

**1. Read the policy.** If `architecture.yml` is missing, stop. Offer to start from `templates/architecture.java.yml`, but let the user decide the roles; never invent them. Note `profiles`, `roles`, `contexts` and `requireClassification`.

**2. Map files to roles.** For each new or changed class, find the `roles` selector its package matches (`**` = any segments, `*` = one segment). With `requireClassification: true`, a class matching no role is a MODEL-001 error, so only create classes in packages the policy covers.

**3. Place code correctly.** Follow [reference/java-placement.md](reference/java-placement.md). Before writing an import, look up the row for the importing role in the profile's matrix in [reference/rules.md](reference/rules.md). Typical moves:
- Database or external API access needs an OUTBOUND_PORT interface in the core, implemented by an OUTBOUND_ADAPTER.
- Controllers live in INBOUND_ADAPTER and call APPLICATION, never an OUTBOUND_ADAPTER.
- No framework or persistence APIs in DOMAIN or ports.
- Another bounded context is used only through its `exposedPackages`.

**4. Run the check** from the project root, after editing:

```bash
bash <this-skill-dir>/scripts/check.sh --changed     # findings in files changed vs HEAD
bash <this-skill-dir>/scripts/check.sh               # full check (before finishing a larger change)
```

The script compiles the project, then prints one JSON line per finding and a final summary line. Exit `0` means pass, `1` means violations, and `2` means the build or analysis failed. Exit 2 is never a pass: read the `error` and fix compilation errors. If the CLI or the policy is missing, tell the user.

**5. Fix findings.** For each line with `"status":"NEW"`, open `file` at `line`, read `message` and `fix`, and look up `rule` in [reference/rules.md](reference/rules.md) for compliant examples. Restructure the code (introduce a port, move the class, map entities to DTOs) and re-run. `EXISTING` findings are baselined legacy debt: leave them unless the task is to fix them.

**6. Report** which roles the new code went into and the final check result (or the exact blocking finding).

## Never do this to get a green check

- Edit `architecture.yml`, the baseline or suppressions files, or regenerate the baseline.
- Set `allowEmptySelectors`, `allowEmptyAnalysis` or `archguard.skip`, remove the plugin, or lower `failOn`.
- Move a class into a package just because no rule covers it, or into a role it does not belong to.
- Use reflection, string class names or similar tricks to hide a dependency.

If a finding looks wrong or the task cannot be done within the policy (for example it needs a package another context does not expose), stop and explain the conflict to the user. Quote the rule ID and the dependency. Policy changes go through review by the architecture owners.

## Resources

- [reference/rules.md](reference/rules.md): role matrices per profile, every rule with rationale, fix and examples (generated from the spec; do not edit).
- [reference/java-placement.md](reference/java-placement.md): role-to-package guide and recipes.
- [templates/architecture.java.yml](templates/architecture.java.yml): starter policy for onboarding a project.
- [hooks/README.md](hooks/README.md): optional Cursor hook that runs the check automatically when the agent stops.
