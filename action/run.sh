#!/usr/bin/env bash
# Build the project, run `archguard check`, write the job summary and outputs.
# Always exits 0 after recording exit-code; the action's last step applies the gate, so report
# uploads still run on violations and errors.
set -uo pipefail

ACTION_DIR="${GITHUB_ACTION_PATH:-$(cd "$(dirname "$0")" && pwd)}"
VERSION="${INPUT_ARCHGUARD_VERSION:-0.1.0}"
CONFIG="${INPUT_CONFIG:-architecture.yml}"
WORKDIR="$(pwd)"
ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
OUT="$WORKDIR/target/archguard"
OUTPUT_FILE="${GITHUB_OUTPUT:-/dev/null}"
SUMMARY_FILE="${GITHUB_STEP_SUMMARY:-/dev/null}"

finish() {
  local code="$1" status
  case "$code" in 0) status=passed ;; 1) status=failed ;; *) status=error; code=2 ;; esac
  {
    echo "exit-code=$code"
    echo "status=$status"
    echo "report-dir=$OUT"
    if [ -f "$OUT/archguard.sarif" ]; then echo "sarif=$OUT/archguard.sarif"; else echo "sarif="; fi
  } >> "$OUTPUT_FILE"
  python3 "$ACTION_DIR/summary.py" "$OUT/archguard.json" "$code" "${INPUT_ANNOTATIONS:-true}" \
    "$SUMMARY_FILE" "$OUTPUT_FILE" "${2:-}"
  exit 0
}

group() { echo "::group::$1"; }
endgroup() { echo "::endgroup::"; }

[ -f "$CONFIG" ] || finish 2 "Policy file $WORKDIR/$CONFIG not found."

# 1. Analyzer jar: explicit, Maven Central, or built from this action's source.
jar="${INPUT_CLI_JAR:-}"
if [ -z "$jar" ]; then
  jar="${RUNNER_TEMP:-/tmp}/archguard-cli-$VERSION.jar"
  url="https://repo1.maven.org/maven2/io/archguard/archguard-cli/$VERSION/archguard-cli-$VERSION.jar"
  if ! curl -fsSL -o "$jar" "$url" 2>/dev/null; then
    group "Build ArchGuard $VERSION from source (not on Maven Central)"
    built_ok=false
    for attempt in 1 2 3; do
      if mvn -B -q -ntp -f "$ACTION_DIR/../pom.xml" install -DskipTests; then built_ok=true; break; fi
      echo "Source build attempt $attempt failed; retrying (transient repository errors are common)."
      sleep $((attempt * 10))
    done
    if ! $built_ok; then
      endgroup
      finish 2 "Could not download or build archguard-cli $VERSION."
    fi
    endgroup
    built=$(ls "$ACTION_DIR"/../archguard-cli/target/archguard-cli-*.jar 2>/dev/null | grep -v original- | head -1)
    [ -n "$built" ] || finish 2 "archguard-cli jar was not produced by the source build."
    jar="$built"
    VERSION="$(basename "$jar" .jar)"
    VERSION="${VERSION#archguard-cli-}"
  fi
fi
[ -f "$jar" ] || finish 2 "archguard-cli jar not found: $jar"

# 2. Compile and describe modules and dependencies.
group "Compile and resolve the classpath"
if [ -f pom.xml ]; then
  mvn -B -q -ntp -DskipTests compile "io.archguard:archguard-maven-plugin:$VERSION:classpath" \
    || { endgroup; finish 2 "Maven compile failed."; }
else
  OUT="$WORKDIR/build/archguard"
  gradle_cmd=gradle
  [ -x ./gradlew ] && gradle_cmd=./gradlew
  "$gradle_cmd" -q -I "$ACTION_DIR/../skills/archguard/scripts/archguard.init.gradle" classes archguardClasspath \
    || { endgroup; finish 2 "Gradle build failed."; }
fi
endgroup

args=(check --project "$ROOT" --config "$WORKDIR/$CONFIG" --out "$OUT" --format json,sarif,html,console)
while IFS= read -r file; do
  args+=(--classpath-file "$file")
done < <(find . \( -path '*/target/archguard.classpath' -o -path '*/build/archguard.classpath' \) -not -path '*/node_modules/*' | sort)

baseline="${INPUT_BASELINE:-}"
[ -z "$baseline" ] && [ -f architecture-baseline.json ] && baseline=architecture-baseline.json
[ -n "$baseline" ] && args+=(--baseline "$WORKDIR/$baseline")
suppressions="${INPUT_SUPPRESSIONS:-}"
[ -z "$suppressions" ] && [ -f architecture-suppressions.json ] && suppressions=architecture-suppressions.json
[ -n "$suppressions" ] && args+=(--suppressions "$WORKDIR/$suppressions")
[ -n "${INPUT_FAIL_ON:-}" ] && args+=(--fail-on "$INPUT_FAIL_ON")

# 3. Pull-request scope: files changed relative to the merge base (repository-relative paths).
if [ "${INPUT_CHANGED_FILES_ONLY:-false}" = true ] && [ -n "${GITHUB_BASE_REF:-}" ]; then
  changed="${RUNNER_TEMP:-/tmp}/archguard-changed-files.txt"
  git -C "$ROOT" fetch -q --no-tags origin "$GITHUB_BASE_REF" 2>/dev/null || true
  base=$(git -C "$ROOT" merge-base "origin/$GITHUB_BASE_REF" HEAD 2>/dev/null || echo "origin/$GITHUB_BASE_REF")
  if git -C "$ROOT" diff --name-only "$base" HEAD > "$changed" 2>/dev/null; then
    echo "Changed-files scope: $(wc -l < "$changed" | tr -d ' ') file(s) since $base"
    args+=(--changed-files "$changed")
  else
    echo "::warning title=ArchGuard::Could not compute changed files; checking the whole project."
  fi
fi

group "archguard ${args[*]}"
java -jar "$jar" "${args[@]}"
code=$?
endgroup
finish "$code"
