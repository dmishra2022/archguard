import { existsSync, readdirSync, readFileSync, realpathSync, statSync } from 'node:fs';
import { basename, dirname, join, relative, resolve, sep } from 'node:path';
import ts from 'typescript';

const TS_EXTENSIONS = ['.ts', '.tsx', '.mts', '.cts'];
const JS_EXTENSIONS = ['.js', '.jsx', '.mjs', '.cjs'];
const SKIPPED_DIRECTORIES = new Set(['node_modules', '__tests__', '__mocks__']);
/** Build output names, skipped only directly under a package root. */
const OUTPUT_DIRECTORIES = new Set(['dist', 'build', 'out', 'coverage', 'reports', 'target']);
const TEST_FILE = /\.(test|spec)\.[cm]?[jt]sx?$/;

export interface Config {
  file: string | null;
  options: ts.CompilerOptions;
  fileNames: Set<string>;
}

export interface WorkspacePackage {
  name: string;
  dir: string;
  manifest: any;
}

export interface Project {
  root: string;
  configs: Config[];
  files: string[];
  packages: WorkspacePackage[];
  hasTsconfig: boolean;
  diagnostics: string[];
}

export function real(p: string): string {
  try {
    return realpathSync.native(p);
  } catch {
    return resolve(p);
  }
}

export function posix(p: string): string {
  return p.split(sep).join('/');
}

export function rel(root: string, file: string): string {
  return posix(relative(root, file));
}

export function isSource(file: string, allowJs: boolean): boolean {
  if (file.endsWith('.d.ts') || file.endsWith('.d.mts') || file.endsWith('.d.cts')) return false;
  if (TEST_FILE.test(file)) return false;
  return TS_EXTENSIONS.some((e) => file.endsWith(e)) || (allowJs && JS_EXTENSIONS.some((e) => file.endsWith(e)));
}

/** Module name: project-relative POSIX path without the source extension. */
export function moduleName(root: string, file: string): string {
  return rel(root, file).replace(/\.d\.[cm]?ts$/, '').replace(/\.[cm]?[jt]sx?$/, '');
}

function walk(dir: string, out: string[]): void {
  let entries: import('node:fs').Dirent[];
  try {
    entries = readdirSync(dir, { withFileTypes: true });
  } catch {
    return;
  }
  const packageRoot = entries.some(
    (e) => e.isFile() && (e.name === 'package.json' || e.name === 'tsconfig.json'),
  );
  for (const e of entries.sort((a, b) => (a.name < b.name ? -1 : a.name > b.name ? 1 : 0))) {
    if (e.name.startsWith('.') && e.isDirectory()) continue;
    const full = join(dir, e.name);
    if (e.isDirectory()) {
      if (SKIPPED_DIRECTORIES.has(e.name) || (packageRoot && OUTPUT_DIRECTORIES.has(e.name))) continue;
      walk(full, out);
    } else if (e.isFile()) out.push(full);
  }
}

const parseHost: ts.ParseConfigFileHost = {
  ...ts.sys,
  onUnRecoverableConfigFileDiagnostic: (d) => {
    throw new Error(`Invalid tsconfig: ${ts.flattenDiagnosticMessageText(d.messageText, '\n')}`);
  },
};

function loadConfig(file: string, seen: Set<string>, out: Config[]): void {
  const path = real(file);
  if (seen.has(path)) return;
  seen.add(path);
  const parsed = ts.getParsedCommandLineOfConfigFile(path, { noEmit: true }, parseHost);
  if (!parsed) throw new Error(`Cannot read tsconfig: ${path}`);
  out.push({ file: path, options: parsed.options, fileNames: new Set(parsed.fileNames.map(real)) });
  for (const ref of parsed.projectReferences ?? []) {
    const target = ts.resolveProjectReferencePath(ref);
    if (existsSync(target)) loadConfig(target, seen, out);
  }
}

function discoverPackages(root: string): WorkspacePackage[] {
  const manifests: string[] = [];
  walk(root, manifests);
  const out: WorkspacePackage[] = [];
  for (const file of manifests) {
    if (basename(file) !== 'package.json') continue;
    try {
      const manifest = JSON.parse(readFileSync(file, 'utf8'));
      if (typeof manifest.name === 'string' && manifest.name)
        out.push({ name: manifest.name, dir: real(dirname(file)), manifest });
    } catch {
      // Unparseable manifests are not workspace packages.
    }
  }
  return out.sort((a, b) => b.dir.length - a.dir.length);
}

export const DEFAULT_OPTIONS: ts.CompilerOptions = {
  allowJs: true,
  checkJs: false,
  jsx: ts.JsxEmit.Preserve,
  module: ts.ModuleKind.ESNext,
  moduleResolution: ts.ModuleResolutionKind.Bundler,
  target: ts.ScriptTarget.ES2022,
  resolveJsonModule: true,
  experimentalDecorators: true,
  noEmit: true,
};

export function loadProject(rootDir: string, sourceRoots: string[] | null, tsconfig?: string): Project {
  const root = real(rootDir);
  if (!existsSync(root) || !statSync(root).isDirectory())
    throw new Error(`Project directory not found: ${rootDir}`);
  const configs: Config[] = [];
  const configFile = tsconfig ? resolve(tsconfig) : join(root, 'tsconfig.json');
  if (tsconfig && !existsSync(configFile)) throw new Error(`tsconfig not found: ${tsconfig}`);
  if (existsSync(configFile)) loadConfig(configFile, new Set(), configs);
  const hasTsconfig = configs.length > 0;
  if (!hasTsconfig) configs.push({ file: null, options: DEFAULT_OPTIONS, fileNames: new Set() });
  const allowJs = !hasTsconfig || configs.some((c) => c.options.allowJs);

  const roots = sourceRoots ?? (existsSync(join(root, 'src')) ? ['src'] : ['.']);
  const files: string[] = [];
  const seen = new Set<string>();
  for (const r of roots) {
    const dir = resolve(root, r);
    if (!existsSync(dir)) throw new Error(`Source root not found: ${r}`);
    const found: string[] = [];
    walk(dir, found);
    for (const f of found) {
      const file = real(f);
      if (isSource(file, allowJs) && !seen.has(file) && !rel(root, file).startsWith('..')) {
        seen.add(file);
        files.push(file);
      }
    }
  }
  files.sort();
  const diagnostics: string[] = [];
  diagnostics.push(
    hasTsconfig
      ? `Module resolution: ${configs.map((c) => rel(root, c.file!)).join(', ')}`
      : 'No tsconfig.json: default module resolution (Bundler) with JavaScript sources; FW-002 type resolution is best effort.',
  );
  diagnostics.push(`Source roots: ${roots.join(', ')} (test files, declaration files and build output are excluded)`);
  const packages = discoverPackages(root);
  if (!packages.some((p) => p.dir === root))
    diagnostics.push(
      `No package.json name at the project root: module ID defaults to the directory name '${basename(root)}'. Set a package name so fingerprints are stable across checkouts.`,
    );
  return { root, configs, files, packages, hasTsconfig, diagnostics };
}

export function configFor(project: Project, file: string): Config {
  return project.configs.find((c) => c.fileNames.has(file)) ?? project.configs[0];
}

export function packageOf(project: Project, file: string): WorkspacePackage | undefined {
  return project.packages.find((p) => file === p.dir || file.startsWith(p.dir + sep));
}

/** Selector containers: the directory path, plus `<package name>/<dir within package>`. */
export function containers(project: Project, file: string): string[] {
  const dir = rel(project.root, dirname(file));
  const out = [dir === '.' ? '' : dir];
  const pkg = packageOf(project, file);
  if (pkg) {
    const inner = rel(pkg.dir, dirname(file));
    out.push(inner === '' || inner === '.' ? pkg.name : `${pkg.name}/${inner}`);
  }
  return out;
}

export function moduleId(project: Project, file: string): string {
  return packageOf(project, file)?.name ?? basename(project.root);
}
