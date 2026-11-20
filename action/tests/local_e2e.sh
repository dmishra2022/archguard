#!/usr/bin/env bash
# Run the action's detect.sh and run.sh outside GitHub against the examples and assert the outcome.
# The repository is copied to a scratch git repository first, so nothing in the checkout changes.
#
# Usage: action/tests/local_e2e.sh [case-filter]
# Needs bash, git, python3, rsync; Node.js for TypeScript cases; JDK and Maven for Java cases.
set -uo pipefail

SRC="$(cd "$(dirname "$0")/../.." && pwd)"
FILTER="${1:-}"
SCRATCH="$(mktemp -d)"
REPO="$SCRATCH/repo"
rsync -a --exclude .git --exclude target --exclude node_modules --exclude reports --exclude __pycache__ \
  --exclude '*.egg-info' --exclude docs/kb --exclude src/archguard/spec "$SRC/" "$REPO/"
git -C "$REPO" init -q
git -C "$REPO" add -A
git -C "$REPO" -c user.name=e2e -c user.email=e2e@localhost commit -qm base

# name | working directory | config | expected exit code | expected rule in SARIF | expected SARIF uri
CASES=(
  "python-clean|examples/python-clean|architecture.yml|0||"
  "python-violating|examples/python-violating|architecture.yml|1|HEX-002|examples/python-violating/src/orders/application/place_order.py"
  "python-missing|examples/python-clean|missing.yml|2||"
  "typescript-clean|examples/typescript-clean|architecture.yml|0||"
  "typescript-violating|examples/typescript-violating|architecture.yml|1|HEX-002|examples/typescript-violating/src/orders/application/place-order.ts"
  "typescript-missing|examples/typescript-clean|missing.yml|2||"
  "java-clean|examples/clean|architecture.yml|0||"
  "java-violating|examples/violating|architecture.yml|1|HEX-002|examples/violating/src/main/java/example/orders/application/OrderService.java"
)

failures=0
for entry in "${CASES[@]}"; do
  IFS='|' read -r name workdir config expect rule uri <<< "$entry"
  [ -n "$FILTER" ] && [[ "$name" != *"$FILTER"* ]] && continue
  run_dir="$(mktemp -d)"
  export GITHUB_ACTION_PATH="$REPO/action" RUNNER_TEMP="$run_dir" GITHUB_OUTPUT="$run_dir/output" \
    GITHUB_STEP_SUMMARY="$run_dir/summary"
  : > "$GITHUB_OUTPUT"
  (
    cd "$REPO/$workdir" || exit 3
    INPUT_LANGUAGE=auto INPUT_CONFIG="$config" bash "$GITHUB_ACTION_PATH/detect.sh" > "$run_dir/detect.log" 2>&1 || exit 3
    ARCHGUARD_LANGUAGE="$(sed -n 's/^language=//p' "$GITHUB_OUTPUT")" INPUT_CONFIG="$config" INPUT_ANNOTATIONS=true \
      bash "$GITHUB_ACTION_PATH/run.sh" > "$run_dir/run.log" 2>&1
  )
  code="$(sed -n 's/^exit-code=//p' "$GITHUB_OUTPUT")"
  language="$(sed -n 's/^language=//p' "$GITHUB_OUTPUT")"
  sarif="$(sed -n 's/^sarif=//p' "$GITHUB_OUTPUT")"
  problem=""
  [ "$code" = "$expect" ] || problem="exit-code '$code', expected $expect"
  if [ -z "$problem" ] && [ -n "$rule" ]; then
    problem="$(python3 - "$sarif" "$rule" "$uri" <<'EOF'
import json, sys
path, rule, uri = sys.argv[1:4]
try:
    results = json.load(open(path))['runs'][0]['results']
except (OSError, ValueError, KeyError, IndexError) as error:
    print(f'no SARIF: {error}')
    sys.exit()
uris = {l['physicalLocation']['artifactLocation']['uri'] for r in results if r['ruleId'] == rule for l in r['locations']}
if uri not in uris:
    print(f'{rule} not reported at {uri}; got {sorted(uris)}')
EOF
)"
  fi
  if [ -z "$problem" ] && [ "$expect" = 1 ] && ! grep -q "^::error file=$uri" "$run_dir/run.log"; then
    problem="no workflow annotation for $uri"
  fi
  if [ -z "$problem" ]; then
    echo "ok   $name ($language, exit $code)"
  else
    echo "FAIL $name ($language): $problem (logs in $run_dir)"
    failures=$((failures + 1))
  fi
done
# Pull-request scope: a commit on top of origin/main touches one violating file per language, so only
# the finding in that file is reported and gated.
if [ -z "$FILTER" ] || [[ "changed" == *"$FILTER"* ]]; then
  git -C "$REPO" branch -q -M main
  git clone -q --bare "$REPO" "$SCRATCH/origin.git"
  git -C "$REPO" remote add origin "$SCRATCH/origin.git"
  echo "# touched" >> "$REPO/examples/python-violating/src/orders/application/place_order.py"
  echo "// touched" >> "$REPO/examples/typescript-violating/src/orders/application/place-order.ts"
  git -C "$REPO" -c user.name=e2e -c user.email=e2e@localhost commit -qam "touch application files"
  for workdir in examples/python-violating examples/typescript-violating; do
    run_dir="$(mktemp -d)"
    export GITHUB_ACTION_PATH="$REPO/action" RUNNER_TEMP="$run_dir" GITHUB_OUTPUT="$run_dir/output" \
      GITHUB_STEP_SUMMARY="$run_dir/summary" GITHUB_BASE_REF=main
    : > "$GITHUB_OUTPUT"
    (
      cd "$REPO/$workdir" || exit 3
      INPUT_CONFIG=architecture.yml bash "$GITHUB_ACTION_PATH/detect.sh" > "$run_dir/detect.log" 2>&1 || exit 3
      ARCHGUARD_LANGUAGE="$(sed -n 's/^language=//p' "$GITHUB_OUTPUT")" INPUT_CHANGED_FILES_ONLY=true \
        bash "$GITHUB_ACTION_PATH/run.sh" > "$run_dir/run.log" 2>&1
    )
    unset GITHUB_BASE_REF
    code="$(sed -n 's/^exit-code=//p' "$GITHUB_OUTPUT")"
    new="$(sed -n 's/^new-findings=//p' "$GITHUB_OUTPUT")"
    rules="$(grep -o '^::error file=[^,]*,line=[0-9]*,title=[A-Z]*-[0-9]*' "$run_dir/run.log" | sed 's/.*title=//' | sort -u | tr '\n' ' ')"
    if [ "$code" = 1 ] && [ "$new" = 1 ] && [ "$rules" = "HEX-002 " ]; then
      echo "ok   changed-files $workdir (only HEX-002 in the touched file)"
    else
      echo "FAIL changed-files $workdir: exit $code, new $new, rules '$rules' (logs in $run_dir)"
      failures=$((failures + 1))
    fi
  done
fi

# Organisation preset: each clean example extends org:acme/base@1.0.0 from presets/acme, packaged the
# way that ecosystem consumes it.
preset_case() {
  local name="$1" workdir="$2" extensions="$3" expect="$4"
  [ -n "$FILTER" ] && [[ "$name" != *"$FILTER"* ]] && return
  local run_dir code
  run_dir="$(mktemp -d)"
  export GITHUB_ACTION_PATH="$REPO/action" RUNNER_TEMP="$run_dir" GITHUB_OUTPUT="$run_dir/output" \
    GITHUB_STEP_SUMMARY="$run_dir/summary"
  : > "$GITHUB_OUTPUT"
  (
    cd "$REPO/$workdir" || exit 3
    bash "$GITHUB_ACTION_PATH/detect.sh" > "$run_dir/detect.log" 2>&1 || exit 3
    ARCHGUARD_LANGUAGE="$(sed -n 's/^language=//p' "$GITHUB_OUTPUT")" INPUT_EXTENSIONS="$extensions" \
      bash "$GITHUB_ACTION_PATH/run.sh" > "$run_dir/run.log" 2>&1
  )
  code="$(sed -n 's/^exit-code=//p' "$GITHUB_OUTPUT")"
  if [ "$code" = "$expect" ] && grep -q '"org:acme/base@1.0.0"' "$REPO/$workdir/architecture.yml"; then
    echo "ok   $name (exit $code)"
  else
    echo "FAIL $name: exit '$code', expected $expect (logs in $run_dir)"
    failures=$((failures + 1))
  fi
}
extend_policy() {
  python3 - "$1" "$2" <<'EOF'
import sys
path, language = sys.argv[1:3]
lines = open(path).read().splitlines()
body = [l for l in lines if not l.startswith(('schemaVersion:', 'language:'))]
open(path, 'w').write('\n'.join(['schemaVersion: 2', f'language: {language}', 'extends: ["org:acme/base@1.0.0"]'] + body) + '\n')
EOF
}
if [ -z "$FILTER" ] || [[ "$FILTER" == preset* ]]; then
  for language in python typescript java; do
    [[ -n "$FILTER" && "$FILTER" != preset && "$FILTER" != "preset-$language"* ]] && continue
    case "$language" in
      python)
        extend_policy "$REPO/examples/python-clean/architecture.yml" python
        extend_policy "$REPO/examples/python-violating/architecture.yml" python
        preset_case preset-python-clean examples/python-clean "../../presets/acme" 0
        preset_case preset-python-violating examples/python-violating "../../presets/acme" 1
        preset_case preset-python-not-installed examples/python-clean "" 2 ;;
      typescript)
        extend_policy "$REPO/examples/typescript-clean/architecture.yml" typescript
        tarball="$(cd "$SCRATCH" && npm pack --silent "$REPO/presets/acme" | tail -1)"
        preset_case preset-typescript-not-installed examples/typescript-clean "" 2
        # The layout `npm install @acme/archguard-presets` produces, without installing the example's NestJS dependencies.
        mkdir -p "$REPO/examples/typescript-clean/node_modules/@acme/archguard-presets"
        tar -xzf "$SCRATCH/$tarball" --strip-components=1 -C "$REPO/examples/typescript-clean/node_modules/@acme/archguard-presets" \
          || { echo "FAIL preset-typescript: could not unpack the preset"; failures=$((failures + 1)); }
        preset_case preset-typescript-clean examples/typescript-clean "" 0 ;;
      java)
        extend_policy "$REPO/examples/clean/architecture.yml" java
        if mvn -B -q -ntp -f "$REPO/presets/acme/pom.xml" package > "$SCRATCH/preset-jar.log" 2>&1; then
          preset_case preset-java-clean examples/clean "../../presets/acme/target/archguard-presets-1.0.0.jar" 0
          preset_case preset-java-not-installed examples/clean "" 2
        else
          echo "FAIL preset-java: preset jar build failed ($SCRATCH/preset-jar.log)"; failures=$((failures + 1))
        fi ;;
    esac
  done
fi

echo "$failures failure(s); scratch repository $SCRATCH"
[ "$failures" -eq 0 ]
