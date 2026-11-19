#!/usr/bin/env python3
"""Cursor `stop` hook: run the ArchGuard check on changed files and send violations back to the agent.

Fails open: build errors, a missing CLI or a missing policy never block the agent, they are only
reported to it once. Set ARCHGUARD_CHECK to the check script path if the skill is not installed in
.cursor/skills/archguard.
"""
import json
import os
import subprocess
import sys

CHECK = os.environ.get('ARCHGUARD_CHECK', '.cursor/skills/archguard/scripts/check.sh')


def main():
    try:
        event = json.load(sys.stdin)
    except ValueError:
        event = {}
    if event.get('status') not in (None, 'completed') or not os.path.isfile('architecture.yml'):
        print('{}')
        return
    if not os.path.isfile(CHECK):
        print('{}')
        return
    try:
        run = subprocess.run(['bash', CHECK, '--changed'], capture_output=True, text=True, timeout=600)
    except subprocess.TimeoutExpired:
        print('{}')
        return
    if run.returncode == 0:
        print('{}')
        return
    findings = [line for line in run.stdout.splitlines() if line.startswith('{"rule"') and '"status":"NEW"' in line]
    if run.returncode == 1 and findings:
        message = (
            'ArchGuard found new architecture violations in the files you changed. Fix each one using '
            'its "fix" text and the archguard skill (reference/rules.md). Do not edit architecture.yml, '
            'the baseline or suppressions; if a finding seems wrong, explain it to the user instead.\n'
            + '\n'.join(findings[:20])
        )
    elif run.returncode == 2 and event.get('loop_count', 0) == 0:
        summary = run.stdout.strip().splitlines()[-1:] or [run.stderr.strip()[-500:]]
        message = 'The ArchGuard check could not run (exit 2): ' + summary[0]
    else:
        print('{}')
        return
    print(json.dumps({'followup_message': message}))


if __name__ == '__main__':
    main()
