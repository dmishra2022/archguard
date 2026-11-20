// Copies the language-neutral spec catalog into the package so the published CLI is self-contained.
import { cpSync, rmSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const pkg = join(dirname(fileURLToPath(import.meta.url)), '..');
const source = join(pkg, '..', '..', 'spec');
const target = join(pkg, 'spec');
rmSync(target, { recursive: true, force: true });
for (const part of ['index.yml', 'profiles', 'rules', 'infrastructure', 'schemas']) {
  cpSync(join(source, part), join(target, part), { recursive: true });
}
console.log(`Copied spec catalog to ${target}`);
