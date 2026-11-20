# Fingerprints, ordering and deduplication

## Fingerprint

A finding's fingerprint identifies a violation independently of source line movement.

```
key = ruleId + "\n" + module + "\n" + origin + "\n" + target + "\n" + normalize(evidence)
fingerprint = lowercase_hex(SHA-256(UTF-8(key)))        # 64 characters
```

- `module`: the analyzed module ID (`Location.module`), for example `com.acme:orders` (Maven), the distribution name (Python) or the workspace package name (TypeScript).
- `origin`, `target`: fully qualified unit or symbol names of the dependency.
- `evidence`: the raw evidence string before rule-specific prefixes are applied (see the rule catalog for the evidence template of each rule).

### Evidence normalization

`normalize` replaces every parenthesised source location of the form `(<anything without parentheses>.<ext>:<digits>)` with the literal `(source)`. The extensions are language-specific:

| Language | Regex (Java syntax) |
|---|---|
| Java | `\([^()]*\.java:[0-9]+\)` |
| Python | `\([^()]*\.py:[0-9]+\)` |
| TypeScript | `\([^()]*\.(?:ts\|tsx\|mts\|cts\|js\|jsx\|mjs\|cjs):[0-9]+\)` |

Analyzers must not embed line numbers in evidence in any other form, otherwise fingerprints become line-sensitive.

## Deduplication

Findings with equal fingerprints are collapsed, keeping the first one produced.

## Ordering

Findings are sorted by `ruleId`, then `location.module`, then `location.symbol`, then `fingerprint`, all by Unicode code point. Diagnostics keep production order.

## Cycle findings

For `DDD-002` (context graph) and `CYCLE-001` (container graph):

1. Build a directed graph from owned-to-owned dependencies, mapping each endpoint to its context or container and skipping self-edges and empty names.
2. The witness for an edge `x -> y` is the first dependency, in model order, that produced it. Model order sorts dependencies by origin, target, then evidence.
3. Compute strongly connected components with more than one member. Members are sorted; components are sorted by their first member.
4. One finding per component. `{component}` renders as `[a, b, c]`. `{edges}` lists, for each member `x` in sorted order and each sorted neighbour `y` inside the component, `x -> y`, joined by `, `.
5. The finding's origin, target and location come from the witness of the first listed edge.

## Policy hash

`policyHash` is an opaque, canonical (map and set order independent) SHA-256 over the analyzer engine version and the fully resolved policy. It is analyzer-specific and only compared against baselines produced by the same analyzer.
