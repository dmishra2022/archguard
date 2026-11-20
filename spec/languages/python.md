# Python binding

How the language-neutral spec maps onto Python projects. The reference implementation is the `archguard` distribution in [`python/archguard-py`](../../python/archguard-py). It parses sources with the standard-library `ast` module and never imports or executes project code.

## Units, names and containers

| Concept | Python meaning |
|---|---|
| Unit | One module (`.py` file). A package `__init__.py` is the unit named after the package. |
| Unit name (`origin`, `target`, `location.symbol`) | Dotted module name relative to its source root: `orders.application.place_order`; `orders/domain/__init__.py` is `orders.domain`. |
| Member symbol | `<unit name>#<function>` or `<unit name>#<Class>.<method>` (used by FW-002). Tools that need the unit strip everything from `#`. |
| Container (for selectors) | The module name itself ([SELECTORS.md](../SELECTORS.md)), so `orders.domain.**` matches the package `orders.domain` and every module below it. |
| Package (for CYCLE-001) | The package that contains the module: `orders.application` for `orders.application.place_order`, the package itself for an `__init__.py`. Top-level modules outside any package use their own name. |
| External target | The imported module as written: `requests`, `sqlalchemy.orm`, `fastapi` (for `from fastapi import APIRouter`). Its container is the same name, so constraints can forbid modules (`forbidden: ["boto3.**", "requests"]`). For `from pkg import name`, `pkg.name` becomes the target when it is itself an infrastructure entry (`from http import client` targets `http.client`). |
| Module ID (`location.module`) | `[project].name` (or `[tool.poetry].name`) of the nearest `pyproject.toml`, otherwise `[metadata] name` from `setup.cfg`, otherwise the project directory name with a diagnostic. Set a distribution name so fingerprints stay stable across checkouts. |

## Sources

- Directories come from `sourceRoots` in the policy. The default is `src` when it contains Python files, otherwise `.` (a diagnostic states the detected value).
- Excluded:
  - test modules (`test_*.py`, `*_test.py`, `tests.py`, `conftest.py`) and `test`, `tests` and `testing` directories;
  - hidden directories (`.venv`, `.tox`, `.git`, ...), `__pycache__`, `venv`, `env`, `site-packages`, `node_modules`, `*.egg-info`;
  - build and report output (`build`, `dist`, `htmlcov`, `reports`, `target`).
- Files whose path is not a valid dotted module name (for example `my-script.py`, or Django migrations such as `0001_initial.py`) are not units.
- Two source roots that define the same module name are an analysis error.
- Namespace packages (directories without `__init__.py`) are supported. Importing a namespace package itself is not a dependency because it has no code; a diagnostic counts such imports.
- A file that does not parse is an analysis error (exit 2). Run ArchGuard with a Python version that supports the project's syntax.

## Dependencies

Each import statement, at module level or nested inside functions, classes and conditionals, is a dependency:

| Source form | Evidence verb |
|---|---|
| `import a.b`, `import a.b as c` | `imports` (target `a.b`) |
| `from a.b import c` where `a.b.c` is an owned module | `imports` (target `a.b.c`) |
| `from a.b import name`, `from a.b import *` | `imports` (target `a.b`) |
| Relative imports (`from ..port import store`) | Resolved against the importing module's package, then as above |
| Any of the above inside `if TYPE_CHECKING:` (or `typing.TYPE_CHECKING`) | `imports type` |
| `importlib.import_module('a.b')`, `__import__('a.b')` with a string literal | `dynamically imports` |

- Computed dynamic imports are not resolved. They are counted in a diagnostic.
- Type-only edges count unless `typeOnlyImports: ignore`.
- An import resolves to one of three things:
  - **An owned module:** a module discovered under the source roots.
  - **An external module:** any module whose top-level package is not owned (standard library, installed distributions).
  - **Unresolved:** a module under an owned top-level package that does not exist, or a relative import that climbs above the top-level package. This is an analysis error (exit 2) unless `unresolvedImports: warn`, in which case it is reported in diagnostics. Run code generators (protobuf, OpenAPI clients) before analysis.
- Evidence is `Module <origin> <verb> <target> (<file name>:<line>)`. The parenthesised location is removed by fingerprint normalization (see [FINGERPRINT.md](../FINGERPRINT.md)).

## Infrastructure

[`infrastructure/python.yml`](../infrastructure/python.yml) entries match the imported module exactly or as a parent package (`entry + "."`), so `sqlalchemy` matches `sqlalchemy.orm` but not `sqlalchemyx`.

## Framework tags

Names are resolved statically through the module's imports, including re-exports through owned packages and aliases (`from fastapi import APIRouter as R`). Router objects are followed to the assignment that creates them, also across modules (`from app.api.deps import router`).

| Tag | Signal |
|---|---|
| `fastapi.endpoint` | A function decorated with `@x.get/post/put/patch/delete/options/head/trace/api_route/websocket(...)` where `x` is created by `FastAPI()` or `APIRouter()` (or a subclass), or the module imports `fastapi` and `x` is a plain name |
| `flask.endpoint` | Same for `Flask()`, `Blueprint()`, Quart and APIFlask objects with `route/get/post/put/patch/delete`; classes deriving from `flask.views.MethodView` or `View` |
| `ninja.endpoint` | Same for `NinjaAPI()` and `Router()` from `ninja` |
| `django.endpoint` | Classes deriving from `django.views.*`, `rest_framework.views.*`, `rest_framework.viewsets.*` or `rest_framework.generics.*` (directly or through owned base classes); functions decorated with `@api_view`; modules named `views` that import Django and define functions |
| `django.routing` | A module-level `urlpatterns` assignment |
| `persistence.entity` | A mapped ORM class (see below) |
| `pydantic.model` | A class deriving from `pydantic.BaseModel` or `ninja.Schema` |

A class is a **persistence entity** when it is:
- a SQLAlchemy mapped class: it derives from a declarative base (`DeclarativeBase`, `declarative_base()`, `registry().generate_base()`, Flask-SQLAlchemy `db.Model`) and is not `__abstract__`, and it declares `__tablename__`/`__table__`, a `Mapped[...]` attribute or a `Column`/`mapped_column` attribute; or it derives from another mapped class;
- an SQLModel class declared with `table=True`;
- a non-abstract subclass of `django.db.models.Model`, `tortoise.models.Model`, `peewee.Model`, `mongoengine.Document`, `beanie.Document` or `odmantic.Model`.

FW-001 uses every `*.endpoint` tag.

FW-002 inspects FastAPI, Flask and Ninja route handlers (module-level functions and methods). It collects parameter and return annotations plus the `response_model=` / `response=` decorator arguments. Parameters injected with `Depends(...)` or `Security(...)` (as a default value or as `Annotated[T, Depends(...)]` metadata) are server-side dependencies, not part of the HTTP contract, and are skipped. Type aliases (`CurrentUser = Annotated[User, Depends(...)]`) are not followed. It unwraps generics (`List[T]`, `list[T]`, `Optional[T]`, `Annotated[T, ...]`), unions (`T | None`) and string annotations. Every persistence entity that it reaches is one finding. The origin is the handler module, the target is the entity module, and the symbol is the handler (`<module>#<function>`).

## Known limits (stated in diagnostics)

- Runtime plugin loading, `importlib` calls with computed names and string-based framework references (Django `INSTALLED_APPS`, `ROOT_URLCONF`, Celery task names) are not resolved.
- FW-002 does not inspect Django REST Framework serializers (`Meta.model`) or Django views, whose payloads are not typed in signatures.
- Names bound only at runtime (`setattr`, star imports used for re-export, monkey patching) are not followed when resolving framework classes.
- Role selectors work on modules. Projects that keep views, services and models in one module can use contexts, `DOMAIN` roles and constraints, but cannot separate adapter roles inside that module.
