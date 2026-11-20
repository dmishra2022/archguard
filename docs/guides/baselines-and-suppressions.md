# Baselines and suppressions

Existing projects rarely comply with their target architecture on day one. ArchGuard gives you two reviewed mechanisms to adopt it anyway, without switching rules off.

| | Baseline | Suppression |
|---|---|---|
| Purpose | Accept *all existing* violations at adoption time, so only new ones fail | Accept *one specific* violation as a deliberate exception |
| File | `architecture-baseline.json` (generated) | `architecture-suppressions.json` (hand-written) |
| Required fields | Generated: fingerprints, policy hash, engine version | `fingerprint`, `owner`, `reason`, `expires` |
| Expires | When the policy or analyzer version changes | On the stated date (UTC), after which analysis fails |
| Visible in reports | Yes, as `EXISTING` | Yes, as `SUPPRESSED` |

Both files should be reviewed by architecture owners (see [CODEOWNERS](../ONBOARDING.md#7-protect-the-gate)).

## Baselines

### Create

Set `newOnly: true` in `architecture.yml`, then:

```bash
npx archguard baseline                                              # TypeScript
archguard baseline                                                  # Python
mvn compile io.archguard:archguard-maven-plugin:0.1.0:baseline     # Java (Maven)
java -jar archguard-cli-0.1.0.jar baseline                          # Java (CLI)
```

Review the file in a pull request and commit it. `check` picks it up with `--baseline architecture-baseline.json` (or `-Darchguard.baseline=...` for Maven; the GitHub Action finds it automatically at the default name).

### How matching works

Each finding has a **fingerprint** computed from the rule, the module and the symbols involved, not the line number. Moving code within a file does not create a "new" finding; changing which class or module depends on which does. See [spec/FINGERPRINT.md](https://github.com/dmishra2022/archguard/blob/main/spec/FINGERPRINT.md).

A baseline is bound to the **policy hash** and the **engine version**. If either changes, the check refuses the baseline instead of silently comparing against the wrong rules.

### Regenerate

Regenerate in a dedicated, reviewed pull request when you:

- change `architecture.yml` (including upgrading a preset version), or
- upgrade the analyzer.

```bash
archguard baseline --overwrite-baseline            # TypeScript: npx archguard ...; Maven: -Darchguard.overwriteBaseline=true
```

The reviewer should check that the baseline did not *grow*: a regeneration must only remove entries, unless the policy deliberately became stricter.

### Pay down debt

Fix baselined violations like any other refactoring. The report lists "Baseline entries no longer observed"; when the list is non-empty, regenerate the baseline so it only shrinks. Track the entry count per service as a debt metric.

## Suppressions

Use a suppression when a specific dependency is a deliberate, approved exception, for example a temporary adapter shortcut during a migration.

```json
{
  "schemaVersion": 1,
  "entries": [
    {
      "fingerprint": "<64-character fingerprint from archguard.json>",
      "owner": "team-orders",
      "reason": "Legacy billing client is called directly until BILL-142 introduces a port",
      "expires": "2027-03-31"
    }
  ]
}
```

- Copy the `fingerprint` from the finding in `reports/archguard/archguard.json` (`target/archguard/` for Java).
- `owner`, `reason` and `expires` are required. Missing fields, duplicate fingerprints and **expired entries fail the analysis** (exit 2), so exceptions cannot outlive their justification unnoticed.
- Pass the file with `--suppressions architecture-suppressions.json` (Maven: `-Darchguard.suppressions=...`); the GitHub Action picks it up at the default name.

## Which one to use

- Adopting ArchGuard on existing code: **baseline**.
- A new violation that the team and architecture owners agree to accept for a limited time: **suppression** with an expiry date and a ticket in the reason.
- A dependency that is actually fine by design: neither. **Change the policy** (role mapping, `exposedPackages` or a rule severity) in a reviewed pull request.
