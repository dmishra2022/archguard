# Java placement guide

The project's `architecture.yml` is authoritative: map a package to a role by reading its `roles` selectors (`**` = any number of package segments, `*` = one segment). The package names below are the conventional defaults from `templates/architecture.java.yml`; use whatever the policy declares.

## Where new code goes (hexagonal, clean)

| You are adding | Role | Conventional package | May depend on |
|---|---|---|---|
| Entity, value object, domain service, domain event | DOMAIN | `<base>.domain` | DOMAIN, ports. No framework or persistence APIs |
| Use case / application service | APPLICATION | `<base>.application` | DOMAIN, ports. Never a concrete adapter |
| Use-case interface called by the outside (optional) | INBOUND_PORT | `<base>.port.inbound` | DOMAIN, APPLICATION types. No framework APIs |
| Interface the core needs from the outside (repository, gateway, clock, publisher) | OUTBOUND_PORT | `<base>.port.outbound` | DOMAIN. No framework APIs |
| REST controller, message listener, CLI command, scheduled job | INBOUND_ADAPTER | `<base>.adapter.inbound` | APPLICATION, ports, DOMAIN, frameworks |
| JPA/JDBC repository implementation, HTTP client, message producer | OUTBOUND_ADAPTER | `<base>.adapter.outbound` | Ports (it implements them), DOMAIN, frameworks |
| Spring `@Configuration`, Quarkus producers, Micronaut factories, `main` | COMPOSITION_ROOT | `<base>.config` | Everything; wires ports to adapters |

Adapters never call each other: an inbound adapter reaches an outbound adapter only through APPLICATION and an OUTBOUND_PORT (HEX-004).

## Recipes

**New database access** ("add a repository for X"):
1. OUTBOUND_PORT: `interface XRepository` in the core, using domain types only.
2. OUTBOUND_ADAPTER: `class JpaXRepository implements XRepository`. JPA entities and Spring Data interfaces stay in the adapter package and are mapped to domain objects there.
3. APPLICATION: the use case receives `XRepository` through its constructor.
4. COMPOSITION_ROOT: wire the adapter (or rely on framework scanning of the adapter package).

**New HTTP endpoint**: controller in INBOUND_ADAPTER, request/response DTOs next to it, call an APPLICATION use case. Never return or accept `@Entity` types from endpoint methods (FW-002). This includes server-side MVC form binding (`@ModelAttribute Owner owner`); use a form object and map it.

**New external API call**: an OUTBOUND_PORT interface in the core plus an OUTBOUND_ADAPTER client implementing it.

**Framework annotations**: keep `jakarta.persistence`, `org.springframework`, `io.quarkus`, `io.micronaut`, JAX-RS and similar out of DOMAIN and ports (HEX-001, HEX-003). `@Transactional` on an APPLICATION service is allowed by hexagonal (only DOMAIN and ports forbid infrastructure), but prefer configuring transactions at the composition root when the project already does.

## Layered profile

| Layer | Role | May depend on |
|---|---|---|
| Presentation (controllers) | INBOUND_ADAPTER | APPLICATION, DOMAIN, ports. Not OUTBOUND_ADAPTER (LAYER-002) |
| Business (services) | APPLICATION, ports, DOMAIN | Each other and OUTBOUND_ADAPTER. Never INBOUND_ADAPTER (LAYER-001) |
| Persistence / integration | OUTBOUND_ADAPTER | DOMAIN and ports only (LAYER-001) |

## Bounded contexts (ddd, modular-monolith)

A class in context A may use context B only through B's `exposedPackages` (DDD-001), and context dependencies must stay acyclic (DDD-002). To use another context, call its exposed port or API package; never import its domain or adapters. If nothing suitable is exposed, stop and ask: exposing a package is a policy change.

## Unclassified code (MODEL-001)

With `requireClassification: true`, every class under `roots` must match a role. Put new classes in a package that already maps to a role. If none fits, ask the user rather than adding a package the policy does not cover.
