# Python analyzer pilot (plan step 10)

The analyzer `archguard` (`python/archguard-py`) was checked in four ways:
- the shared conformance suite;
- unit tests on Python 3.9, 3.11 and 3.13, and the built wheel installed into a fresh Python 3.9 environment;
- three examples in this repository (FastAPI clean, FastAPI violating, Django REST Framework), each with its own running test suite;
- three public projects: a hexagonal reference application, a FastAPI/SQLModel template and a Django styleguide project.

## Conformance and packaging

`python3 scripts/conformance.py --language python` passes all 8 cases: clean, hex-002, ddd-001, cycles, http-entity, unclassified, invalid-policy and layered. The Python variants cover these import forms on purpose:
- regular packages (`clean` has `__init__.py` files) and namespace packages (every other case);
- relative imports (`from ..domain.order import Order`) and `from package import submodule`;
- `if TYPE_CHECKING:` imports (`cycles`, `layered`);
- `import a.b.c as alias` (`ddd-001`);
- a FastAPI router created in one module and used in another (`http-entity`).

The 23 unit tests pass on Python 3.9, 3.11 and 3.13. Python 3.9 exercises the fallback `pyproject.toml` reader that is used when `tomllib` is missing. The wheel bundles the spec catalog. Installed into a fresh Python 3.9 environment, the `archguard` and `archguard-pre-commit` entry points both work.

The pre-commit hook was run end to end with `pre-commit` against a git repository built from the `hex-002` case, using a `repo: local` hook with `language: python` that installs the wheel. Staging an unrelated file passed. Staging the use case that imports the adapter failed with HEX-002.

## Repository examples

| Example | Expected | Result |
|---|---|---|
| `examples/python-clean`: hexagonal and DDD FastAPI orders service (router, Pydantic DTOs, use case, `Protocol` port, SQLAlchemy 2.0 adapter, composition root with `dependency_overrides`) | pass | exit 0. 15 modules, 43 dependencies, 0 violations. Its 2 API tests pass with FastAPI and SQLAlchemy on Python 3.9 |
| `examples/python-violating`: the same service with a use case that constructs the SQLAlchemy repository, a route that returns the ORM record and imports the infrastructure package, and a domain that imports `sqlalchemy.orm` | HEX-002, FW-002, HEX-004, HEX-001 | exit 1 with exactly those four findings, the same set as `examples/typescript-violating` |
| `examples/python-django`: layered Django REST Framework service in the HackSoft style (APIs, services and selectors, models, an ISBN integration) with a project constraint that keeps views off the ORM | pass | exit 0. 15 modules, 0 violations. Accurate `django.endpoint`, `django.routing` and `persistence.entity` tags. Django's system check and the 2 API tests pass. Injecting `from catalog.models import Book` into the APIs and an integration import into the serializers produced exactly CATALOG-001 and LAYER-002 |

## Public hexagonal project: [cosmicpython/code](https://github.com/cosmicpython/code) (commit 14c8479)

This is the reference application of *Architecture Patterns with Python*: Flask, SQLAlchemy classical mapping, Redis, a message bus and a unit of work. The policy is in [cosmicpython/architecture.yml](cosmicpython/architecture.yml) and follows the book's own layering. `domain` is DOMAIN, `service_layer` and `views` are APPLICATION, `adapters` are OUTBOUND_ADAPTER, `entrypoints` are INBOUND_ADAPTER, and `bootstrap` and `config` are the COMPOSITION_ROOT. CYCLE-001 is on.

Timing: 20 modules and 71 dependencies in 0.2 s for the whole CLI run.

Findings: 4 non-INFO findings, all confirmed against the source. Each is a deliberate pragmatic choice in the book.
- **HEX-002 (×3):**
  - `service_layer.unit_of_work` imports `adapters.repository`, because the abstract repository lives in the adapters package.
  - `service_layer.unit_of_work` imports `allocation.config`.
  - `service_layer.handlers` type-imports `adapters.notifications` (inside `if TYPE_CHECKING:`) for `AbstractNotifications`.
- **CYCLE-001:** the packages `allocation`, `allocation.adapters` and `allocation.service_layer` form a real cycle. `bootstrap` imports both, and the adapters and the unit of work import `allocation.config` back.

The baseline, `newOnly` gate and injected violation behaved as intended:
- The baseline recorded 4 findings, and the gate then passed.
- Appending `import requests` to `domain/model.py` produced exactly one NEW HEX-001 and failed the gate with exit 1.
- Reverting returned to a pass.

**False positives: 0.**

## Public FastAPI project: [fastapi/full-stack-fastapi-template](https://github.com/fastapi/full-stack-fastapi-template) (commit 77e550a)

This project uses FastAPI, SQLModel, Alembic and JWT authentication. Its backend requires Python 3.14 and uses PEP 758 syntax (`except A, B:`). Under Python 3.11 the analyzer stopped with exit 2: `Cannot parse backend/app/api/deps.py:36 ... Run ArchGuard with a Python version that supports the project syntax`. That is the intended behavior, because an unparsable file never produces a pass. Under Python 3.14 it analyzed 23 modules and 118 dependencies in 0.04 s (analysis only, excluding interpreter start-up).

The policy is in [full-stack-fastapi-template/architecture.yml](full-stack-fastapi-template/architecture.yml): the `layered` profile with routes and dependencies as presentation, `crud` and `security` as business, `models` as domain, and `core.db`, the email utilities and Alembic as persistence and integration.

The first run modelled `app.core.config` (the settings object) as part of the composition root. Four LAYER-001 findings were lower layers reading settings, which is a policy-modelling mistake, not an architecture problem. Leaving the settings module unclassified, as a shared kernel, removed them.

Findings with the refined policy: 7 non-INFO findings, all confirmed against the source.
- **LAYER-001 (×2):**
  - `core.db` imports `crud` to create the first superuser, so persistence calls business code.
  - `utils` (email) imports `core.security` to issue password-reset tokens.
- **LAYER-002 (×4):**
  - `api.deps` takes the engine from `core.db`.
  - The `login`, `users` and `utils` routes call the email utilities directly instead of going through a business function.
- **CYCLE-001:** the packages `app`, `app.api`, `app.api.routes` and `app.core` form a real cycle.

FW-002 reported nothing, which is correct. Every route returns a `*Public` model or `Any` with a `*Public`/`Message` `response_model`. The `table=True` models (`User`, `Item`) reach handlers only as injected dependencies (`CurrentUser = Annotated[User, Depends(...)]`), which are not part of the HTTP contract.

**False positives: 0.**

## Public Django project: [HackSoftware/Django-Styleguide-Example](https://github.com/HackSoftware/Django-Styleguide-Example) (commit a70ef43)

This project uses Django, Django REST Framework, Celery, django-filter, S3 integration and Google OAuth. The policy is in [django-styleguide-example/architecture.yml](django-styleguide-example/architecture.yml). It maps the styleguide's conventions onto the `layered` profile:
- APIs, views, URLs, admin and Celery tasks are presentation, because tasks are triggered by the broker;
- services, selectors and filters are business;
- models, enums and shared exceptions are domain;
- the AWS integration is outbound.

Timing: 137 modules and 366 dependencies in 0.09 s of analysis (about 0.3 s for the whole CLI run).

The first run had three findings that came from role mapping, not from the code. In each case the role was changed to match how the styleguide uses the code:
- Celery tasks had been mapped as outbound, but they are entry points.
- The Celery app module is the composition root.
- `django-filter` FilterSets are used inside selectors, so they belong to business.

Findings with the refined policy: 2 non-INFO findings, both confirmed against the source.
- **LAYER-001:** `emails.services` imports `emails.tasks` to schedule sending, and the task imports the service back (lazily) to do the work. This is a real two-way dependency between business and an entry point.
- **CYCLE-001:** `config.urls` imports the debug-toolbar setup, and the debug-toolbar settings import `config.env`, so the package and its subpackage form a real cycle.

The baseline, `newOnly` gate and injected violation behaved as intended:
- The baseline recorded 2 findings, and the gate then passed.
- Importing the S3 client into `files/apis.py` produced exactly one NEW LAYER-002 and failed the gate with exit 1.
- Reverting returned to a pass.

**False positives: 0.**

## Issues found and fixed during the pilot

| Issue | Action |
|---|---|
| Django's `tests.py` convention was analyzed as production code | Fixed: `tests.py` is excluded like `test_*.py`, `*_test.py` and `conftest.py` |
| A file such as `gunicorn.conf.py` became the module `gunicorn.conf`, which made `gunicorn` an owned package and would have made `import gunicorn` unresolved | Fixed: module names are built only from path segments that are identifiers. Such files, and Django migrations (`0001_initial.py`), are not units |
| Production code importing helpers from a `tests/` package (`common/factories.py` imports `utils.tests.faker`) failed as an unresolved import | Fixed: excluded test modules are remembered, and imports of them are counted in a diagnostic instead of failing |
| `from http import client` targeted `http`, which missed the `http.client` infrastructure entry | Fixed: for external `from pkg import name`, `pkg.name` is the target when it is itself an infrastructure entry |
| FastAPI parameters injected with `Depends(...)` would have counted as HTTP contract for FW-002 | Fixed: `Depends`/`Security` parameters (default value or `Annotated` metadata) are skipped. Documented in the Python binding |
| The "no distribution name" diagnostic was printed whenever the project root had no `pyproject.toml`, even when a nested `backend/pyproject.toml` supplied the module ID | Fixed: the diagnostic appears only when a module actually falls back to the directory name |
| Projects that need a newer Python syntax than the analyzer's interpreter cannot be parsed | Working as intended: exit 2 with a message to run ArchGuard on the project's Python version. Documented |
| Per-app Django layouts need role selectors keyed on module names (`**.services`, `**.apis`), and overlapping selectors across roles are rejected as ambiguous | Documented in the pilot policy. Unambiguous selectors were enough for all three projects. A precedence rule for overlapping selectors would need a spec change |

## Verdict

The step 10 exit criteria hold:
- Python conformance passes.
- The FastAPI and Django samples produce exactly the expected results, and their own test suites pass.
- The three public projects produce only true findings with no false positives once the policies follow each project's stated architecture.
