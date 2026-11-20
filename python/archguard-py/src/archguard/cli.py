"""ArchGuard command line (spec/CLI.md)."""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, List, Optional, Set

from .model import LANGUAGE, SEVERITIES, VERSION

OK, VIOLATION, ERROR, USAGE = 0, 1, 2, 64
COMMANDS = frozenset({'check', 'analyze', 'baseline', 'validate', 'rules'})

USAGE_TEXT = """Usage: archguard <check|analyze|baseline|validate|rules> [options]

  check      Analyze, apply baseline and suppressions, write reports, gate (exit 1 on violation)
  analyze    Same analysis and reports, never fails on policy violations
  baseline   Write a baseline of current non-INFO findings
  validate   Validate the policy only (schema, semantics, extends resolution)
  rules      Print the rule catalog (--json for JSON)

Shared options:
  --config <file>            Policy file (default <project>/architecture.yml)
  --project <dir>            Project root; report paths are relative to it (default .)
  --out <dir>                Report directory (default <project>/reports/archguard)
  --format <list>            Subset of json,sarif,html,agent,console (default json,sarif,html)
  --baseline <file>          Reviewed baseline to apply
  --suppressions <file>      Reviewed suppressions to apply
  --changed-files <file|->   Report and gate only findings located in these project-relative files
  --baseline-output <file>   Destination for 'baseline' (default <project>/architecture-baseline.json)
  --overwrite-baseline       Allow replacing an existing baseline
  --fail-on <severity>       Override the policy failOn (INFO, WARNING, ERROR)

Python: source roots come from the policy sourceRoots (default: src/ when it contains Python files, else .).

Exit codes: 0 pass, 1 policy violation, 2 analysis error (never a pass), 64 usage error."""


class UsageError(Exception):
    pass


@dataclass
class Options:
    project: Path
    command: Optional[str] = None
    help: bool = False
    version: bool = False
    json: bool = False
    overwrite_baseline: bool = False
    config: Optional[Path] = None
    out: Optional[Path] = None
    baseline: Optional[Path] = None
    suppressions: Optional[Path] = None
    baseline_output: Optional[Path] = None
    changed_files: Optional[str] = None
    fail_on: Optional[str] = None
    formats: Set[str] = field(default_factory=lambda: {'json', 'sarif', 'html'})


def parse_options(args: List[str], cwd: Path) -> Options:
    from .reports import FORMATS

    o = Options(project=cwd.resolve())
    rest = list(args)

    def path(v: str) -> Path:
        return (cwd / v).resolve()

    while rest:
        arg = rest.pop(0)
        inline: Optional[str] = None
        if arg.startswith('--') and '=' in arg[1:]:
            arg, inline = arg.split('=', 1)

        def value() -> str:
            if inline is not None:
                if not inline:
                    raise UsageError(f'Empty value for {arg}')
                return inline
            if not rest or (rest[0].startswith('--') and len(rest[0]) > 2):
                raise UsageError(f'Missing value for {arg}')
            return rest.pop(0)

        if arg in ('-h', '--help', 'help'):
            o.help = True
        elif arg == '--version':
            o.version = True
        elif arg == '--json':
            o.json = True
        elif arg == '--overwrite-baseline':
            o.overwrite_baseline = True
        elif arg == '--project':
            o.project = path(value())
        elif arg == '--config':
            o.config = path(value())
        elif arg == '--out':
            o.out = path(value())
        elif arg == '--baseline':
            o.baseline = path(value())
        elif arg == '--suppressions':
            o.suppressions = path(value())
        elif arg == '--baseline-output':
            o.baseline_output = path(value())
        elif arg == '--changed-files':
            v = value()
            o.changed_files = '-' if v == '-' else str(path(v))
        elif arg == '--fail-on':
            v = value().upper()
            if v not in SEVERITIES:
                raise UsageError(f'Invalid severity: {v}')
            o.fail_on = v
        elif arg == '--format':
            formats = {f.strip() for f in value().split(',') if f.strip()}
            for f in sorted(formats):
                if f not in FORMATS:
                    raise UsageError(f'Unknown format: {f}')
            if not formats:
                raise UsageError('Empty --format')
            o.formats = formats
        else:
            if arg.startswith('-'):
                raise UsageError(f'Unknown option: {arg}')
            if o.command:
                raise UsageError(f'Unexpected argument: {arg}')
            if arg not in COMMANDS:
                raise UsageError(f'Unknown command: {arg}')
            o.command = arg
    if not o.command and not o.help and not o.version:
        raise UsageError('Missing command')
    return o


@dataclass
class Io:
    cwd: Path
    stdout: Callable[[str], None]
    stderr: Callable[[str], None]
    stdin: Callable[[], str]
    today: Optional[object] = None


def run(args: List[str], io: Io) -> int:
    try:
        o = parse_options(args, io.cwd)
    except UsageError as e:
        io.stderr(f'archguard: {e}\n{USAGE_TEXT}\n')
        return USAGE
    if o.help:
        io.stdout(USAGE_TEXT + '\n')
        return OK

    from .spec import catalog

    if o.version:
        io.stdout(f'archguard {VERSION} ({LANGUAGE} analyzer, spec {catalog().spec_version})\n')
        return OK
    config = o.config or o.project / 'architecture.yml'

    from .policy import policy_hash, read_policy

    if o.command == 'validate':
        try:
            policy = read_policy(config)
            io.stdout(f'Policy valid: {config} (schemaVersion {policy.schemaVersion}, policyHash {policy_hash(policy)})\n')
            return OK
        except Exception as e:  # noqa: BLE001 - any failure is an invalid policy
            io.stderr(f'Policy invalid: {e}\n')
            return ERROR
    if o.command == 'rules':
        try:
            c = catalog()
            rows = [
                {'id': rid, 'title': c.rule(rid).title, 'defaultSeverity': c.rule(rid).default_severity,
                 'helpUri': '', 'tags': [c.rule(rid).category]}
                for rid in sorted(c.rule_ids)
            ]
            if o.json:
                io.stdout(json.dumps(rows, indent=2) + '\n')
            else:
                for r in rows:
                    io.stdout(f"{r['id']:<10} {r['defaultSeverity']:<8} {r['title']}\n")
            return OK
        except Exception as e:  # noqa: BLE001
            io.stderr(f'Rule catalog unavailable: {e}\n')
            return ERROR

    from .changed import restrict_to_changed_files
    from .debt import apply_debt, write_baseline
    from .engine import analyze
    from .reports import agent, agent_error, console_report, summary, write_failure, write_reports

    out = o.out or o.project / 'reports' / 'archguard'
    try:
        policy = read_policy(config)
        result = analyze(o.project, policy)
        if o.command == 'baseline':
            target = o.baseline_output or o.project / 'architecture-baseline.json'
            if target.exists() and not o.overwrite_baseline:
                raise RuntimeError(f'Baseline already exists; review changes before passing --overwrite-baseline: {target}')
            write_baseline(target, result)
            io.stderr(f'Baseline written: {target}\n')
        else:
            result = apply_debt(result, o.baseline, o.suppressions, io.today)
        if o.changed_files:
            text = io.stdin() if o.changed_files == '-' else Path(o.changed_files).read_text(encoding='utf-8')
            result = restrict_to_changed_files(result, text.splitlines(), o.project)
        failed = result.fails(o.fail_on or policy.failOn, policy.newOnly)
        write_reports(out, result, o.formats, failed)
        if 'console' in o.formats:
            io.stdout(console_report(result) + '\n')
        if 'agent' in o.formats:
            io.stdout(agent(result, failed))
        if 'console' not in o.formats:
            io.stderr(summary(result) + '\n')
        io.stderr(f'Reports: {out}\n')
        if o.command == 'check' and failed:
            io.stderr(f"Architecture policy violated. See {out / 'index.html'}\n")
            return VIOLATION
        return OK
    except Exception as e:  # noqa: BLE001 - every failure is an analysis error, never a pass
        message = str(e) or type(e).__name__
        try:
            write_failure(out, message, o.formats)
        except Exception:  # noqa: BLE001 - the analysis error is the primary failure
            pass
        if 'agent' in o.formats:
            io.stdout(agent_error(message))
        io.stderr(f'Architecture analysis failed (not a policy pass): {message}\n')
        return ERROR


def main(argv: Optional[List[str]] = None) -> None:
    io = Io(Path.cwd(), sys.stdout.write, sys.stderr.write, sys.stdin.read)
    sys.exit(run(sys.argv[1:] if argv is None else argv, io))
