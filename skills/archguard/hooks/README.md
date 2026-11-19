# Optional Cursor hook

The skill already tells the agent to run the check. This hook enforces it: when the agent finishes a turn, the hook runs `scripts/check.sh --changed`. If there are NEW findings, it sends them back as a follow-up message, so the agent fixes them before handing over. It is an example, not a requirement; CI remains the enforcement point.

Install in a project (paths are relative to the project root):

```bash
mkdir -p .cursor/skills .cursor/hooks
cp -r <archguard>/skills/archguard .cursor/skills/
cp .cursor/skills/archguard/hooks/archguard-stop.py .cursor/hooks/
cp .cursor/skills/archguard/hooks/hooks.json .cursor/hooks.json   # or merge the "stop" entry into an existing file
```

Behaviour:
- It runs only when the agent completed normally and `architecture.yml` exists.
- It follows up at most 3 times in a row (`loop_limit`).
- It fails open. Build errors, a missing CLI or a timeout never block the agent; an analysis error is reported once.
- It needs `python3`, `bash`, `git`, Java and the build tool on `PATH`, and the ArchGuard CLI jar (see `scripts/check.sh` for `ARCHGUARD_CLI_JAR`).
