# Security policy

## Supported versions

Security fixes are released for the latest minor version of the analyzers (`archguard-cli` on npm and PyPI, and the `io.archguard` Java artifacts).

## Reporting a vulnerability

Please report vulnerabilities privately through GitHub: open the repository's **Security** tab and choose **Report a vulnerability** ([direct link](https://github.com/dmishra2022/archguard/security/advisories/new)). Do not open a public issue.

Include the affected analyzer and version, a description of the impact, and steps or a minimal project to reproduce it. We aim to acknowledge reports within 5 working days and will agree a disclosure date with you once a fix is available.

## Scope

ArchGuard reads source code, bytecode and policy files and writes reports; it makes no network calls during analysis. Relevant issues include, for example, code execution or file writes outside the report directory triggered by a crafted project or policy, path traversal through policy references, and denial of service from small inputs. A policy file is trusted configuration: policy changes should be reviewed (see CODEOWNERS).
