#!/usr/bin/env bash
# Install the analyzer for ARCHGUARD_LANGUAGE, run `archguard check`, write the job summary and outputs.
# Always exits 0 after recording exit-code; the action's last step applies the gate, so report
# uploads still run on violations and errors.
set -uo pipefail

ACTION_DIR="${GITHUB_ACTION_PATH:-$(cd "$(dirname "$0")" && pwd)}"
SOURCE_DIR="$(cd "$ACTION_DIR/.." && pwd)"
LANGUAGE="${ARCHGUARD_LANGUAGE:-java}"
VERSION="${INPUT_ARCHGUARD_VERSION:-0.1.0}"
CONFIG="${INPUT_CONFIG:-architecture.yml}"
WORKDIR="$(pwd)"
ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
OUT="$WORKDIR/target/archguard"
[ "$LANGUAGE" = java ] || OUT="$WORKDIR/reports/archguard"
TMP="${RUNNER_TEMP:-/tmp}"
OUTPUT_FILE="${GITHUB_OUTPUT:-/dev/null}"
SUMMARY_FILE="${GITHUB_STEP_SUMMARY:-/dev/null}"
# TypeScript and Python report paths relative to the analyzed project; GitHub needs repository paths.
PATH_PREFIX=""
if [ "$LANGUAGE" != java ]; then
  PATH_PREFIX=$(python3 -c 'import os,sys; r=os.path.relpath(os.path.realpath(sys.argv[1]), os.path.realpath(sys.argv[2])); print("" if r == "." else r.replace(os.sep, "/") + "/")' "$WORKDIR" "$ROOT")
fi

finish() {
  local code="$1" status
  case "$code" in 0) status=passed ;; 1) status=failed ;; *) status=error; code=2 ;; esac
  if [ -n "$PATH_PREFIX" ] && [ -f "$OUT/archguard.sarif" ]; then
    python3 "$ACTION_DIR/rebase_sarif.py" "$OUT/archguard.sarif" "$PATH_PREFIX" \
      || echo "::warning title=ArchGuard::Could not rebase SARIF paths onto the repository root."
  fi
  {
    echo "exit-code=$code"
    echo "status=$status"
    echo "report-dir=$OUT"
    if [ -f "$OUT/archguard.sarif" ]; then echo "sarif=$OUT/archguard.sarif"; else echo "sarif="; fi
  } >> "$OUTPUT_FILE"
  ARCHGUARD_PATH_PREFIX="$PATH_PREFIX" python3 "$ACTION_DIR/summary.py" "$OUT/archguard.json" "$code" \
    "${INPUT_ANNOTATIONS:-true}" "$SUMMARY_FILE" "$OUTPUT_FILE" "${2:-}"
  exit 0
}

group() { echo "::group::$1"; }
endgroup() { echo "::endgroup::"; }

retry() {
  local attempt
  for attempt in 1 2 3; do
    "$@" && return 0
    echo "Attempt $attempt failed; retrying (transient registry errors are common)."
    sleep $((attempt * 10))
  done
  return 1
}

# The output is the analyzer's self-description, for example "archguard 0.1.0 (python analyzer, ...)".
is_archguard() { "$@" --version 2>/dev/null | grep -q "($LANGUAGE analyzer"; }

[ -f "$CONFIG" ] || finish 2 "Policy file $WORKDIR/$CONFIG not found."

cli=()
[ -n "${INPUT_CLI_COMMAND:-}" ] && read -r -a cli <<< "$INPUT_CLI_COMMAND"
args=(check --config "$WORKDIR/$CONFIG" --out "$OUT" --format json,sarif,html,console)

case "$LANGUAGE" in
  java)
    # Analyzer jar: explicit, Maven Central, or built from this action's source.
    if [ ${#cli[@]} -eq 0 ]; then
      jar="${INPUT_CLI_JAR:-}"
      if [ -z "$jar" ]; then
        jar="$TMP/archguard-cli-$VERSION.jar"
        url="https://repo1.maven.org/maven2/io/archguard/archguard-cli/$VERSION/archguard-cli-$VERSION.jar"
        if ! curl -fsSL -o "$jar" "$url" 2>/dev/null; then
          group "Build ArchGuard $VERSION from source (not on Maven Central)"
          retry mvn -B -q -ntp -f "$SOURCE_DIR/pom.xml" install -DskipTests \
            || { endgroup; finish 2 "Could not download or build archguard-cli $VERSION."; }
          endgroup
          built=$(ls "$SOURCE_DIR"/archguard-cli/target/archguard-cli-*.jar 2>/dev/null | grep -v original- | head -1)
          [ -n "$built" ] || finish 2 "archguard-cli jar was not produced by the source build."
          jar="$built"
          VERSION="$(basename "$jar" .jar)"
          VERSION="${VERSION#archguard-cli-}"
        fi
      fi
      [ -f "$jar" ] || finish 2 "archguard-cli jar not found: $jar"
      cli=(java -jar "$jar")
    fi

    # Compile and describe modules and dependencies.
    group "Compile and resolve the classpath"
    if [ -f pom.xml ]; then
      mvn -B -q -ntp -DskipTests compile "io.archguard:archguard-maven-plugin:$VERSION:classpath" \
        || { endgroup; finish 2 "Maven compile failed."; }
    elif [ -f build.gradle ] || [ -f build.gradle.kts ]; then
      OUT="$WORKDIR/build/archguard"
      args[4]="$OUT"
      gradle_cmd=gradle
      [ -x ./gradlew ] && gradle_cmd=./gradlew
      "$gradle_cmd" -q -I "$SOURCE_DIR/skills/archguard/scripts/archguard.init.gradle" classes archguardClasspath \
        || { endgroup; finish 2 "Gradle build failed."; }
    else
      endgroup
      finish 2 "No pom.xml or build.gradle in $WORKDIR for a Java policy."
    fi
    endgroup
    args+=(--project "$ROOT")
    while IFS= read -r file; do
      args+=(--classpath-file "$file")
    done < <(find . \( -path '*/target/archguard.classpath' -o -path '*/build/archguard.classpath' \) -not -path '*/node_modules/*' | sort)
    ;;

  typescript)
    # The project's own archguard-cli devDependency, else the analyzer from this action's source.
    if [ ${#cli[@]} -eq 0 ] && [ -x node_modules/.bin/archguard ] && is_archguard node_modules/.bin/archguard; then
      cli=(node_modules/.bin/archguard)
    fi
    if [ ${#cli[@]} -eq 0 ]; then
      group "Build the TypeScript analyzer from the action source"
      (cd "$SOURCE_DIR/typescript/archguard-ts" && retry npm ci --no-audit --no-fund --loglevel=error && npm run build --silent) \
        || { endgroup; finish 2 "Could not build the TypeScript analyzer."; }
      endgroup
      cli=(node "$SOURCE_DIR/typescript/archguard-ts/dist/cli.js")
    fi
    args+=(--project "$WORKDIR")
    ;;

  python)
    # The analyzer installed in the job's environment, else a private venv from this action's source.
    if [ ${#cli[@]} -eq 0 ] && command -v archguard >/dev/null 2>&1 && is_archguard archguard; then
      cli=(archguard)
    fi
    if [ ${#cli[@]} -eq 0 ]; then
      group "Install the Python analyzer from the action source"
      venv="$TMP/archguard-venv"
      { python3 -m venv "$venv" \
        && python3 "$SOURCE_DIR/python/archguard-py/scripts/copy_spec.py" \
        && retry "$venv/bin/python" -m pip install -q --disable-pip-version-check "$SOURCE_DIR/python/archguard-py"; } \
        || { endgroup; finish 2 "Could not install the Python analyzer."; }
      endgroup
      cli=("$venv/bin/archguard")
    fi
    args+=(--project "$WORKDIR")
    ;;

  *) finish 2 "Unknown language '$LANGUAGE'." ;;
esac
is_archguard "${cli[@]}" || finish 2 "'${cli[*]}' is not the ArchGuard $LANGUAGE analyzer (check its --version)."

baseline="${INPUT_BASELINE:-}"
[ -z "$baseline" ] && [ -f architecture-baseline.json ] && baseline=architecture-baseline.json
[ -n "$baseline" ] && args+=(--baseline "$WORKDIR/$baseline")
suppressions="${INPUT_SUPPRESSIONS:-}"
[ -z "$suppressions" ] && [ -f architecture-suppressions.json ] && suppressions=architecture-suppressions.json
[ -n "$suppressions" ] && args+=(--suppressions "$WORKDIR/$suppressions")
[ -n "${INPUT_FAIL_ON:-}" ] && args+=(--fail-on "$INPUT_FAIL_ON")

# Pull-request scope: files changed relative to the merge base, as absolute paths so every analyzer
# maps them onto its project directory.
if [ "${INPUT_CHANGED_FILES_ONLY:-false}" = true ] && [ -n "${GITHUB_BASE_REF:-}" ]; then
  changed="$TMP/archguard-changed-files.txt"
  git -C "$ROOT" fetch -q --no-tags origin "$GITHUB_BASE_REF" 2>/dev/null || true
  base=$(git -C "$ROOT" merge-base "origin/$GITHUB_BASE_REF" HEAD 2>/dev/null || echo "origin/$GITHUB_BASE_REF")
  if names=$(git -C "$ROOT" diff --name-only "$base" HEAD 2>/dev/null); then
    printf '%s\n' "$names" | sed '/^$/d' | sed "s|^|$ROOT/|" > "$changed"
    echo "Changed-files scope: $(wc -l < "$changed" | tr -d ' ') file(s) since $base"
    args+=(--changed-files "$changed")
  else
    echo "::warning title=ArchGuard::Could not compute changed files; checking the whole project."
  fi
fi

group "archguard ${args[*]}"
"${cli[@]}" "${args[@]}"
code=$?
endgroup
finish "$code"
