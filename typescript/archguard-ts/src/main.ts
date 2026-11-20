import { existsSync, readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { LANGUAGE, Severity, SEVERITIES, VERSION, fails } from './model.js';
import { policyHash, readPolicy } from './policy.js';
import { analyze } from './engine.js';
import { applyDebt, writeBaseline } from './debt.js';
import { restrictToChangedFiles } from './changed.js';
import { FORMATS, agent, agentError, consoleReport, writeFailure, writeReports } from './reports.js';
import { catalog } from './spec.js';

export const OK = 0;
export const VIOLATION = 1;
export const ERROR = 2;
export const USAGE = 64;

const COMMANDS = new Set(['check', 'analyze', 'baseline', 'validate', 'rules']);

export const USAGE_TEXT = `Usage: archguard <check|analyze|baseline|validate|rules> [options]

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

TypeScript options:
  --tsconfig <file>          tsconfig used for module resolution (default <project>/tsconfig.json)

Exit codes: 0 pass, 1 policy violation, 2 analysis error (never a pass), 64 usage error.`;

class UsageError extends Error {}

interface Options {
  command?: string;
  help: boolean;
  version: boolean;
  json: boolean;
  overwriteBaseline: boolean;
  project: string;
  config?: string;
  out?: string;
  baseline?: string;
  suppressions?: string;
  baselineOutput?: string;
  changedFiles?: string;
  failOn?: Severity;
  tsconfig?: string;
  formats: Set<string>;
}

function parseOptions(args: string[], cwd: string): Options {
  const o: Options = {
    help: false,
    version: false,
    json: false,
    overwriteBaseline: false,
    project: resolve(cwd),
    formats: new Set(['json', 'sarif', 'html']),
  };
  const rest = [...args];
  const path = (v: string) => resolve(cwd, v);
  while (rest.length) {
    let arg = rest.shift()!;
    let inline: string | undefined;
    const eq = arg.indexOf('=');
    if (arg.startsWith('--') && eq > 0) {
      inline = arg.slice(eq + 1);
      arg = arg.slice(0, eq);
    }
    const value = (): string => {
      if (inline !== undefined) {
        if (!inline) throw new UsageError(`Empty value for ${arg}`);
        return inline;
      }
      const v = rest.shift();
      if (v === undefined || (v.startsWith('--') && v.length > 2)) throw new UsageError(`Missing value for ${arg}`);
      return v;
    };
    switch (arg) {
      case '-h':
      case '--help':
      case 'help':
        o.help = true;
        break;
      case '--version':
        o.version = true;
        break;
      case '--json':
        o.json = true;
        break;
      case '--overwrite-baseline':
        o.overwriteBaseline = true;
        break;
      case '--project':
        o.project = path(value());
        break;
      case '--config':
        o.config = path(value());
        break;
      case '--out':
        o.out = path(value());
        break;
      case '--baseline':
        o.baseline = path(value());
        break;
      case '--suppressions':
        o.suppressions = path(value());
        break;
      case '--baseline-output':
        o.baselineOutput = path(value());
        break;
      case '--changed-files': {
        const v = value();
        o.changedFiles = v === '-' ? '-' : path(v);
        break;
      }
      case '--tsconfig':
        o.tsconfig = path(value());
        break;
      case '--fail-on': {
        const v = value().toUpperCase();
        if (!(SEVERITIES as readonly string[]).includes(v)) throw new UsageError(`Invalid severity: ${v}`);
        o.failOn = v as Severity;
        break;
      }
      case '--format': {
        const formats = new Set(value().split(',').map((f) => f.trim()).filter(Boolean));
        for (const f of formats) if (!FORMATS.has(f)) throw new UsageError(`Unknown format: ${f}`);
        if (formats.size === 0) throw new UsageError('Empty --format');
        o.formats = formats;
        break;
      }
      default:
        if (arg.startsWith('-')) throw new UsageError(`Unknown option: ${arg}`);
        if (o.command) throw new UsageError(`Unexpected argument: ${arg}`);
        if (!COMMANDS.has(arg)) throw new UsageError(`Unknown command: ${arg}`);
        o.command = arg;
    }
  }
  if (!o.command && !o.help && !o.version) throw new UsageError('Missing command');
  return o;
}

export interface Io {
  cwd: string;
  stdout: (s: string) => void;
  stderr: (s: string) => void;
  stdin: () => string;
  now?: Date;
}

export async function run(args: string[], io: Io): Promise<number> {
  let o: Options;
  try {
    o = parseOptions(args, io.cwd);
  } catch (e) {
    io.stderr(`archguard: ${(e as Error).message}\n${USAGE_TEXT}\n`);
    return USAGE;
  }
  if (o.help) {
    io.stdout(USAGE_TEXT + '\n');
    return OK;
  }
  if (o.version) {
    io.stdout(`archguard ${VERSION} (${LANGUAGE} analyzer, spec ${catalog().specVersion})\n`);
    return OK;
  }
  const config = o.config ?? resolve(o.project, 'architecture.yml');
  if (o.command === 'validate') {
    try {
      const policy = await readPolicy(config, o.project);
      io.stdout(`Policy valid: ${config} (schemaVersion ${policy.schemaVersion}, policyHash ${policyHash(policy)})\n`);
      return OK;
    } catch (e) {
      io.stderr(`Policy invalid: ${(e as Error).message}\n`);
      return ERROR;
    }
  }
  if (o.command === 'rules') {
    try {
      const c = catalog();
      const rows = [...c.ruleIds].sort().map((id) => {
        const r = c.rule(id);
        return { id, title: r.title, defaultSeverity: r.defaultSeverity, helpUri: '', tags: [r.category] };
      });
      if (o.json) io.stdout(JSON.stringify(rows, null, 2) + '\n');
      else for (const r of rows) io.stdout(`${r.id.padEnd(10)} ${r.defaultSeverity.padEnd(8)} ${r.title}\n`);
      return OK;
    } catch (e) {
      io.stderr(`Rule catalog unavailable: ${(e as Error).message}\n`);
      return ERROR;
    }
  }
  const out = o.out ?? resolve(o.project, 'reports/archguard');
  try {
    const policy = await readPolicy(config, o.project);
    let result = analyze(o.project, policy, o.tsconfig);
    if (o.command === 'baseline') {
      const target = o.baselineOutput ?? resolve(o.project, 'architecture-baseline.json');
      if (existsSync(target) && !o.overwriteBaseline)
        throw new Error(`Baseline already exists; review changes before passing --overwrite-baseline: ${target}`);
      writeBaseline(target, result);
      io.stderr(`Baseline written: ${target}\n`);
    } else result = applyDebt(result, o.baseline, o.suppressions, io.now);
    if (o.changedFiles) {
      const text = o.changedFiles === '-' ? io.stdin() : readFileSync(o.changedFiles, 'utf8');
      result = restrictToChangedFiles(result, text.split(/\r?\n/), o.project);
    }
    const failed = fails(result, o.failOn ?? policy.failOn, policy.newOnly);
    writeReports(out, result, o.formats, failed);
    if (o.formats.has('console')) io.stdout(consoleReport(result) + '\n');
    if (o.formats.has('agent')) io.stdout(agent(result, failed));
    io.stderr(`Reports: ${out}\n`);
    if (o.command === 'check' && failed) {
      io.stderr(`Architecture policy violated. See ${resolve(out, 'index.html')}\n`);
      return VIOLATION;
    }
    return OK;
  } catch (e) {
    const message = String((e as Error).message ?? e);
    try {
      writeFailure(out, message, o.formats);
    } catch {
      // The analysis error is the primary failure; reporting problems must not mask it.
    }
    if (o.formats.has('agent')) io.stdout(agentError(message));
    io.stderr(`Architecture analysis failed (not a policy pass): ${message}\n`);
    return ERROR;
  }
}
