#!/usr/bin/env bash
# Resolve the analyzer language for the working directory and write it to $GITHUB_OUTPUT.
# Order: the `language` input, the policy's `language:` key, then the build files present.
set -euo pipefail

language="${INPUT_LANGUAGE:-auto}"
config="${INPUT_CONFIG:-architecture.yml}"
if [ "$language" = auto ] && [ -f "$config" ]; then
  declared=$(sed -n 's/^language:[[:space:]]*["'\'']\{0,1\}\([a-z]*\).*/\1/p' "$config" | head -1)
  [ -n "$declared" ] && language="$declared"
fi
if [ "$language" = auto ]; then
  if [ -f pom.xml ] || [ -f build.gradle ] || [ -f build.gradle.kts ]; then
    language=java
  elif [ -f tsconfig.json ] || [ -f package.json ]; then
    language=typescript
  elif [ -f pyproject.toml ] || [ -f setup.py ] || [ -f setup.cfg ]; then
    language=python
  else
    echo "::error title=ArchGuard::Cannot detect the project language in $(pwd); set 'language:' in the policy or the 'language' input."
    exit 2
  fi
fi
case "$language" in
  java | typescript | python) ;;
  *)
    echo "::error title=ArchGuard::Unknown language '$language' (expected java, typescript, python or auto)."
    exit 2 ;;
esac
echo "language=$language" >> "$GITHUB_OUTPUT"
echo "ArchGuard language: $language"
