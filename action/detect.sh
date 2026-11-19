#!/usr/bin/env bash
# Resolve the analyzer language for the working directory and write it to $GITHUB_OUTPUT.
set -euo pipefail

language="${INPUT_LANGUAGE:-auto}"
if [ "$language" = auto ]; then
  if [ -f pom.xml ] || [ -f build.gradle ] || [ -f build.gradle.kts ]; then
    language=java
  elif [ -f package.json ]; then
    language=typescript
  elif [ -f pyproject.toml ] || [ -f setup.py ] || [ -f setup.cfg ]; then
    language=python
  else
    echo "::error title=ArchGuard::Cannot detect the project language in $(pwd); set the 'language' input."
    exit 2
  fi
fi
case "$language" in
  java) ;;
  python | typescript)
    echo "::error title=ArchGuard::The $language analyzer is not available in this version of the action."
    exit 2 ;;
  *)
    echo "::error title=ArchGuard::Unknown language '$language' (expected java or auto)."
    exit 2 ;;
esac
echo "language=$language" >> "$GITHUB_OUTPUT"
echo "ArchGuard language: $language"
