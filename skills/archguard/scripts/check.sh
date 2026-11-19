#!/usr/bin/env bash
# Compile the project, run `archguard check --format agent` and pass its exit code through.
#
# Usage (from the project root, where architecture.yml lives):
#   check.sh             full check
#   check.sh --changed   only findings in files changed versus HEAD (tracked and untracked)
#   check.sh ... <args>  extra arguments are passed to the CLI (for example --baseline FILE)
#
# Exit codes: 0 pass, 1 policy violation, 2 analysis or build error (never a pass).
# Environment: ARCHGUARD_VERSION (default 0.1.0), ARCHGUARD_CLI (full command, overrides lookup),
# ARCHGUARD_CLI_JAR (path to archguard-cli jar), ARCHGUARD_CONFIG (policy file).
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

if [ -f pom.xml ]; then
  if ! mvn -q -B -DskipTests compile "io.archguard:archguard-maven-plugin:${VERSION}:classpath" >&2; then
    error "Maven compile failed; fix the compilation errors above, then re-run the check."
  fi
elif [ -f build.gradle ] || [ -f build.gradle.kts ]; then
  gradle_cmd=gradle
  [ -x ./gradlew ] && gradle_cmd=./gradlew
  if ! "$gradle_cmd" -q classes archguardClasspath >&2; then
    error "Gradle build failed (it needs the archguardClasspath task from docs/CLI.md)."
  fi
else
  error "No pom.xml or build.gradle found; this skill version supports Java projects only."
fi

classpath_args=()
while IFS= read -r file; do
  classpath_args+=(--classpath-file "$file")
done < <(find . \( -path '*/target/archguard.classpath' -o -path '*/build/archguard.classpath' \) -not -path '*/node_modules/*' | sort)
[ ${#classpath_args[@]} -gt 0 ] || error "No archguard.classpath file was produced by the build."

if [ -n "${ARCHGUARD_CLI:-}" ]; then
  read -r -a cli <<< "$ARCHGUARD_CLI"
else
  jar="${ARCHGUARD_CLI_JAR:-$HOME/.m2/repository/io/archguard/archguard-cli/${VERSION}/archguard-cli-${VERSION}.jar}"
  [ -f "$jar" ] || error "ArchGuard CLI jar not found at $jar. Set ARCHGUARD_CLI_JAR or install io.archguard:archguard-cli:${VERSION}."
  cli=(java -jar "$jar")
fi

args=(check --config "$CONFIG" --format agent "${classpath_args[@]}")
if $changed && git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  { git diff --name-only --relative HEAD; git ls-files --others --exclude-standard; } | sort -u \
    | "${cli[@]}" "${args[@]}" --changed-files - ${extra[@]+"${extra[@]}"}
else
  "${cli[@]}" "${args[@]}" ${extra[@]+"${extra[@]}"}
fi
