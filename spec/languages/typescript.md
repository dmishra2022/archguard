# TypeScript and JavaScript binding

How the language-neutral spec maps onto TypeScript and JavaScript projects. The reference implementation is `@archguard/cli` in [`typescript/archguard-ts`](../../typescript/archguard-ts).

## Units, names and containers

| Concept | TypeScript meaning |
|---|---|
| Unit | One source module (file). |
| Unit name (`origin`, `target`, `location.symbol`) | Project-relative POSIX path without the source extension: `src/orders/application/place-order`. |
| Member symbol | `<unit name>#<Class>.<method>` (used by FW-002). Tools that need the unit strip everything from `#`. |
| Container (for selectors) | The file's directory relative to the project root (`src/orders/application`). A file in a workspace package also has the container `<package name>/<directory within the package>`. A selector matches when it matches either form. |
| External target | The package name (`express`, `@nestjs/common`, `node:fs`). Its container is the package name, so constraints can forbid packages (`forbidden: ["lodash", "@aws-sdk/*"]`). |
| Module ID (`location.module`) | The `name` of the nearest `package.json` within the project, otherwise the project directory name. Set a package name so fingerprints stay stable across checkouts. |

## Sources

- Directories come from `sourceRoots` in the policy. The default is `src` when it exists, otherwise `.`.
- TypeScript files (`.ts`, `.tsx`, `.mts`, `.cts`) are always analyzed.
- JavaScript files (`.js`, `.jsx`, `.mjs`, `.cjs`) are analyzed when the tsconfig sets `allowJs`, or when there is no tsconfig.
- Excluded:
  - declaration files (`.d.ts`);
  - test files (`*.test.*`, `*.spec.*`);
  - `__tests__`, `__mocks__` and `node_modules`;
  - hidden directories;
  - build output directly under a package root (`dist`, `build`, `out`, `coverage`, `reports`, `target`).
- Module resolution uses `<project>/tsconfig.json` or the file passed to `--tsconfig`. It honours `extends`, `paths`, `baseUrl`, `moduleResolution` and project references. Each file is resolved with the options of the referenced config that includes it.
- Without a tsconfig the analyzer uses Bundler resolution with JavaScript enabled. Precision is lower, and a diagnostic says so.

## Dependencies

Each of these statically names a module and is one dependency edge:

| Source form | Evidence verb |
|---|---|
| `import ... from 'x'`, `import 'x'` | `imports` |
| `import type ... from 'x'`, or imports whose named bindings are all `type` | `imports type` |
| `export ... from 'x'` | `re-exports` |
| `export type ... from 'x'` | `re-exports type` |
| `require('x')`, `import x = require('x')` | `requires` |
| `import('x')` with a string literal | `dynamically imports` |
| `import('x').T` in a type position | `imports type` |

- Computed `import(expr)` and `require(expr)` are not resolved. They are counted in a diagnostic.
- Imports of styles, media, fonts and data files (`.css`, `.svg`, `.json`, and so on) are assets, not code dependencies. They are counted in a diagnostic.
- Type-only edges count unless `typeOnlyImports: ignore`.
- An import resolves to one of three things:
  - **An owned module:** a file inside the project and outside `node_modules`. Workspace packages are mapped to their source entry (`source`, then `types`/`main` with `dist/` replaced by `src/`, then `src/index`), so analysis works without a build or an install.
  - **An external package:** a bare specifier that resolves into `node_modules` or does not resolve at all.
  - **Unresolved:** a relative path, `paths` alias or workspace package specifier that does not resolve. This is an analysis error (exit 2) unless `unresolvedImports: warn`, in which case it is reported in diagnostics. Run code generators (Prisma, GraphQL codegen, contentlayer) before analysis.
- Evidence is `Module <origin> <verb> <target> (<file name>:<line>)`. The parenthesised location is removed by fingerprint normalization (see [FINGERPRINT.md](../FINGERPRINT.md)).

## Infrastructure

[`infrastructure/typescript.yml`](../infrastructure/typescript.yml) entries match the import specifier in three ways:
- exactly;
- as a prefix followed by `/`;
- for entries ending in `/*`, any package in that npm scope.

## Framework tags

Tags come from decorators and calls whose names resolve to imports of the listed packages, including namespace imports such as `nest.Controller`.

| Tag | Signal |
|---|---|
| `nest.endpoint` | Class decorated with `@Controller` from `@nestjs/common` |
| `nest.provider`, `nest.module` | `@Injectable`, `@Module` from `@nestjs/common` |
| `graphql.endpoint` | `@Resolver` from `@nestjs/graphql` or `type-graphql` |
| `express.endpoint`, `fastify.endpoint`, `koa.endpoint`, `hono.endpoint` | The module imports the framework (also type-only) and registers a route: `x.get('/path', ...)`, `post`, `put`, `patch`, `delete`, `all`, `options`, `head`, `route` |
| `next.endpoint` | `app/**/route.(ts\|js)` exporting `GET`, `POST`, `PUT`, `PATCH`, `DELETE`, `HEAD` or `OPTIONS`; or a default export under `pages/api/**` |
| `persistence.entity` | `@Entity` from `typeorm` or `@mikro-orm/*`; `@Schema` from `@nestjs/mongoose` |
| `mongoose.schema` | `new Schema(...)` from `mongoose` |
| `prisma.client` | A value import from `@prisma/client` |

FW-001 uses every `*.endpoint` tag.

FW-002 works through the type checker:
- It inspects NestJS handler methods, meaning methods decorated with `@Get`, `@Post`, `@Put`, `@Patch`, `@Delete`, `@Options`, `@Head` or `@All` inside a `@Controller` class.
- It collects the return type and every parameter type, unwrapping unions, intersections, arrays, `Promise<T>`, other generic arguments and type aliases.
- Every class tagged `persistence.entity` that it reaches is one finding. The origin is the controller module, the target is the entity module, and the symbol is the handler member.

## Known limits (stated in diagnostics)

- Runtime DI containers, computed dynamic imports, and module augmentation are not resolved.
- FW-002 covers NestJS handlers. Express, Fastify and Next.js handlers have untyped payloads at the routing layer.
- Role selectors work on directories. Projects that keep controllers, services and repositories in one folder (vertical slices) can use contexts, `DOMAIN` roles and constraints, but cannot separate adapter roles inside that folder.
