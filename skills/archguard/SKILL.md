---
name: archguard
description: >-
  Keeps code changes compliant with the project's ArchGuard architecture policy (architecture.yml)
  in Java, TypeScript/JavaScript and Python projects: places new code in the correct hexagonal,
  layered or DDD role, checks allowed dependencies, runs the ArchGuard check and fixes violations.
  Use when writing, moving or refactoring code in a project that has an architecture.yml, or when
  the user mentions ArchGuard, architecture rules, HEX-/LAYER-/DDD-/FW-/MODEL-/CYCLE- findings,
  ports and adapters, or bounded contexts.
---

# ArchGuard

The architecture policy is `architecture.yml` in the project root. The policy, `architecture-baseline.json` and `architecture-suppressions.json` belong to the architecture owners. You write code that satisfies them; you never change them to make a check pass.

## Workflow

Copy this checklist and track it:

```
- [ ] 1. Read architecture.yml (note `language`)
- [ ] 2. Map every file you will create or edit to a role (and context)
- [ ] 3. Place code using the placement guide; check planned imports against the matrix
- [ ] 4. Run the check
- [ ] 5. Fix every NEW finding; re-run until exit 0
- [ ] 6. Report the result
```

**1. Read the policy.** If `architecture.yml` is missing, stop. Offer to start from the template for the project's language (`templates/architecture.{java,typescript,python}.yml`), but let the user decide the roles; never invent them. Note `language`, `profiles`, `roles`, `contexts`, `constraints` and `requireClassification`.

**2. Map files to roles.** Selectors use `**` for any number of segments and `*` for one. What a selector matches depends on the language:

| `language` | A selector matches | Example | Placement guide |
|---|---|---|---|
| `java` | The class's package | `com.acme.orders.domain.**` | [reference/java-placement.md](reference/java-placement.md) |
| `typescript` | The file's directory, relative to the project root | `src/orders/domain/**` | [reference/typescript-placement.md](reference/typescript-placement.md) |
| `python` | The dotted module name under the source root (`__init__.py` is the package) | `orders.domain.**` | [reference/python-placement.md](reference/python-placement.md) |

With `requireClassification: true`, a unit matching no role is a MODEL-001 error, so only create files where the policy has a role.

**3. Place code correctly.** Follow the placement guide for the language. Before writing an import, look up the row for the importing role in the profile's matrix in [reference/rules.md](reference/rules.md). Typical moves:
- Database or external API access needs an OUTBOUND_PORT interface (Java interface, TypeScript interface, Python `Protocol`/`ABC`) in the core, implemented by an OUTBOUND_ADAPTER.
- Controllers and route handlers live in INBOUND_ADAPTER and call APPLICATION, never an OUTBOUND_ADAPTER.
- No framework or persistence imports in DOMAIN or ports.
- Endpoints take and return DTOs or schemas, never persistence entities (FW-002).
- Another bounded context is used only through its `exposedPackages`.

**4. Run the check** from the project root, after editing:

```bash
bash <this-skill-dir>/scripts/check.sh --changed     # findings in files changed vs HEAD
bash <this-skill-dir>/scripts/check.sh               # full check (before finishing a larger change)
```

The script reads `language` from the policy. It compiles Java projects first. TypeScript and Python are analyzed from source, and the project's analyzer must be installed: `archguard-cli` in `devDependencies`, or the `archguard-cli` Python distribution in the dev environment. It prints one JSON line per finding and a final summary line. Exit `0` means pass, `1` means violations, and `2` means the build or analysis failed. Exit 2 is never a pass: read the `error`. For example, fix compilation errors, unparsable files or unresolved project imports. If the analyzer or the policy is missing, tell the user; do not install tools or change dependencies unasked.

**5. Fix findings.** For each line with `"status":"NEW"`, open `file` at `line`, read `message` and `fix`, and look up `rule` in [reference/rules.md](reference/rules.md) for compliant examples in the project's language. Restructure the code (introduce a port, move the file, map entities to DTOs) and re-run. `EXISTING` findings are baselined legacy debt: leave them unless the task is to fix them.

**6. Report** which roles the new code went into and the final check result (or the exact blocking finding).

## Never do this to get a green check

- Edit `architecture.yml`, the baseline or suppressions files, or regenerate the baseline.
- Set `allowEmptySelectors`, `allowEmptyAnalysis`, `unresolvedImports: warn`, `typeOnlyImports: ignore` or `archguard.skip`, remove the analyzer or the CI step, or lower `failOn`.
- Move code into a package or directory just because no rule covers it, or into a role it does not belong to.
- Hide a dependency from the analyzer: reflection or string class names (Java), computed `import()`/`require()` or string-keyed DI (TypeScript), `importlib` with computed names or string references (Python).

If a finding looks wrong or the task cannot be done within the policy (for example it needs a package another context does not expose), stop and explain the conflict to the user. Quote the rule ID and the dependency. Policy changes go through review by the architecture owners.

## Resources

- [reference/rules.md](reference/rules.md): role matrices per profile, every rule with rationale, fix and Java, TypeScript and Python examples (generated from the spec; do not edit).
- [reference/java-placement.md](reference/java-placement.md), [reference/typescript-placement.md](reference/typescript-placement.md), [reference/python-placement.md](reference/python-placement.md): role-to-location guides and recipes.
- `templates/architecture.{java,typescript,python}.yml`: starter policies for onboarding a project.
- [hooks/README.md](hooks/README.md): optional Cursor hook that runs the check automatically when the agent stops.
