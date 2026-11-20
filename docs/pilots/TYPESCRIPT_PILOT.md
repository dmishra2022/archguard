# TypeScript analyzer pilot (plan step 9)

The analyzer `@archguard/cli` (`typescript/archguard-ts`) was checked in four ways:
- the shared conformance suite;
- two NestJS examples in this repository;
- a public NestJS DDD/hexagonal project with real dependencies installed;
- a public Next.js App Router project without dependencies installed.

## Conformance

`python3 scripts/conformance.py --language typescript` passes all 8 cases: clean, hex-002, ddd-001, cycles, http-entity, unclassified, invalid-policy and layered. The cases cover three resolution set-ups on purpose:
- NodeNext resolution with `.js` specifiers (`clean`);
- a tsconfig `paths` alias (`hex-002`);
- CommonJS with decorators (`http-entity`).

Three cases (`unclassified`, `invalid-policy`, `layered`) have no tsconfig and use the default resolution. `unclassified` also includes a JavaScript module. The 19 unit tests pass on Node 18 and Node 22.

## Repository examples (NestJS)

| Example | Expected | Result |
|---|---|---|
| `examples/typescript-clean`: hexagonal and DDD orders service (controller, use case, port, TypeORM adapter, composition root) | pass | exit 0. 10 modules, 0 violations, 6 accurate MODEL-002 tags |
| `examples/typescript-violating`: the same service with a use case that injects the TypeORM repository, a controller that returns the entity and injects the TypeORM repository, and a domain that imports `@nestjs/common` | HEX-002, FW-002, HEX-004, HEX-001 | exit 1 with exactly those four findings |

## Public NestJS project: [Sairyss/domain-driven-hexagon](https://github.com/Sairyss/domain-driven-hexagon)

The project has 82 modules and a tsconfig with five `paths` aliases. It uses NestJS 9, CQRS, GraphQL and Slonik. Dependencies were installed (1,240 packages). The policy is in [domain-driven-hexagon/architecture.yml](domain-driven-hexagon/architecture.yml): `hexagonal` and `modular-monolith`, contexts `user` and `wallet` with only their domain events exposed, `DOMAIN` roles for the domain folders, and one custom constraint (`DDH-001`).

Timing: analysis took 1.5 s wall clock for 82 modules and 286 dependencies, including the type checker for FW-002.

Findings: 5 non-INFO findings, all confirmed against the source.
- **HEX-001:** `libs/ddd/aggregate-root.base.ts` imports `EventEmitter2` from `@nestjs/event-emitter`, so the DDD base class depends on the framework.
- **CYCLE-001 (×4), activated by `modular-monolith`:** these are real directory cycles.
  - `libs/ddd` and `libs/utils` import each other.
  - `user/domain` and `user/domain/events` import each other.
  - In each module, the module file at the module root ties together command, query and database folders, which import the DI tokens back from the root.
  - A team would baseline these or restructure the tokens.

There were no DDD-001 findings, which is correct: the only cross-context import is `wallet` using the exposed `UserCreatedDomainEvent`.

The baseline, `newOnly` gate and injected violation behaved as intended:
- The baseline recorded 5 findings, and the gate then passed.
- Injecting `import { UserRepository } from "@modules/user/database/user.repository"` into the wallet domain produced exactly 2 NEW findings, DDD-001 and DDH-001, and failed the gate with exit 1.
- Reverting returned to a pass.

**False positives: 0.**

## Public Next.js project: [shadcn-ui/taxonomy](https://github.com/shadcn-ui/taxonomy), no install

This run checked robustness on an App Router project with route groups (`app/(dashboard)/...`), catch-all segments, `@/*` aliases and Prisma, without `node_modules`. It analyzed 122 modules and 485 dependencies in about 1 s. The `route.ts` handlers and `pages/api` modules were tagged `next.endpoint`, and Prisma users were tagged `prisma.client`.

## Issues found and fixed during the pilot

| Issue | Action |
|---|---|
| Stylesheet imports (`@/styles/mdx.css`) were treated as unresolved code imports | Fixed: style, media, font and data imports are assets, counted in a diagnostic and not treated as dependencies |
| NestJS GraphQL resolvers were not recognised as endpoints | Fixed: `graphql.endpoint` tag for `@Resolver` from `@nestjs/graphql` or `type-graphql`, used by FW-001 |
| Without a `package.json` name the module ID is the directory name, so fingerprints depend on the checkout directory | Diagnostic added that asks for a package name. Documented in the TypeScript binding |
| Generated modules (`contentlayer/generated`) are unresolved until the generator runs | Working as intended: exit 2 with a message naming `unresolvedImports: warn`. Docs say to run code generators before analysis |
| Vertical-slice layouts (controller, service and repository in one folder) cannot get separate adapter roles from directory selectors | Documented limit. Contexts, `DOMAIN` roles and constraints still apply. A file-pattern selector would need a spec change |

## Verdict

The step 9 exit criteria hold: TypeScript conformance passes, and the NestJS samples and the public NestJS project produce the expected findings with no false positives.
