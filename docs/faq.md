# FAQ

## General

**Is ArchGuard only for AI-generated code?**
No. It checks the code itself, whoever wrote it. The agent skill is an optional extra for teams using coding agents.

**Does it send code anywhere?**
No. Analysis is fully offline: no network calls and no telemetry. Reports are written to local files. Package managers may download the analyzer itself when you install it.

**Does it change my code?**
Never. It only reads source or bytecode and writes reports.

**How is this different from ArchUnit, dependency-cruiser or import-linter?**
Those are excellent single-language tools where you write rules in code or language-specific configuration. ArchGuard gives one declarative policy model (roles, profiles, bounded contexts) with the same rules, fingerprints, baselines, reports and exit codes for Java, TypeScript/JavaScript and Python, plus organisation-wide presets with locked rules. If one team already uses one of those tools happily, there is no need to switch; ArchGuard is aimed at organisations that want one standard across languages.

**Which architecture styles are supported?**
Hexagonal (ports and adapters), clean, classic layered, DDD bounded contexts and modular monolith. Custom forbidden-dependency constraints cover project-specific rules in every language; Java additionally supports custom rule packs.

## Adoption

**Our code does not follow the architecture yet. Can we still adopt it?**
Yes, that is the normal case. Run report-only, then record existing violations in a [baseline](guides/baselines-and-suppressions.md). From then on only new violations fail.

**How long does onboarding take?**
About half a day per service: most of it is mapping packages or directories to roles and reviewing the first report. The [quickstarts](getting-started/python.md) take 10 minutes.

**Do we have to restructure folders to match ArchGuard?**
No. Selectors map whatever structure you have to roles. A folder that mixes roles (for example a `repos/` folder holding both interfaces and implementations) can be classified file by file in TypeScript and module by module in Python, or baselined until it is split.

**Can we use it in a monorepo?**
Yes. Each project has its own `architecture.yml`. In GitHub Actions, add one step per project with its own `working-directory` and `artifact-name`. TypeScript selectors can also start with a workspace package name.

**Which CI systems are supported?**
Anything that runs a command and reads an exit code. There is a GitHub Action, and [CI integration](CI.md) has recipes for GitLab, Jenkins and Azure Pipelines.

## Behaviour

**Why did the check fail with exit 2 instead of passing?**
ArchGuard refuses to report compliance when it could not analyze everything it was asked to: an invalid policy, a selector that matches nothing, an unresolved import of your own code, a missing preset. See [Troubleshooting](troubleshooting.md).

**Does it slow down the build?**
Analysis is static and fast: seconds for typical services. It does not compile (TypeScript, Python) or run tests. Java analyzes already compiled classes.

**Does it understand dependency injection, reflection or dynamic imports?**
It sees static dependencies: imports, type references and framework annotations or decorators. It does not see wiring decided at runtime, reflection, or imports with computed names; the report's diagnostics count what was skipped. Reviewers should treat code that hides dependencies as a violation of intent.

**Will upgrading ArchGuard break our build?**
A new analyzer version can find more (a minor spec change may change detection), and baselines are bound to the analyzer version. Upgrade in a pull request that also regenerates the baseline. See [Compatibility and versioning](reference/compatibility.md).

**Why are the npm and PyPI packages called `archguard-cli`?**
The names `archguard` (PyPI) and `@archguard/cli` (npm) belong to unrelated projects. Install `archguard-cli` on both.
