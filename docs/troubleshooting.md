# Troubleshooting

Start with the exit code:

| Exit code | Meaning | What to do |
|---|---|---|
| `0` | Pass | Nothing |
| `1` | Policy violation | Fix the code (each finding has a suggested fix), or change the policy in a reviewed pull request |
| `2` | The analysis could not run | Read the error message; the sections below cover the common ones. **Never treat exit 2 as a pass** |
| `64` | Usage error | Check the command-line options (`archguard --help`) |

On exit 2, the reports are overwritten with an explicit failure report, so a stale passing report is never left behind.

## Policy errors (exit 2)

**`Unknown policy key at (root): profile`** (or any unknown key)
: Every key is validated, so typos fail instead of being ignored. The key is `profiles` (a list): `profiles: [hexagonal]`. Compare with your language's [template](https://github.com/dmishra2022/archguard/tree/main/skills/archguard/templates) or run `archguard validate`.

**`Empty selector for role DOMAIN`** (or a context or constraint)
: A selector matches no unit. Usually a wrong path style: Java selectors are packages (`com.acme.orders.domain.**`), TypeScript selectors are directories relative to the project root (`src/orders/domain/**`), Python selectors are dotted module names under the source root (`orders.domain.**`, not `src.orders.domain.**`). If a role is intentionally empty for now, set `allowEmptySelectors: true`.

**`Ambiguous role mapping for <unit>: [APPLICATION, OUTBOUND_PORT]`**
: Two roles match the same unit. Make the selectors disjoint. A common case is `APPLICATION: ["orders.application.**"]` together with `OUTBOUND_PORT: ["orders.application.ports.**"]`: use `orders.application` (no `**`) plus specific sub-packages for `APPLICATION`.

**`No application modules matched roots; refusing a vacuous pass`**
: `roots` matches nothing, so there is nothing to check. Check the selector style as above, and for Python check the source root (`src/` is used when it holds Python files; set `sourceRoots` otherwise).

**`Rule HEX-002 is locked by an extended preset`**
: Your organisation's preset locks that rule. Changing it needs a new preset version from the architecture owners.

**`Policy preset not found: presets/base/1.0.0.yml in acme_archguard_presets`**
: The preset package or that version is not installed where the analyzer runs. Install it as a dev dependency (TypeScript, Python), add it as a plugin dependency or `--extension` (Java), or pass it with the Action's `extensions` input. See [Organisation presets](guides/org-presets.md).

**`Baseline schema, engine or policy does not match; review and explicitly regenerate it`**
: The policy (including a preset version) or the analyzer version changed since the baseline was created. Regenerate it with `--overwrite-baseline` in a reviewed pull request ([how](guides/baselines-and-suppressions.md#regenerate)).

**`Expired suppression: <fingerprint>`**
: A suppression passed its `expires` date. Fix the violation, or agree a new date with the architecture owners.

## Analysis errors by language (exit 2)

### Python

**`Unresolved import of an owned module: 'from orders.domain.missing import X'`**
: The import names a module of your project that does not exist. Typical causes: a typo, generated code that has not been generated yet (run your generators first), or a file excluded by the scan (tests and hidden directories are excluded). While investigating, set `unresolvedImports: warn`.

A local folder named like a third-party package (for example a `src/alembic/` migrations folder without `__init__.py`) does not cause this as long as it is outside `roots`: imports under it that match no file are treated as the installed package.

**`SyntaxError` / a file that does not parse**
: Run ArchGuard with a Python version that supports your project's syntax (for example 3.12 for `type` statements).

### TypeScript / JavaScript

**Unresolved project import**
: ArchGuard resolves imports through your `tsconfig.json` (`paths`, `baseUrl`, project references). Pass `--tsconfig` if the file is not at the project root, run code generators first, or set `unresolvedImports: warn` while investigating.

**`Policy preset not found` for `@acme/archguard-presets`**
: Presets resolve from the project's `node_modules`; run `npm ci` before the check (also in CI).

### Java

**Missing classes or `target/classes` not found**
: The Java analyzer reads bytecode. Compile first (`mvn compile`, `./gradlew classes`), and for multi-module builds run `check-reactor` from the reactor root after compilation.

**Unresolved dependencies**
: Pass the full compile classpath (`--classpath-file` written by `mvn archguard:classpath` or the Gradle init script).

## Findings that look wrong

1. **Check the role mapping first.** Most surprising findings are a package or directory in the wrong role. The finding's evidence line shows the exact dependency, for example `Module <orders.web.routes> imports <orders.infrastructure.repo> (routes.py:6)`.
2. **Unclassified units** (`MODEL-001`): add a selector, or narrow `roots` if the code should not be checked.
3. **The finding is correct but accepted**: use a [baseline or a suppression](guides/baselines-and-suppressions.md), not a disabled rule.
4. **The analyzer is wrong**: open an issue with the policy excerpt, the evidence line and the analyzer version (`archguard --version`). See [Getting support](support.md).

## CI-specific problems

**The GitHub Action reports the wrong language**
: It uses the `language` input, then `language:` in the policy, then build files. Set `language:` in `architecture.yml`.

**`changed-files-only` reports nothing on pull requests**
: Check out with `fetch-depth: 0`, so the merge base with the target branch is available.

**SARIF upload fails on a private repository**
: Code scanning needs GitHub Advanced Security on private repositories. Set `upload-sarif: "false"`; the annotations, job summary and report artifact still work.

**Annotations point at the wrong path in a monorepo**
: Set `working-directory` to the project's directory; the Action rewrites report paths to be relative to the repository root.
