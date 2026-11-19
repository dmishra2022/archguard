#!/usr/bin/env python3
"""Write the ArchGuard job summary, workflow annotations and the new-findings output.

Usage: summary.py <archguard.json> <exit code> <annotations true|false> <summary file> <output file> [error]
"""
import json
import sys
from pathlib import Path

MAX_ROWS = 50


def escape(value, prop=False):
    value = str(value).replace('%', '%25').replace('\r', '%0D').replace('\n', '%0A')
    if prop:
        value = value.replace(':', '%3A').replace(',', '%2C')
    return value


def cell(value):
    return str(value).replace('|', '\\|').replace('\n', ' ')


def main():
    report_path, code, annotate, summary_path, output_path = sys.argv[1:6]
    error = sys.argv[6] if len(sys.argv) > 6 else ''
    code = int(code)
    lines = ['## ArchGuard architecture check', '']
    new = []
    report = None
    if Path(report_path).is_file():
        report = json.loads(Path(report_path).read_text(encoding='utf-8'))
    if code == 2 or report is None or report.get('analysisStatus') == 'FAILED':
        reason = error or (report or {}).get('error') or 'see the job log'
        lines += [f':x: **Analysis error (exit 2), not a pass.** {cell(reason)}']
        if error:
            print(f'::error title=ArchGuard::{escape(error)}')
    else:
        findings = report.get('findings', [])
        new = [f for f in findings if f['status'] == 'NEW' and f['severity'] != 'INFO']
        existing = sum(1 for f in findings if f['status'] == 'EXISTING')
        suppressed = sum(1 for f in findings if f['status'] == 'SUPPRESSED')
        headline = ':white_check_mark: **Passed**' if code == 0 else ':x: **Architecture policy violated**'
        lines += [
            f'{headline}: {len(new)} new, {existing} baselined, {suppressed} suppressed; '
            f'{report.get("analyzedClasses", 0)} classes analyzed (policy {report.get("policyHash", "")[:12]}).',
            '',
        ]
        if new:
            lines += ['| Rule | Severity | Location | Depends on | Fix |', '|---|---|---|---|---|']
            for f in new[:MAX_ROWS]:
                loc = f['location']
                where = loc['path'] or loc['symbol']
                if loc.get('line'):
                    where += f':{loc["line"]}'
                lines.append(
                    f'| {f["ruleId"]} | {f["severity"]} | `{cell(where)}` | `{cell(f["target"])}` | {cell(f["remediation"])} |'
                )
            if len(new) > MAX_ROWS:
                lines.append(f'\n{len(new) - MAX_ROWS} more in the report artifact.')
        for d in report.get('diagnostics', []):
            lines.append(f'\n> {cell(d)}')
        if annotate == 'true':
            for f in new:
                loc = f['location']
                level = 'error' if f['severity'] == 'ERROR' else 'warning'
                props = [f'title={escape(f["ruleId"] + " " + f["message"], True)}']
                if loc['path']:
                    props.insert(0, f'file={escape(loc["path"], True)}')
                    if loc.get('line'):
                        props.insert(1, f'line={loc["line"]}')
                text = f'{loc["symbol"]} depends on {f["target"]}. {f["remediation"]}'
                print(f'::{level} {",".join(props)}::{escape(text)}')
    with open(summary_path, 'a', encoding='utf-8') as handle:
        handle.write('\n'.join(lines) + '\n')
    with open(output_path, 'a', encoding='utf-8') as handle:
        handle.write(f'new-findings={len(new)}\n')


if __name__ == '__main__':
    main()
