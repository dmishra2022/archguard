# Adoption playbook

This playbook is for architects, engineering managers and platform teams who roll ArchGuard out across several teams or services. For the hands-on steps in one repository, use [Onboarding a project](../ONBOARDING.md).

## Principles

1. **Never block on day one.** Every service starts in report-only mode, then gates only *new* violations against a reviewed baseline. Existing debt is made visible, not turned into a wall of red builds.
2. **The policy belongs to the team, the standard to the organisation.** Teams own their `architecture.yml`; the organisation publishes a shared [preset](org-presets.md) with locked rules that teams cannot weaken.
3. **Policy changes are design decisions.** Changes to the policy, baseline and suppressions are reviewed by architecture owners (CODEOWNERS), never made to get a build green.
4. **Exit 2 is never a pass.** A misconfigured or broken analysis fails loudly; nobody gets a false sense of compliance.

## Phases

| Phase | Duration | Scope | Exit criteria |
|---|---|---|---|
| 0. Prepare | 1 week | Platform team | Analyzers available from your registry; organisation preset drafted; CI recipe tested on one repository |
| 1. Pilot | 2 weeks | 1–2 volunteer services per language | Policy written; findings reviewed with the team; false positives fixed or reported; baseline committed; gate on in CI |
| 2. Early adopters | 4 weeks | One team per business area | Onboarding done from the docs alone, without the platform team's help; feedback folded into docs and preset |
| 3. General rollout | Per quarter | All active services | Gate required by branch protection; preset version pinned; dashboard of baseline size per service |
| 4. Steady state | Ongoing | Organisation | Baselines shrink; preset upgrades shipped like any dependency upgrade |

### Phase 0: Prepare

- Decide where teams get the analyzers: public PyPI and npm (`archguard-cli`), or your internal mirror. Java artifacts come from your internal Maven repository or the GitHub release jar.
- Draft the organisation preset from [`presets/acme`](../../presets/acme/README.md): which rules are locked at `ERROR`, whether `requireClassification` is mandatory, and organisation-wide constraints (for example "no service imports another service's internal client").
- Choose the CI integration: the GitHub Action, or the CLI in GitLab, Jenkins or Azure Pipelines ([CI integration](../CI.md)).

### Phase 1: Pilot

Pick services that have an engaged team and an architecture that is roughly hexagonal, clean or layered already. For each:

1. A team member follows [Onboarding a project](../ONBOARDING.md) (about half a day).
2. Review the report-only findings together. Classify each one as a real violation, a role mapping mistake (fix the policy), or an analyzer problem (open an issue with the evidence line).
3. Commit the baseline and turn on the gate with `newOnly: true`.
4. Record how long it took and where the docs were unclear.

### Phase 2 and 3: Rollout

- Announce with a short internal post (template below) and office hours.
- Teams onboard themselves; the platform team reviews the first policy pull request of each team.
- Make the ArchGuard check a required status check once a service has a baseline.

## Roles and responsibilities

| Activity | Architecture owners | Team tech lead | Developers | Platform team |
|---|---|---|---|---|
| Organisation preset | Owns | Consulted | Informed | Publishes |
| Service `architecture.yml` | Approves | Owns | Consulted | — |
| Baseline and suppressions | Approves | Owns | Informed | — |
| Fixing new violations | — | Accountable | Responsible | — |
| CI integration and analyzer upgrades | Informed | Consulted | — | Owns |
| Analyzer bugs and false positives | Consulted | Reports | Reports | Triages |

## Measuring success

- **Coverage**: share of active services with a gate on the default branch.
- **New violations blocked**: count of pull requests that failed the check and were fixed before merging (from CI history).
- **Debt trend**: baseline entry count per service over time. The report lists "baseline entries no longer observed", which are paid-down debt.
- **Policy health**: unclassified units (`MODEL-001`) at 0; number of active suppressions and how many expire this quarter.
- **Onboarding effort**: time from start to gate, per team. Target: half a day.

## Announcement template

> **Subject: Architecture checks in CI with ArchGuard**
>
> From <date>, services can turn on ArchGuard, which checks every pull request against the service's declared architecture (for example: the domain must not import the database layer). It only fails on *new* violations; existing ones are recorded in a baseline and can be fixed over time.
>
> - Getting started (10 minutes): <docs link>/getting-started/
> - Onboarding your service (half a day): <docs link>/ONBOARDING/
> - Office hours: <day/time>, channel: <#channel>
>
> Owners: <architecture group>. Questions and false positives: <support link>.

## Common pitfalls

- **Writing the policy from the ideal architecture instead of the real one.** Map what exists, baseline the gap, then tighten.
- **Turning off rules to get green.** Use a baseline for existing debt and owned, expiring suppressions for justified exceptions; keep rules on.
- **Skipping CODEOWNERS.** Without it, anyone can weaken the policy in the same pull request that breaks it.
- **Gating only changed files everywhere.** `changed-files-only` is good for pull requests, but keep a full check on the default branch.
