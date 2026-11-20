#!/usr/bin/env node
import { readFileSync } from 'node:fs';
import { run } from './main.js';

const code = await run(process.argv.slice(2), {
  cwd: process.cwd(),
  stdout: (s) => process.stdout.write(s),
  stderr: (s) => process.stderr.write(s),
  stdin: () => readFileSync(0, 'utf8'),
});
process.exitCode = code;
