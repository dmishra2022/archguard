# Getting support

## Before asking

1. Check [Troubleshooting](troubleshooting.md) and the [FAQ](faq.md).
2. Run `archguard validate` (TypeScript: `npx archguard validate`; Java: `java -jar archguard-cli-<version>.jar validate`) to rule out policy errors.
3. Note the analyzer version: `archguard --version` prints, for example, `archguard 0.1.0 (python analyzer, spec 2.0.0)`.

## Where to go

| Need | Channel |
|---|---|
| Question about adopting or configuring ArchGuard | Your organisation's internal channel first, otherwise a [question issue](https://github.com/dmishra2022/archguard/issues/new/choose) |
| Bug, false positive or false negative | A [bug or false-positive issue](https://github.com/dmishra2022/archguard/issues/new/choose) |
| Security vulnerability | Privately, as described in the [security policy](https://github.com/dmishra2022/archguard/blob/main/SECURITY.md); never in a public issue |
| Change to your organisation's preset | Your architecture owners |

## What to include in a bug report

- Analyzer and version (`archguard --version`), language version (JDK, Node.js or Python) and operating system.
- The relevant part of `architecture.yml` (roles, profiles, roots).
- The finding or error exactly as printed, including the evidence line, for example
  `Module <orders.web.routes> imports <orders.infrastructure.repo> (routes.py:6)`.
- What you expected and why.
- If you can, a minimal project that reproduces it. The [conformance cases](../spec/conformance/README.md) are good templates.

Do not attach proprietary source code to a public issue; reduce it to a minimal example.

## Service levels

ArchGuard is an open-source project. Responses on GitHub are best effort. Organisations that roll it out internally should name an owning platform team that triages internal reports first; see the roles table in the [adoption playbook](guides/adoption-playbook.md#roles-and-responsibilities).
