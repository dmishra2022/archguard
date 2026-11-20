# Quickstart: TypeScript / JavaScript

Time: about 10 minutes. You will run ArchGuard on a sample project, see violations, and then add it to your own project.

**Requirements:** Node.js 18 or later. ArchGuard reads your source with the TypeScript compiler API; it does not run or build your code, and it does not need your project's `node_modules` (except for organisation presets).

## 1. Try the sample

```bash
git clone https://github.com/dmishra2022/archguard.git
cd archguard/typescript/archguard-ts && npm ci && npm run build && cd -
cd archguard/examples/typescript-violating
node ../../typescript/archguard-ts/dist/cli.js check --format console
```

Expected output (abridged), exit code `1`:

```text
ArchGuard 0.1.0: 10 modules, 30 dependencies, 10 findings (4 new, 0 existing, 0 suppressed, 6 info)
ERROR FW-002 [NEW] src/orders/web/orders.controller#OrdersController.find:22 — HTTP contract exposes a persistence entity
ERROR HEX-001 [NEW] src/orders/domain/order:1 — Domain depends on an outer layer or framework
ERROR HEX-002 [NEW] src/orders/application/place-order:3 — Application depends on a concrete outer component
ERROR HEX-004 [NEW] src/orders/web/orders.controller:5 — Inbound and outbound adapters depend directly on each other
```

Each finding is followed by a suggested fix. INFO findings (framework evidence) are counted in the summary but listed only in the reports. The HTML report is at `reports/archguard/index.html`. Run the same command in `examples/typescript-clean` to see a pass.

## 2. Install in your project

```bash
npm install --save-dev archguard-cli
npm pkg set scripts.arch:check="archguard check"
```

!!! note
    Until 0.1.0 is on npm, install it from the clone in step 1: `npm install --save-dev <path-to>/archguard/typescript/archguard-ts`.

## 3. Write a starter policy

Copy [`architecture.typescript.yml`](https://github.com/dmishra2022/archguard/blob/main/skills/archguard/templates/architecture.typescript.yml) to `architecture.yml` at the project root. Selectors match **directories relative to the project root**: `src/orders/domain/**` covers that directory and everything below it, and `src/orders` (without `**`) covers only the files directly in it, such as `index.ts`.

```yaml
schemaVersion: 2
language: typescript
roots: ["src/**"]
profiles: [hexagonal]
roles:
  DOMAIN: ["src/orders/domain/**"]
  APPLICATION: ["src/orders/application"]
  OUTBOUND_PORT: ["src/orders/application/ports/**"]
  INBOUND_ADAPTER: ["src/orders/web/**"]
  OUTBOUND_ADAPTER: ["src/orders/infrastructure/**"]
  COMPOSITION_ROOT: ["src", "src/orders"]
requireClassification: true
newOnly: true
```

This minimal policy uses only `hexagonal`. The template also enables `ddd` and declares `contexts`; keep that if you have bounded contexts, otherwise remove `ddd` and the `contexts` block.

Path aliases from `tsconfig.json` (`paths`, `baseUrl`), project references and monorepo workspace packages are resolved automatically.

## 4. Run it in report-only mode

```bash
npx archguard validate      # checks the policy file itself
npx archguard analyze       # writes reports, never fails
```

Adjust the role selectors until no file is reported as unclassified (`MODEL-001`).

## Next steps

- Record existing violations as a baseline, add a pre-commit hook and the CI gate: [Onboarding a project](../ONBOARDING.md#4-capture-existing-debt).
- Understand each rule: [Rules](../RULES.md).
- Where new code should go for NestJS, Express, Next.js and others: [TypeScript placement guide](https://github.com/dmishra2022/archguard/blob/main/skills/archguard/reference/typescript-placement.md).
- Full analyzer reference: [archguard-cli for TypeScript](https://github.com/dmishra2022/archguard/blob/main/typescript/archguard-ts/README.md).
