import { existsSync, readFileSync } from 'node:fs';
import { basename, isAbsolute, join, sep } from 'node:path';
import ts from 'typescript';
import { AnalysisError, ArchitectureModel, Dependency, Location, ROLES, Role, Unit } from './model.js';
import { Policy } from './policy.js';
import { matches } from './selectors.js';
import {
  Config,
  Project,
  WorkspacePackage,
  configFor,
  containers,
  moduleId,
  moduleName,
  packageOf,
  real,
  rel,
} from './project.js';
import { frameworkTags, isEntityClass, isNestController, isNestHttpMethod } from './frameworks.js';

const SOURCE_EXTENSIONS = ['.ts', '.tsx', '.mts', '.cts', '.js', '.jsx', '.mjs', '.cjs'];
/** Style, media, font and data imports are bundler assets, not code dependencies. */
const ASSET =
  /\.(css|scss|sass|less|styl|pcss|svg|png|jpe?g|gif|webp|avif|ico|bmp|woff2?|ttf|eot|otf|mp4|webm|mp3|wav|ogg|json|ya?ml|toml|txt|md|html|graphql|gql|wasm)(\?.*)?$/i;

type ImportVerb = 'imports' | 'imports type' | 're-exports' | 're-exports type' | 'requires' | 'dynamically imports';

interface RawImport {
  specifier: string;
  verb: ImportVerb;
  typeOnly: boolean;
  line: number;
}

type Resolution =
  | { kind: 'internal'; file: string }
  | { kind: 'external'; name: string }
  | { kind: 'unresolved' };

function lineOf(sf: ts.SourceFile, node: ts.Node): number {
  return sf.getLineAndCharacterOfPosition(node.getStart(sf)).line + 1;
}

function literal(node: ts.Node | undefined): string | undefined {
  if (node && (ts.isStringLiteral(node) || ts.isNoSubstitutionTemplateLiteral(node))) return node.text;
  return undefined;
}

function allTypeOnly(elements: readonly { isTypeOnly: boolean }[]): boolean {
  return elements.length > 0 && elements.every((e) => e.isTypeOnly);
}

/** Static imports of one module; computed dynamic imports are only counted. */
export function collectImports(sf: ts.SourceFile): { imports: RawImport[]; computed: number } {
  const imports: RawImport[] = [];
  let computed = 0;
  const add = (specifier: string, verb: ImportVerb, typeOnly: boolean, node: ts.Node) =>
    imports.push({ specifier, verb, typeOnly, line: lineOf(sf, node) });
  const visit = (node: ts.Node): void => {
    if (ts.isImportDeclaration(node)) {
      const spec = literal(node.moduleSpecifier);
      if (spec !== undefined) {
        const c = node.importClause;
        const typeOnly =
          !!c &&
          (c.isTypeOnly ||
            (!c.name && !!c.namedBindings && ts.isNamedImports(c.namedBindings) && allTypeOnly(c.namedBindings.elements)));
        add(spec, typeOnly ? 'imports type' : 'imports', typeOnly, node);
      }
      return;
    }
    if (ts.isExportDeclaration(node)) {
      const spec = literal(node.moduleSpecifier);
      if (spec !== undefined) {
        const typeOnly =
          node.isTypeOnly ||
          (!!node.exportClause && ts.isNamedExports(node.exportClause) && allTypeOnly(node.exportClause.elements));
        add(spec, typeOnly ? 're-exports type' : 're-exports', typeOnly, node);
      }
      return;
    }
    if (ts.isImportEqualsDeclaration(node) && ts.isExternalModuleReference(node.moduleReference)) {
      const spec = literal(node.moduleReference.expression);
      if (spec !== undefined) add(spec, node.isTypeOnly ? 'imports type' : 'requires', node.isTypeOnly, node);
      return;
    }
    if (ts.isImportTypeNode(node) && ts.isLiteralTypeNode(node.argument)) {
      const spec = literal(node.argument.literal);
      if (spec !== undefined) add(spec, 'imports type', true, node);
    }
    if (ts.isCallExpression(node)) {
      const isImport = node.expression.kind === ts.SyntaxKind.ImportKeyword;
      const isRequire = ts.isIdentifier(node.expression) && node.expression.text === 'require' && node.arguments.length === 1;
      if (isImport || isRequire) {
        const spec = literal(node.arguments[0]);
        if (spec !== undefined) add(spec, isImport ? 'dynamically imports' : 'requires', false, node);
        else computed++;
      }
    }
    ts.forEachChild(node, visit);
  };
  visit(sf);
  return { imports, computed };
}

export function packageName(specifier: string): string {
  const parts = specifier.split('/');
  return specifier.startsWith('@') && parts.length > 1 ? `${parts[0]}/${parts[1]}` : parts[0];
}

function isRelative(spec: string): boolean {
  return spec === '.' || spec === '..' || spec.startsWith('./') || spec.startsWith('../') || isAbsolute(spec);
}

function matchesPathAlias(spec: string, paths: ts.MapLike<string[]> | undefined): boolean {
  for (const key of Object.keys(paths ?? {})) {
    const star = key.indexOf('*');
    if (star < 0 ? spec === key : spec.startsWith(key.slice(0, star)) && spec.endsWith(key.slice(star + 1)))
      return true;
  }
  return false;
}

class Resolver {
  private readonly caches = new Map<Config, ts.ModuleResolutionCache>();
  private readonly owned: Set<string>;

  constructor(private readonly project: Project) {
    this.owned = new Set(project.files);
  }

  private cache(config: Config): ts.ModuleResolutionCache {
    let c = this.caches.get(config);
    if (!c) {
      c = ts.createModuleResolutionCache(this.project.root, (x) => x, config.options);
      this.caches.set(config, c);
    }
    return c;
  }

  private inside(file: string): boolean {
    return !rel(this.project.root, file).startsWith('..') && !file.includes(`${sep}node_modules${sep}`);
  }

  private findSource(base: string): string | undefined {
    const stripped = base.replace(/\.d\.[cm]?ts$/, '').replace(/\.[cm]?[jt]sx?$/, '');
    for (const candidate of [base, ...SOURCE_EXTENSIONS.map((e) => stripped + e), ...SOURCE_EXTENSIONS.map((e) => join(stripped, 'index' + e))])
      if (existsSync(candidate)) {
        const r = real(candidate);
        if (this.owned.has(r)) return r;
      }
    return undefined;
  }

  /** Maps a workspace package import to its source entry instead of build output. */
  workspaceSource(pkg: WorkspacePackage, subpath: string): string | undefined {
    const candidates: string[] = [];
    if (subpath) candidates.push(join(pkg.dir, subpath), join(pkg.dir, 'src', subpath));
    else {
      const m = pkg.manifest;
      for (const field of [m.source, m.types, m.typings, m.module, m.main])
        if (typeof field === 'string') {
          candidates.push(join(pkg.dir, field));
          candidates.push(join(pkg.dir, field.replace(/^(\.\/)?(dist|build|lib|out)\//, 'src/')));
        }
      candidates.push(join(pkg.dir, 'src', 'index'), join(pkg.dir, 'index'));
    }
    for (const c of candidates) {
      const found = this.findSource(c);
      if (found) return found;
    }
    return undefined;
  }

  private workspace(spec: string): { pkg: WorkspacePackage; subpath: string } | undefined {
    for (const pkg of this.project.packages)
      if (pkg.dir !== this.project.root && (spec === pkg.name || spec.startsWith(pkg.name + '/')))
        return { pkg, subpath: spec.slice(pkg.name.length + 1) };
    return undefined;
  }

  resolve(spec: string, file: string): Resolution {
    const config = configFor(this.project, file);
    const result = ts.resolveModuleName(spec, file, config.options, ts.sys, this.cache(config)).resolvedModule;
    if (result) {
      const target = real(result.resolvedFileName);
      if (this.inside(target)) {
        if (!this.owned.has(target)) {
          const pkg = packageOf(this.project, target);
          if (pkg && pkg.dir !== this.project.root) {
            const ws = this.workspace(spec);
            const source = ws ? this.workspaceSource(ws.pkg, ws.subpath) : undefined;
            if (source) return { kind: 'internal', file: source };
          }
        }
        return { kind: 'internal', file: target };
      }
      if (isRelative(spec)) return { kind: 'external', name: rel(this.project.root, target) };
      return { kind: 'external', name: packageName(spec) };
    }
    const ws = this.workspace(spec);
    if (ws) {
      const source = this.workspaceSource(ws.pkg, ws.subpath);
      return source ? { kind: 'internal', file: source } : { kind: 'unresolved' };
    }
    if (isRelative(spec) || matchesPathAlias(spec, config.options.paths)) return { kind: 'unresolved' };
    return { kind: 'external', name: packageName(spec) };
  }
}

function single<T>(items: T[], error: string): T | undefined {
  if (items.length > 1) throw new AnalysisError(error);
  return items[0];
}

export function roleOf(policy: Policy, unitContainers: string[], name: string, label = 'role mapping'): Role {
  const roles = ROLES.filter((r) => policy.roles[r] && matches(policy.roles[r]!, unitContainers));
  return single(roles, `Ambiguous ${label} for ${name}: [${roles.join(', ')}]`) ?? 'UNCLASSIFIED';
}

export function contextOf(policy: Policy, unitContainers: string[], name: string, label = 'context mapping'): string {
  const found = policy.contexts.filter((c) => matches(c.packages, unitContainers));
  return single(found, `Ambiguous ${label} for ${name}`)?.id ?? '';
}

function requireMatch(units: Map<string, Unit>, patterns: string[], label: string): void {
  for (const u of units.values()) if (matches(patterns, u.containers)) return;
  throw new AnalysisError(`Empty selector for ${label}`);
}

function parse(file: string): ts.SourceFile {
  const kind = file.endsWith('x') ? (file.endsWith('.tsx') ? ts.ScriptKind.TSX : ts.ScriptKind.JSX) : undefined;
  return ts.createSourceFile(file, readFileSync(file, 'utf8'), ts.ScriptTarget.Latest, true, kind);
}

export function readModel(project: Project, policy: Policy): ArchitectureModel {
  const units = new Map<string, Unit>();
  const files = new Map<string, ts.SourceFile>();
  const unitFile = new Map<string, string>();
  const diagnostics = [...project.diagnostics];
  let outside = 0;
  for (const file of project.files) {
    const unitContainers = containers(project, file);
    if (!matches(policy.roots, unitContainers)) {
      outside++;
      continue;
    }
    const name = moduleName(project.root, file);
    if (units.has(name))
      throw new AnalysisError(`Ambiguous module name ${name}: ${rel(project.root, unitFile.get(name)!)} and ${rel(project.root, file)}`);
    const sf = parse(file);
    files.set(file, sf);
    unitFile.set(name, file);
    const path = rel(project.root, file);
    units.set(name, {
      name,
      containers: unitContainers,
      role: roleOf(policy, unitContainers, name),
      context: contextOf(policy, unitContainers, name),
      tags: frameworkTags(sf, path),
      location: { module: moduleId(project, file), path, symbol: name, line: 0 },
    });
  }
  if (units.size === 0 && !policy.allowEmptyAnalysis)
    throw new AnalysisError('No application modules matched roots; refusing a vacuous pass');
  if (!policy.allowEmptySelectors) {
    for (const r of ROLES) if (policy.roles[r]) requireMatch(units, policy.roles[r]!, `role ${r}`);
    for (const c of policy.contexts) requireMatch(units, c.packages, `context ${c.id}`);
    for (const c of policy.constraints) requireMatch(units, c.from, `constraint ${c.id}`);
  }

  const resolver = new Resolver(project);
  const dependencies: Dependency[] = [];
  const unresolved: string[] = [];
  let computed = 0;
  let typeOnlySkipped = 0;
  let assets = 0;
  for (const [name, unit] of units) {
    const file = unitFile.get(name)!;
    const sf = files.get(file)!;
    const found = collectImports(sf);
    computed += found.computed;
    for (const imp of found.imports) {
      if (ASSET.test(imp.specifier)) {
        assets++;
        continue;
      }
      if (imp.typeOnly && policy.typeOnlyImports === 'ignore') {
        typeOnlySkipped++;
        continue;
      }
      const r = resolver.resolve(imp.specifier, file);
      if (r.kind === 'unresolved') {
        const where = `${unit.location.path}:${imp.line}`;
        if (policy.unresolvedImports === 'fail')
          throw new AnalysisError(
            `Unresolved import of an owned module: '${imp.specifier}' in ${where}. Fix the import or set unresolvedImports: warn.`,
          );
        unresolved.push(`'${imp.specifier}' in ${where}`);
        continue;
      }
      const target = r.kind === 'internal' ? moduleName(project.root, r.file) : r.name;
      if (target === name) continue;
      const location: Location = { ...unit.location, line: imp.line };
      dependencies.push({
        origin: name,
        target,
        evidence: `Module <${name}> ${imp.verb} <${target}> (${basename(file)}:${imp.line})`,
        location,
        kind: 'IMPORT',
        targetContainers: r.kind === 'internal' ? containers(project, r.file) : [r.name],
        externalSpecifier: r.kind === 'external' ? imp.specifier : undefined,
      });
    }
  }
  dependencies.push(...httpEntityExposures(project, units, unitFile));
  dependencies.sort((a, b) => cmp(a.origin, b.origin) || cmp(a.target, b.target) || cmp(a.evidence, b.evidence));

  diagnostics.push(
    'Static imports only: runtime DI containers, computed dynamic imports and require() with non-literal arguments are not resolved.',
  );
  diagnostics.push(
    policy.typeOnlyImports === 'ignore'
      ? `Type-only imports ignored (typeOnlyImports: ignore): ${typeOnlySkipped}`
      : 'Type-only imports count as dependencies (typeOnlyImports: count).',
  );
  if (computed > 0) diagnostics.push(`Computed dynamic imports not analyzed: ${computed}`);
  if (assets > 0) diagnostics.push(`Asset imports (styles, media, data files) not treated as dependencies: ${assets}`);
  if (unresolved.length > 0) {
    diagnostics.push(`Unresolved imports ignored (unresolvedImports: warn): ${unresolved.length}`);
    for (const u of unresolved.slice(0, 20)) diagnostics.push(`Unresolved import ${u}`);
  }
  const unclassified = [...units.values()].filter((u) => u.role === 'UNCLASSIFIED').length;
  diagnostics.push(`Unclassified application modules: ${unclassified} / ${units.size}`);
  if (outside > 0)
    diagnostics.push(`Source files outside roots (not checked, and their own imports are ignored): ${outside}`);
  return { units, dependencies, diagnostics };
}

function cmp(a: string, b: string): number {
  return a < b ? -1 : a > b ? 1 : 0;
}

/** FW-002: NestJS handler signatures that expose a persistence entity, via the type checker. */
function httpEntityExposures(project: Project, units: Map<string, Unit>, unitFile: Map<string, string>): Dependency[] {
  const controllers = [...units.values()].filter((u) => u.tags.includes('nest.endpoint'));
  if (controllers.length === 0) return [];
  const base = project.configs[0].options;
  const program = ts.createProgram({
    rootNames: project.files,
    options: { ...base, noEmit: true, skipLibCheck: true, allowJs: base.allowJs ?? !project.hasTsconfig },
  });
  const checker = program.getTypeChecker();
  const out: Dependency[] = [];
  for (const unit of controllers) {
    const file = unitFile.get(unit.name)!;
    const sf = program.getSourceFile(file) ?? program.getSourceFiles().find((s) => real(s.fileName) === file);
    if (!sf) continue;
    const visit = (node: ts.Node): void => {
      if (ts.isClassDeclaration(node) && node.name && isNestController(node, sf)) {
        for (const member of node.members) {
          if (!ts.isMethodDeclaration(member) || !isNestHttpMethod(member, sf)) continue;
          const method = `${unit.name}#${node.name.text}.${member.name.getText(sf)}`;
          const signature = checker.getSignatureFromDeclaration(member);
          const types: ts.Type[] = [];
          if (signature) types.push(checker.getReturnTypeOfSignature(signature));
          for (const p of member.parameters) types.push(checker.getTypeAtLocation(p));
          const entities = new Map<string, string>();
          for (const t of types) collectEntities(checker, t, project, entities, new Set(), 0);
          for (const [entity, entityFile] of [...entities].sort()) {
            out.push({
              origin: unit.name,
              target: moduleName(project.root, entityFile),
              evidence: `HTTP method <${method}> exposes persistence entity <${entity}>`,
              location: { ...unit.location, symbol: method, line: lineOf(sf, member.name) },
              kind: 'HTTP_ENTITY_EXPOSURE',
              targetContainers: containers(project, entityFile),
            });
          }
        }
      }
      ts.forEachChild(node, visit);
    };
    visit(sf);
  }
  return out;
}

function collectEntities(
  checker: ts.TypeChecker,
  type: ts.Type,
  project: Project,
  out: Map<string, string>,
  seen: Set<ts.Type>,
  depth: number,
): void {
  if (depth > 6 || seen.has(type)) return;
  seen.add(type);
  if (type.isUnionOrIntersection()) {
    for (const t of type.types) collectEntities(checker, t, project, out, seen, depth + 1);
    return;
  }
  const symbol = type.aliasSymbol ?? type.getSymbol();
  for (const decl of symbol?.declarations ?? []) {
    if (!ts.isClassDeclaration(decl) || !decl.name) continue;
    const sf = decl.getSourceFile();
    const file = real(sf.fileName);
    if (rel(project.root, file).startsWith('..') || file.includes(`${sep}node_modules${sep}`)) continue;
    if (isEntityClass(decl, sf)) out.set(`${moduleName(project.root, file)}#${decl.name.text}`, file);
  }
  for (const t of type.aliasTypeArguments ?? []) collectEntities(checker, t, project, out, seen, depth + 1);
  if ((type as ts.ObjectType).objectFlags & ts.ObjectFlags.Reference)
    for (const t of checker.getTypeArguments(type as ts.TypeReference)) collectEntities(checker, t, project, out, seen, depth + 1);
}
