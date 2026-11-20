# archguard (Python)

ArchGuard checks that a codebase follows its declared architecture, such as hexagonal, layered, DDD bounded contexts or a modular monolith. It works the same whether a person or a coding agent wrote the code. This distribution is the Python analyzer. It reads the same `architecture.yml`, rule catalog, report formats and exit codes as the Java and TypeScript analyzers.

Requires Python 3.9 or later. It parses source code with the standard-library `ast` module. Project code is never imported or executed, and the project's own dependencies do not need to be installed.

## Install

```bash
pip install archguard            # or: uv add --dev archguard / poetry add --group dev archguard
```

## Policy

Put `architecture.yml` at the project root:

```yaml
schemaVersion: 2
language: python
roots: ["orders.**"]
profiles: [hexagonal, ddd]
roles:
  DOMAIN: ["orders.domain.**"]
  APPLICATION: ["orders.application.**"]
  OUTBOUND_PORT: ["orders.application.ports.**"]
  INBOUND_ADAPTER: ["orders.api.**"]
  OUTBOUND_ADAPTER: ["orders.infrastructure.**"]
  COMPOSITION_ROOT: ["orders.main"]
contexts:
  - id: orders
    packages: ["orders.**"]
    exposedPackages: ["orders.application.ports.**"]
requireClassification: true
newOnly: true
```

How selectors work:
- Selectors match dotted module names relative to the source root. `orders.domain.**` matches the package `orders.domain` and every module below it. `**` matches any number of segments and `*` matches exactly one.
- Forbidden selectors in `constraints` can name external modules, for example `requests` or `boto3.**`.

Optional settings:
- `sourceRoots`: defaults to `src` when it contains Python files, otherwise `.`. Use several roots for a monorepo (`["services/orders/src", "libs/shared/src"]`).
- `typeOnlyImports: count | ignore`: whether imports inside `if TYPE_CHECKING:` count. Defaults to `count`.
- `unresolvedImports: fail | warn`: defaults to `fail`.
- `extends: ["org:acme/base@1.0.0"]`: loads `presets/base/1.0.0.yml` from the installed package `acme_archguard_presets`.

## Commands

```bash
archguard validate                       # policy only
archguard analyze                        # report, never fails the build
archguard baseline                       # record existing debt (review, then commit)
archguard check --baseline architecture-baseline.json
archguard check --format agent --changed-files changed.txt   # for coding agents
archguard rules                          # rule catalog
```

Reports are written to `reports/archguard/`:
- `archguard.json`
- `archguard.sarif`
- `index.html`
- `archguard.agent.jsonl`, with `--format agent`

The exit codes are:
- `0`: pass;
- `1`: policy violation;
- `2`: the analysis could not run (never a pass);
- `64`: usage error.

## pre-commit

The hook reports only findings located in the staged files, while still analyzing the whole import graph:

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: archguard-check
        name: ArchGuard architecture check
        entry: archguard-pre-commit
        language: python
        additional_dependencies: ["archguard==0.1.0"]
        files: '(\.py|architecture\.yml)$'
        require_serial: true
```

If `archguard` is already installed in the development environment, you can instead reference this repository's hook (`id: archguard-check`, `language: system`). Extra options go before the file names, for example `args: [--baseline, architecture-baseline.json]`.

## What it sees

- Every import statement: absolute, relative, `from x import submodule`, star imports, lazy imports inside functions, `if TYPE_CHECKING:` imports, and `importlib.import_module` / `__import__` with a literal.
- Regular and namespace packages, `src` layouts and several source roots.
- Framework signals:
  - FastAPI, Flask (also Quart and APIFlask) and Django Ninja route handlers, with routers followed across modules;
  - Django views, Django REST Framework views and viewsets, and `urlpatterns`;
  - SQLAlchemy (2.0 `DeclarativeBase`, `declarative_base()`, Flask-SQLAlchemy `db.Model`), SQLModel `table=True`, Django, Tortoise, Peewee, MongoEngine, Beanie and ODMantic models;
  - Pydantic models.
- FW-002 finds FastAPI, Flask and Ninja handler signatures (parameters, return annotation, `response_model=`) that expose a persistence entity. It looks through `List[T]`, `Optional[T]`, `Annotated[T, ...]`, `T | None` and string annotations.

The full mapping is specified in [spec/languages/python.md](https://github.com/dmishra2022/archguard/blob/main/spec/languages/python.md).

Limits:
- Runtime plugin loading, computed `importlib` calls and string references (Django `INSTALLED_APPS`, Celery task names) are not resolved.
- A file that does not parse is an analysis error. Run ArchGuard with a Python version that supports the project's syntax.
- Run code generators (protobuf, OpenAPI clients) before analysis. Otherwise imports of generated modules are reported as unresolved.

## Development

```bash
python -m unittest discover -s tests          # uses ../../spec directly
python scripts/copy_spec.py && python -m build  # bundles the spec into the wheel
```
