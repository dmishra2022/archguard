# TypeScript placement guide

The project's `architecture.yml` is authoritative. Selectors match a file's directory relative to the project root: `src/orders/domain/**` matches that directory and everything below it, `*` matches exactly one segment, and a selector without `**` matches that directory only (`src/orders/application` does not cover `src/orders/application/ports`). In a monorepo a selector can start with a workspace package name (`@acme/orders-domain/**`). The paths below are the conventional defaults from `templates/architecture.typescript.yml`; use whatever the policy declares.

Roles attach to directories, not files. Put files with different roles in different directories; a folder that mixes controllers, services and repositories cannot satisfy a hexagonal policy.

## Where new code goes (hexagonal, clean)

| You are adding | Role | Conventional directory | May import |
|---|---|---|---|
| Entity, value object, domain service, domain event | DOMAIN | `src/<ctx>/domain` | DOMAIN, ports. No NestJS, TypeORM, Prisma, Express or HTTP clients |
| Use case / application service | APPLICATION | `src/<ctx>/application` | DOMAIN, ports. Never a concrete adapter |
| Use-case interface called by the outside (optional) | INBOUND_PORT | `src/<ctx>/application/ports/inbound` | DOMAIN, APPLICATION types. No framework imports |
| Interface the core needs (repository, gateway, clock, publisher), plus its DI token | OUTBOUND_PORT | `src/<ctx>/application/ports` | DOMAIN. No framework imports |
| NestJS controller or resolver, Express/Fastify/Hono routes, Next.js route handler, queue consumer, domain-event subscriber that calls a use case | INBOUND_ADAPTER | `src/<ctx>/web` (or `http`, `graphql`, `subscribers`) | APPLICATION, ports, DOMAIN, frameworks |
| Request/response DTOs | INBOUND_ADAPTER, next to the controller | `src/<ctx>/web/dto` | As the controller |
| Use-case input/output types | APPLICATION | `src/<ctx>/application` | As the use case |
| Mappers between ORM entities and domain objects | OUTBOUND_ADAPTER, next to the repository | `src/<ctx>/infrastructure` | As the repository |
| TypeORM/MikroORM entity and repository, Prisma or Mongoose access, HTTP client | OUTBOUND_ADAPTER | `src/<ctx>/infrastructure` | Ports (it implements them), DOMAIN, frameworks |
| `main.ts`, Nest `AppModule` and feature modules, DI container setup | COMPOSITION_ROOT | `src`, `src/<ctx>` | Everything; binds ports to adapters |

Adapters never import each other: a controller reaches a repository only through APPLICATION and an OUTBOUND_PORT (HEX-004).

## Recipes

**New database access** ("add a repository for X"):
1. OUTBOUND_PORT: `export interface XRepository` and `export const X_REPOSITORY = Symbol('XRepository')` in `src/<ctx>/application/ports`, using domain types only.
2. OUTBOUND_ADAPTER: `class TypeOrmXRepository implements XRepository` in `src/<ctx>/infrastructure`, with the `@Entity` class next to it, mapped to domain objects there.
3. APPLICATION: the use case receives `XRepository` in its constructor. With NestJS, inject by token (`@Inject(X_REPOSITORY) private readonly xs: XRepository`). `@Injectable` on the use case is fine under hexagonal; never put `@nestjs/*` decorators in DOMAIN or ports.
4. COMPOSITION_ROOT: the feature module binds the token: `{ provide: X_REPOSITORY, useClass: TypeOrmXRepository }`.

**New HTTP endpoint**: controller in INBOUND_ADAPTER, request/response DTO classes next to it, call an APPLICATION use case. Never use an `@Entity` (TypeORM, MikroORM) or `@Schema` (Mongoose) class as a handler parameter or return type, including inside `Promise<...>`, arrays or generics (FW-002); return a DTO and map in the controller.

**New external API call**: an OUTBOUND_PORT interface in the core plus an OUTBOUND_ADAPTER client (`axios`, `fetch` wrapper, SDK) implementing it.

**Type-only imports count**: `import type { X } from '...'` is still a dependency (unless the policy sets `typeOnlyImports: ignore`). Path aliases from `tsconfig.json` `paths` resolve to the real directory, so an alias does not hide a dependency.

**Framework imports**: keep `@nestjs/*`, `typeorm`, `sequelize`, `@prisma/client`, `mongoose`, `express`, `axios` and similar out of DOMAIN and ports (HEX-001, HEX-003). The full default list is [`spec/infrastructure/typescript.yml`](../../../spec/infrastructure/typescript.yml); libraries not on it (validation libraries, vendor SDKs) are forbidden only if the policy adds a `constraints` entry for them.

## Layered profile

| Layer | Role | May import |
|---|---|---|
| Presentation (controllers, routes) | INBOUND_ADAPTER | APPLICATION, DOMAIN, ports. Not OUTBOUND_ADAPTER (LAYER-002) |
| Business (services) | APPLICATION, ports, DOMAIN | Each other and OUTBOUND_ADAPTER. Never INBOUND_ADAPTER (LAYER-001) |
| Persistence / integration | OUTBOUND_ADAPTER | DOMAIN and ports only (LAYER-001) |

## Bounded contexts (ddd, modular-monolith)

A file in context A may import context B only through B's `exposedPackages` (DDD-001), and context dependencies must stay acyclic (DDD-002). In a monorepo, import the other workspace package's public entry that the policy exposes, never deep paths into its domain or infrastructure. If nothing suitable is exposed, stop and ask: exposing a package is a policy change.

Files outside every context (for example `src/config` or `src/shared`) are not checked by DDD-001 or DDD-002; the role rules still apply to them. A shared kernel used by every context can be a context whose `exposedPackages` is `["src/shared/**"]` (everything), or stay outside the contexts.

## Unclassified code (MODEL-001)

With `requireClassification: true`, every analyzed file under `roots` must sit in a directory that matches a role, including `index.ts` barrels. Put new files in a directory that already maps to a role. If none fits, ask the user rather than creating a directory the policy does not cover. A directory holding only barrels or module wiring is usually COMPOSITION_ROOT.

Excluded from analysis: `*.test.*` and `*.spec.*` files, `__tests__` and `__mocks__` directories, `node_modules` and `.d.ts` files. Other test directories under `roots` (`tests/`, `test/`, `fixtures/`) are analyzed: give them a role (fakes of a port are usually OUTBOUND_ADAPTER) or keep them outside `roots`.

## Existing code that mixes roles

- **Interface and implementation in one file or directory**: classify the directory by its concrete part (OUTBOUND_ADAPTER); importers in the core then show up as HEX-002. Baseline them, and move the interface into a ports directory when you touch the code.
- **Vertical slices** (one directory per feature holding the controller, the use case and the repository): roles attach to directories, so a slice cannot be split by the policy. Either give each slice subdirectories (`features/orders/web`, `features/orders/application`) or classify the slice by its dominant role and baseline the rest.

## What the analyzer cannot see

Runtime DI containers resolving by string, computed `import(expr)` / `require(expr)` and module augmentation are not dependencies to it. Do not use them to get around a rule: CI reviewers treat that as a violation.

Run code generators (Prisma, GraphQL codegen) before the check; otherwise imports of generated modules are unresolved and the check exits 2.
