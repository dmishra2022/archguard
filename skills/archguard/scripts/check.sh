#!/usr/bin/env bash
# Run `archguard check --format agent` for the project in the current directory and pass its exit
# code through. Java projects are compiled first; TypeScript and Python are analyzed from source.
#
# Usage (from the project root, where architecture.yml lives):
#   check.sh             full check
#   check.sh --changed   only findings in files changed versus HEAD (tracked and untracked)
#   check.sh ... <args>  extra arguments are passed to the CLI (for example --baseline FILE)
#
# Exit codes: 0 pass, 1 policy violation, 2 analysis or build error (never a pass).
# Environment:
#   ARCHGUARD_CONFIG     policy file (default architecture.yml)
#   ARCHGUARD_LANGUAGE   java | typescript | python (default: the policy's `language`, else detected)
#   ARCHGUARD_CLI        full analyzer command, overrides the lookup below
#   ARCHGUARD_VERSION    Java analyzer version (default 0.1.0)
#   ARCHGUARD_CLI_JAR    path to the archguard-cli jar (Java)
set -uo pipefail

VERSION="${ARCHGUARD_VERSION:-0.1.0}"
CONFIG="${ARCHGUARD_CONFIG:-architecture.yml}"
changed=false
extra=()
for arg in "$@"; do
  case "$arg" in
    --changed) changed=true ;;
    *) extra+=("$arg") ;;
  esac
done

error() {
  python3 -c 'import json,sys; print(json.dumps({"summary": True, "status": "ERROR", "error": sys.argv[1]}))' "$1"
  exit 2
}

[ -f "$CONFIG" ] || error "$CONFIG not found in $(pwd). Ask the user for the architecture policy; do not invent one."

language="${ARCHGUARD_LANGUAGE:-}"
[ -n "$language" ] || language=$(sed -n 's/^language:[[:space:]]*["'\'']\{0,1\}\([a-z]*\).*/\1/p' "$CONFIG" | head -1)
if [ -z "$language" ]; then
  if [ -f pom.xml ] || [ -f build.gradle ] || [ -f build.gradle.kts ]; then language=java
  elif [ -f package.json ] || [ -f tsconfig.json ]; then language=typescript
  elif [ -f pyproject.toml ] || [ -f setup.py ] || [ -f setup.cfg ]; then language=python
  else error "Cannot tell the project language; set language: in $CONFIG or ARCHGUARD_LANGUAGE."
  fi
fi

cli=()
[ -n "${ARCHGUARD_CLI:-}" ] && read -r -a cli <<< "$ARCHGUARD_CLI"
args=(check --config "$CONFIG" --format agent)

case "$language" in
  java)
    OUT=target/archguard
    if [ -f pom.xml ]; then
      if ! mvn -q -B -DskipTests compile "io.archguard:archguard-maven-plugin:${VERSION}:classpath" >&2; then
        error "Maven compile failed; fix the compilation errors above, then re-run the check."
      fi
    elif [ -f build.gradle ] || [ -f build.gradle.kts ]; then
      OUT=build/archguard
      gradle_cmd=gradle
      [ -x ./gradlew ] && gradle_cmd=./gradlew
      if ! "$gradle_cmd" -q -I "$(dirname "$0")/archguard.init.gradle" classes archguardClasspath >&2; then
        error "Gradle build failed; fix the errors above, then re-run the check."
      fi
    else
      error "No pom.xml or build.gradle found for this Java policy."
    fi
    found=false
    while IFS= read -r file; do
      args+=(--classpath-file "$file"); found=true
    done < <(find . \( -path '*/target/archguard.classpath' -o -path '*/build/archguard.classpath' \) -not -path '*/node_modules/*' | sort)
    $found || error "No archguard.classpath file was produced by the build."
    args+=(--out "$OUT")
    if [ ${#cli[@]} -eq 0 ]; then
      jar="${ARCHGUARD_CLI_JAR:-$HOME/.m2/repository/io/archguard/archguard-cli/${VERSION}/archguard-cli-${VERSION}.jar}"
      [ -f "$jar" ] || error "ArchGuard CLI jar not found at $jar. Set ARCHGUARD_CLI_JAR or install io.archguard:archguard-cli:${VERSION}."
      cli=(java -jar "$jar")
    fi
    ;;
  typescript)
    if [ ${#cli[@]} -eq 0 ]; then
      if [ -x node_modules/.bin/archguard ]; then cli=(node_modules/.bin/archguard)
      elif command -v archguard >/dev/null 2>&1 && archguard --version 2>/dev/null | grep -qi typescript; then cli=(archguard)
      else error "The TypeScript analyzer is not installed. Ask the user to run: npm install --save-dev archguard-cli"
      fi
    fi
    ;;
  python)
    if [ ${#cli[@]} -eq 0 ]; then
      if command -v archguard >/dev/null 2>&1 && archguard --version 2>/dev/null | grep -qi python; then cli=(archguard)
      elif python3 -m archguard --version 2>/dev/null | grep -qi python; then cli=(python3 -m archguard)
      else error "The Python analyzer is not installed. Ask the user to add archguard-cli to the dev dependencies (pip install archguard-cli)."
      fi
    fi
    ;;
  *) error "Unknown language '$language' (expected java, typescript or python)." ;;
esac

if $changed && git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  { git diff --name-only --relative HEAD; git ls-files --others --exclude-standard; } | sort -u \
    | "${cli[@]}" "${args[@]}" --changed-files - ${extra[@]+"${extra[@]}"}
else
  "${cli[@]}" "${args[@]}" ${extra[@]+"${extra[@]}"}
fi
