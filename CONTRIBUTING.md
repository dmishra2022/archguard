# Contributing

Thank you for helping improve ArchGuard. Bug reports with a minimal reproduction, false-positive reports and documentation fixes are as valuable as code.

## Repository layout

| Path | Contents |
|---|---|
| `spec/` | The language-neutral specification: policy schema, profiles, rule catalog, fingerprints, conformance cases |
| `archguard-api`, `archguard-core`, `archguard-cli`, `archguard-maven-plugin` | Java analyzer, CLI and Maven plugin |
| `typescript/archguard-ts` | TypeScript/JavaScript analyzer (`archguard-cli` on npm) |
| `python/archguard-py` | Python analyzer (`archguard-cli` on PyPI) |
| `action/` | GitHub Action |
| `skills/archguard` | Agent skill |
| `presets/acme` | Organisation preset template |
| `docs/` | Documentation site ([Zensical](https://zensical.org), configured in `zensical.toml`) |

## Development

```bash
mvn -B install                                                    # Java build and tests
(cd typescript/archguard-ts && npm ci && npm test)                # TypeScript
(cd python/archguard-py && python3 -m unittest discover -s tests) # Python
python3 scripts/spec_check.py                                     # spec schemas and policies
python3 scripts/conformance.py                                    # all analyzers against spec/conformance
pip install -r docs/requirements.txt && zensical serve            # documentation preview (Python 3.11+)
```

## Rules for changes

- **Behaviour changes start in the spec.** A new rule, profile or policy key is added to `spec/` with a conformance case, then implemented in every analyzer. All analyzers must pass the same conformance suite.
- **Fingerprints are a compatibility contract.** Do not change what goes into a fingerprint without a major spec version ([spec/VERSIONING.md](spec/VERSIONING.md)).
- **Exit 2 is never a pass.** If an analyzer cannot analyze something it was asked to, it must fail with a clear message rather than report compliance.
- Add tests with every fix, and a line to `CHANGELOG.md` under "Unreleased".
- Versions of all packages move together; `scripts/release_check.py` verifies them.

## Pull requests

Keep pull requests focused, describe the user-visible effect, and make sure CI is green. Changes to `spec/`, `presets/`, `action/`, `skills/` and the workflows need review from the code owners.
