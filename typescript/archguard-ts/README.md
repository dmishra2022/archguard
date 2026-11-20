# @archguard/cli (TypeScript and JavaScript)

ArchGuard checks that a codebase follows its declared architecture, such as hexagonal, layered, DDD bounded contexts or a modular monolith. It works the same whether a person or a coding agent wrote the code. This package is the TypeScript/JavaScript analyzer. It reads the same `architecture.yml`, rule catalog, report formats and exit codes as the Java and Python analyzers.

Requires Node.js 18 or later. It analyzes source code statically with the TypeScript compiler API. Nothing is executed, and no build step is needed.

## Install

```bash
npm install --save-dev @archguard/cli
```

## Policy

Put `architecture.yml` at the project root:

```yaml
schemaVersion: 2
language: typescript
roots: ["src/**"]
profiles: [hexagonal, ddd]
roles:
  DOMAIN: ["src/orders/domain/**"]
  APPLICATION: ["src/orders/application"]
  OUTBOUND_PORT: ["src/orders/application/ports/**"]
  INBOUND_ADAPTER: ["src/orders/web/**"]
  OUTBOUND_ADAPTER: ["src/orders/infrastructure/**"]
  COMPOSITION_ROOT: ["src", "src/orders"]
contexts:
  - id: orders
    packages: ["src/orders/**"]
    exposedPackages: ["src/orders/application/ports/**"]
requireClassification: true
newOnly: true
```

How selectors work:
- Selectors match directories relative to the project root. `**` matches any number of segments and `*` matches exactly one.
- In a monorepo, a selector can also start with a workspace package name, for example `@acme/orders-domain/**`.
- Forbidden selectors in `constraints` can name npm packages, for example `lodash` or `@aws-sdk/*`.

Optional settings:
- `sourceRoots`: defaults to `src`, or `.` when there is no `src`.
- `typeOnlyImports: count | ignore`: defaults to `count`.
- `unresolvedImports: fail | warn`: defaults to `fail`.
- `extends: ["org:acme/base@1.0.0"]`: loads `presets/base/1.0.0.yml` from the installed package `@acme/archguard-presets`.

## Commands

```bash
npx archguard validate                       # policy only
npx archguard analyze                        # report, never fails the build
npx archguard baseline                       # record existing debt (review, then commit)
npx archguard check --baseline architecture-baseline.json
npx archguard check --format agent --changed-files changed.txt   # for coding agents and pre-commit
npx archguard rules                          # rule catalog
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

## What it sees

- Static imports of every form: `import`, `import type`, `export ... from`, `require`, `import()` with a literal, and `import('x').T`.
- Module resolution through your `tsconfig.json`: `paths`, `baseUrl`, `moduleResolution` and project references.
- Monorepo workspace packages, which map to their sources.
- Framework signals:
  - NestJS controllers, providers and modules;
  - GraphQL resolvers;
  - Express, Fastify, Koa and Hono routes;
  - Next.js route handlers and `pages/api`;
  - TypeORM and MikroORM entities;
  - Mongoose schemas;
  - Prisma client usage.
- FW-002 finds NestJS handler signatures that expose a persistence entity. It uses the type checker and looks through `Promise<T>`, arrays, unions and generics.

The full mapping is specified in [spec/languages/typescript.md](https://github.com/dmishra2022/archguard/blob/main/spec/languages/typescript.md).

Limits:
- Runtime DI containers, computed dynamic imports and module augmentation are not resolved.
- Run code generators (Prisma, GraphQL codegen) before analysis. Otherwise imports of generated modules are reported as unresolved.
