# Third-party components

This source distribution does not bundle dependency JARs. Maven resolves them using their published metadata and licenses.

- ArchUnit 1.4.1: structural Java bytecode analysis (Apache-2.0).
- Jackson 2.18.3 / SnakeYAML transitive dependency: JSON/YAML configuration and reporting (consult their published license files).
- Apache Maven APIs and Plugin Tools: Maven integration (Apache-2.0).
- JUnit 5.11.4: tests (EPL-2.0).
- Spring, Jakarta/Javax APIs and Quarkus: test fixtures and example applications; consult each artifact's published license.

Versions are pinned for reproducibility. Dependency vulnerability scanning and organizational license review are separate release gates and are not claimed by compilation/test results.
