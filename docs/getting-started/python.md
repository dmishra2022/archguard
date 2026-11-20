# Quickstart: Python

Time: about 10 minutes. You will run ArchGuard on a sample project, see violations, and then add it to your own project.

**Requirements:** Python 3.9 or later. Use a Python version that can parse your project's syntax. ArchGuard reads source with the standard `ast` module; it does not import or run your code, so your project's dependencies do not need to be installed.

## 1. Try the sample

```bash
git clone https://github.com/dmishra2022/archguard.git
python3 -m venv .venv && . .venv/bin/activate
pip install ./archguard/python/archguard-py
cd archguard/examples/python-violating
archguard check --format console
```

Expected output (abridged), exit code `1`:

```text
ArchGuard 0.1.0: 15 modules, 50 dependencies, 7 findings (4 new, 0 existing, 0 suppressed, 3 info)
ERROR FW-002 [NEW] orders.web.routes#get_order:24 — HTTP contract exposes a persistence entity
ERROR HEX-001 [NEW] orders.domain.order:8 — Domain depends on an outer layer or framework
ERROR HEX-002 [NEW] orders.application.place_order:8 — Application depends on a concrete outer component
ERROR HEX-004 [NEW] orders.web.routes:6 — Inbound and outbound adapters depend directly on each other
```

Each finding is followed by a suggested fix. INFO findings (framework evidence) are counted in the summary but listed only in the reports. The HTML report is at `reports/archguard/index.html`. Run the same command in `examples/python-clean` (hexagonal FastAPI) or `examples/python-django` (layered Django) to see a pass.

## 2. Install in your project

```bash
pip install archguard-cli
# or: uv add --dev archguard-cli   /   poetry add --group dev archguard-cli
```

!!! note
    Until 0.1.0 is on PyPI, install it from the clone in step 1: `pip install <path-to>/archguard/python/archguard-py`.

## 3. Write a starter policy

Copy [`architecture.python.yml`](../../skills/archguard/templates/architecture.python.yml) to `architecture.yml` at the project root. Selectors match **dotted module names under the source root** (`src/` when it holds Python files, otherwise the project root): `orders.domain.**` covers that package and everything below it, and `orders.ports` (without `**`) covers only `orders/ports/__init__.py`.

```yaml
schemaVersion: 2
language: python
roots: ["orders.**"]
profiles: [hexagonal]
roles:
  DOMAIN: ["orders.domain.**"]
  APPLICATION: ["orders.application.**"]
  OUTBOUND_PORT: ["orders.ports", "orders.ports.outbound.**"]
  INBOUND_ADAPTER: ["orders.web.**"]
  OUTBOUND_ADAPTER: ["orders.infrastructure.**"]
  COMPOSITION_ROOT: ["orders", "orders.main", "orders.settings"]
requireClassification: true
newOnly: true
```

This minimal policy uses only `hexagonal`. The template also enables `ddd` and declares `contexts`; keep that if you have bounded contexts, otherwise remove `ddd` and the `contexts` block.

For a layered Django project, start from [`examples/python-django/architecture.yml`](../../examples/python-django/architecture.yml) instead.

## 4. Run it in report-only mode

```bash
archguard validate      # checks the policy file itself
archguard analyze       # writes reports, never fails
```

Adjust the role selectors until no module is reported as unclassified (`MODEL-001`).

## Next steps

- Record existing violations as a baseline, add a pre-commit hook and the CI gate: [Onboarding a project](../ONBOARDING.md#4-capture-existing-debt).
- Understand each rule: [Rules](../RULES.md).
- Where new code should go for FastAPI, Django and Flask: [Python placement guide](../../skills/archguard/reference/python-placement.md).
- Full analyzer reference: [archguard-cli for Python](../../python/archguard-py/README.md).
