# Python placement guide

The project's `architecture.yml` is authoritative. Selectors match dotted module names relative to the source root (`sourceRoots`, default `src` when it holds Python files, otherwise `.`): `orders.domain.**` matches the package `orders.domain` and every module below it, `*` matches exactly one segment. A selector without `**` matches that module only (`orders.main`). The module names below are the conventional defaults from `templates/architecture.python.yml`; use whatever the policy declares.

A unit is one `.py` module. `orders/domain/__init__.py` is the module `orders.domain`, so a package's `__init__.py` takes the package's role: keep re-exports there consistent with that role.

## Where new code goes (hexagonal, clean)

| You are adding | Role | Conventional module | May import |
|---|---|---|---|
| Entity, value object (`@dataclass`, plain class), domain service, domain event | DOMAIN | `<pkg>.domain` | DOMAIN, ports, the standard library. No SQLAlchemy, Django, FastAPI, Pydantic or HTTP clients |
| Use case / application service | APPLICATION | `<pkg>.application` | DOMAIN, ports. Never a concrete adapter |
| Use-case protocol called by the outside (optional) | INBOUND_PORT | `<pkg>.ports.inbound` | DOMAIN, APPLICATION types. No framework imports |
| `Protocol` or `ABC` the core needs (repository, gateway, clock, publisher) | OUTBOUND_PORT | `<pkg>.ports` | DOMAIN. No framework imports |
| FastAPI router, Flask blueprint, Django view, CLI command, Celery task, consumer | INBOUND_ADAPTER | `<pkg>.web` (or `api`, `cli`, `tasks`) | APPLICATION, ports, DOMAIN, frameworks |
| SQLAlchemy/Django ORM repository, ORM models, HTTP client, message producer | OUTBOUND_ADAPTER | `<pkg>.infrastructure` | Ports (it implements them), DOMAIN, frameworks |
| App factory, `main.py`, dependency wiring, settings | COMPOSITION_ROOT | `<pkg>`, `<pkg>.main` | Everything; wires ports to adapters |

Adapters never import each other: an inbound adapter reaches an outbound adapter only through APPLICATION and an OUTBOUND_PORT (HEX-004). In FastAPI, the router's dependency provider (`def get_place_order() -> PlaceOrder`) lives in the adapter and returns an APPLICATION type; the composition root binds it to a use case built with the concrete adapter (`app.dependency_overrides[get_place_order] = lambda: PlaceOrder(repository)`).

## Recipes

**New database access** ("add a repository for X"):
1. OUTBOUND_PORT: `class XRepository(Protocol)` (or an `ABC`) in `<pkg>.ports`, using domain types only.
2. OUTBOUND_ADAPTER: `class SqlAlchemyXRepository` in `<pkg>.infrastructure`. ORM models (`DeclarativeBase`, `db.Model`, `SQLModel, table=True`, Django `models.Model`) stay in the adapter package and are mapped to domain objects there.
3. APPLICATION: the use case receives an `XRepository` in `__init__` (or as a function parameter).
4. COMPOSITION_ROOT: construct the adapter and pass it in.

**New HTTP endpoint**: route function in INBOUND_ADAPTER, Pydantic request/response schemas next to it, call an APPLICATION use case. Never use an ORM model as a parameter, return annotation or `response_model=` (FW-002); return a schema and map in the adapter. `Depends(...)`/`Security(...)` parameters are dependency injection, not payload, and are not checked.

**New external API call**: an OUTBOUND_PORT protocol in the core plus an OUTBOUND_ADAPTER client (`httpx`, `requests`, `boto3`) implementing it.

**Type hints across layers**: imports under `if TYPE_CHECKING:` still count as dependencies (unless the policy sets `typeOnlyImports: ignore`). Moving an import into a function body or `importlib.import_module("literal")` does not hide it either.

**Framework imports**: keep `sqlalchemy`, `django`, `fastapi`, `flask`, `pydantic`, `httpx`, `boto3` and similar out of DOMAIN and ports (HEX-001, HEX-003). APPLICATION may use infrastructure APIs under hexagonal (only DOMAIN and ports forbid them), but prefer a port when the project already does.

## Layered profile (typical Django or FastAPI project)

| Layer | Role | Typical modules | May import |
|---|---|---|---|
| Presentation | INBOUND_ADAPTER | `views`, `api`, `serializers`, `urls`, routers | APPLICATION, DOMAIN, ports. Not OUTBOUND_ADAPTER (LAYER-002) |
| Business | APPLICATION, ports, DOMAIN | `services`, `selectors`, `crud`, `models` | Each other and OUTBOUND_ADAPTER. Never INBOUND_ADAPTER (LAYER-001) |
| Persistence / integration | OUTBOUND_ADAPTER | `integrations`, `clients`, `db` | DOMAIN and ports only (LAYER-001) |
| Wiring | COMPOSITION_ROOT | `settings`, project `urls`, `wsgi`/`asgi`, `apps` | Everything |

In layered projects, Django or SQLAlchemy models are usually DOMAIN and may import the ORM. Project constraints often add rules such as "views must not import models" (reads go through selectors, writes through services); check `constraints` before importing.

## Bounded contexts (ddd, modular-monolith)

A module in context A may import context B only through B's `exposedPackages` (DDD-001), and context dependencies must stay acyclic (DDD-002). Import B's exposed ports or API module; never its domain, ORM models or adapters. If nothing suitable is exposed, stop and ask: exposing a package is a policy change.

## Unclassified code (MODEL-001)

With `requireClassification: true`, every module under `roots` must match a role, including `__init__.py` packages and helpers. Put new modules in a package that already maps to a role. If none fits, ask the user rather than creating a package the policy does not cover. Tests (`tests/`, `test_*.py`, `*_test.py`, `conftest.py`) are not analyzed.

## What the analyzer cannot see

Runtime plugin loading, computed `importlib` calls and string references (Django `INSTALLED_APPS`, Celery task names) are not dependencies to it. Do not use them to get around a rule: CI reviewers treat that as a violation.
