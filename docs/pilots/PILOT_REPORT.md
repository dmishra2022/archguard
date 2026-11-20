# Java pilot report (plan step 8)

Two public Spring Boot projects with different structures were taken through the adoption flow: policy, `analyze`, review, baseline, `newOnly` gate, an injected violation, and an agent run. The policies used are in this directory.

| | [thombergs/buckpal](https://github.com/thombergs/buckpal) | [spring-projects/spring-petclinic](https://github.com/spring-projects/spring-petclinic) |
|---|---|---|
| Style | Hexagonal (ports and adapters) | Package by feature |
| Build | Gradle 7.5 (via the bundled init script, no build changes) | Maven wrapper |
| Profile | `hexagonal` | `modular-monolith` (contexts `owner`, `vet`, `system`, shared `model`) |
| Classes analyzed / dependency jars | 34 / 68 | 25 / 106 |
| Analysis time (CLI, after compile) | 0.8 s | 0.9 s |
| Full local gate, warm build (compile + classpath + analysis) | 1.8 to 2.4 s | about 3 s |
| Cold build including dependency resolution | about 22 s | about 23 s |

Both are well under the 2-minute budget proposed in the plan. Analysis itself is under a second; the build dominates.

## Findings and their classification

**buckpal.** The first mapping put `common` (Spring stereotype meta-annotations such as `@UseCase`) under DOMAIN. That produced 9 HEX-001 findings, all correct for that mapping: the review step exposed a policy mistake, not an analyzer error. With `common` mapped as framework glue (COMPOSITION_ROOT), two findings remain, both real design trade-offs:
- HEX-002: `SendMoneyService` (APPLICATION) is annotated with the Spring-backed `@UseCase`.
- HEX-003: `SendMoneyCommand` (an inbound port) calls the `Validation` helper from `common`.

Both were baselined. Injecting a real shortcut (the web controller injecting the persistence adapter) produced 2 NEW HEX-004 findings and failed the gate. The changed-files gate reported only those two, and reverting returned to a pass.

**spring-petclinic.** There were no context-boundary findings, which is correct: `owner`, `vet` and `system` do not import each other. There were 10 FW-002 errors. MVC handler methods bind JPA entities (`Owner`, `Pet`, `Visit`) from HTTP forms. That is the mass-assignment exposure the rule targets; petclinic mitigates it with `setDisallowedFields("id")`, so a team would baseline these or lower FW-002 to WARNING deliberately. Injecting `OwnerRepository` into `VetController` produced exactly one NEW DDD-001 finding and failed the gate.

**False positives: 0** of the 12 non-INFO findings under the final policies. MODEL-002 INFO findings (framework classification notes) were all accurate and never gate.

## Agent run on buckpal

A separate coding agent got a copy of buckpal with the skill installed in `.cursor/skills/archguard`, the pilot policy and the baseline. Its task was: "add `GET /accounts/{accountId}/balance`". It received no architecture hints beyond the skill.

What the agent did:
- Ran the gate first. It passed with the 2 existing findings.
- Created `adapter/in/web/GetAccountBalanceController` (INBOUND_ADAPTER). It depends only on the inbound port `GetAccountBalanceUseCase` and domain value types.
- Wired the existing `GetAccountBalanceService` as a bean in the composition root (`BuckPalConfiguration`). It deliberately did not annotate the service with `@UseCase`. The baseline run had shown that `@UseCase` on `SendMoneyService` is a HEX-002 finding, so copying that pattern would have added a NEW violation.
- Added a `@WebMvcTest` in the style of the existing controller tests.
- Did not edit `architecture.yml`, the baseline or suppressions, and did not commit.

Independent verification after the run:
- The policy and the baseline are byte-identical to the originals.
- `check.sh --baseline architecture-baseline.json` exits 0 with summary `{"status":"PASSED","new":0,"existing":2,"suppressed":0}`.
- `./gradlew test` passes.

The changed-files gate (`--changed`) took 2.5 s and the full gate 1.4–2.6 s.

## Issues found and what was done

| Issue | Action |
|---|---|
| Gradle projects needed a hand-written task to produce the classpath file | Fixed: `skills/archguard/scripts/archguard.init.gradle`, used by the check script and the GitHub Action; no build changes needed |
| Reports for Gradle projects went to `target/` | Fixed: `build/archguard` for Gradle in the check script and the Action |
| Classes outside `roots` are silently unchecked, and dependencies on them are ignored, which offers a way to bypass the gate | Fixed: new diagnostic "Compiled classes outside roots (not checked, ...): N" in every report. Reviewers and the skill treat a non-zero count as a policy-scope question |
| One conceptual dependency yields several findings (one per evidence site: field, constructor, call, annotation attribute) | Mitigated: the Action summary groups findings by rule, file and target with a site count. Fingerprints are unchanged, so baselines are unaffected |
| A transient Maven Central error failed one Action run with exit 2 (correctly not a pass) | Fixed: the Action retries the source build up to 3 times |
| Actions pinned to deprecated majors (Node 20, CodeQL v3) | Fixed: checkout v7, setup-java v6, upload-artifact v7, codeql-action v4 |
| Spring meta-annotation packages (`common`) fit no role cleanly | Proposal for a spec minor version: a `shared` selector list for packages any role may depend on, with no rules of its own. Not implemented; it changes the policy schema and needs agreement |
| FW-002 on server-side MVC form binding may surprise teams | Documented in the Java placement guide; teams can baseline or set FW-002 to WARNING |

## Verdict

The exit criteria hold:
- False positives are acceptable (none found).
- The gate is well within a 2-minute budget.
- The agent loop works: the agent placed new code in the right roles, avoided a known violating pattern, and left the policy alone.

TypeScript and Python can start on the same contract.
