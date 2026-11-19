# Selectors

Selectors choose units by their **container name** (Java package, Python package/module path, TypeScript directory path). They never match class or function names.

## Neutral glob syntax (schemaVersion 2, all languages)

A selector is a sequence of segments separated by `.` (Java, Python) or `/` (TypeScript). A single selector must not mix both separators.

| Token | Meaning |
|---|---|
| `name` | A segment equal to `name` |
| `*` | Exactly one segment of any name |
| `**` | Zero or more segments |

Examples:

| Selector | Matches | Does not match |
|---|---|---|
| `com.acme.orders.**` | `com.acme.orders`, `com.acme.orders.domain.model` | `com.acme.ordersx` |
| `**.domain.**` | `a.domain`, `a.b.domain.c` | `a.domainx` |
| `com.acme.*.api` | `com.acme.orders.api` | `com.acme.orders.v1.api` |
| `orders.domain.**` (Python) | module `orders.domain.model` | `orders.domainx` |
| `src/orders/domain/**` (TS) | `src/orders/domain/order.ts` (container `src/orders/domain`) | `src/orders/domainx/a.ts` |

Matching is case-sensitive. A selector list matches when any element matches.

## Container names by language

- **Java**: the package name of the class (`com.acme.orders.domain` for `com.acme.orders.domain.Order`).
- **Python**: the dotted module name *including* the module itself for selectors, so `orders.domain.**` matches the module `orders.domain.model` and the package `orders.domain` (`__init__.py`). Module names are computed relative to the configured `sourceRoots`.
- **TypeScript**: the POSIX directory path of the file relative to the project root (`src/orders/domain` for `src/orders/domain/order.ts`). Selectors may alternatively name a workspace package (`@acme/orders-domain/**`), in which case the container is `<package name>/<directory within the package>`.

## Java legacy syntax (schemaVersion 1 and 2)

Java analyzers also accept ArchUnit package-matcher syntax. The two forms are equivalent:

| Neutral | ArchUnit |
|---|---|
| `com.acme.**` | `com.acme..` |
| `**.domain.**` | `..domain..` |
| `com.acme.*.api` | `com.acme.*.api` |

Converting `**` to ArchUnit: a leading `**.` becomes `..`, a trailing `.**` becomes `..`, an inner `.**.` becomes `..`. Other forms (for example capture groups) are Java-only and must not be used in policies intended to be shared across languages.

## Validation

Empty selectors, blank strings, selectors longer than 512 characters and syntactically invalid selectors are analysis errors. Unless `allowEmptySelectors: true`, every role, context `packages` list and constraint `from` list must match at least one analyzed unit.
