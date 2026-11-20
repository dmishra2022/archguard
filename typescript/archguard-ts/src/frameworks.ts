import ts from 'typescript';

/** A local name bound by an import: `imported` is the exported name, 'default' or '*'. */
export interface Binding {
  module: string;
  imported: string;
}

export const ENDPOINT_TAGS = new Set([
  'nest.endpoint',
  'express.endpoint',
  'fastify.endpoint',
  'koa.endpoint',
  'hono.endpoint',
  'next.endpoint',
  'graphql.endpoint',
]);

const NEST = ['@nestjs/common'];
const GRAPHQL_RESOLVERS = ['@nestjs/graphql', 'type-graphql'];
const ENTITY_MODULES = ['typeorm', '@mikro-orm/*'];
const NEST_MONGOOSE = ['@nestjs/mongoose'];
export const NEST_HTTP_METHODS = new Set(['Get', 'Post', 'Put', 'Patch', 'Delete', 'Options', 'Head', 'All']);
const ROUTE_METHODS = new Set(['get', 'post', 'put', 'patch', 'delete', 'del', 'all', 'options', 'head', 'route']);
const ROUTER_FRAMEWORKS: [string[], string][] = [
  [['express'], 'express.endpoint'],
  [['fastify'], 'fastify.endpoint'],
  [['@koa/router', 'koa-router'], 'koa.endpoint'],
  [['hono'], 'hono.endpoint'],
];
const NEXT_ROUTE_EXPORTS = new Set(['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'HEAD', 'OPTIONS']);

export function moduleMatches(module: string, patterns: readonly string[]): boolean {
  return patterns.some((p) =>
    p.endsWith('/*') ? module.startsWith(p.slice(0, -1)) : module === p || module.startsWith(p + '/'),
  );
}

const bindingCache = new WeakMap<ts.SourceFile, Map<string, Binding>>();

export function bindings(sf: ts.SourceFile): Map<string, Binding> {
  let out = bindingCache.get(sf);
  if (out) return out;
  out = new Map();
  for (const s of sf.statements) {
    if (!ts.isImportDeclaration(s) || !ts.isStringLiteral(s.moduleSpecifier) || !s.importClause) continue;
    const module = s.moduleSpecifier.text;
    const clause = s.importClause;
    if (clause.name) out.set(clause.name.text, { module, imported: 'default' });
    const named = clause.namedBindings;
    if (named && ts.isNamespaceImport(named)) out.set(named.name.text, { module, imported: '*' });
    if (named && ts.isNamedImports(named))
      for (const e of named.elements)
        out.set(e.name.text, { module, imported: (e.propertyName ?? e.name).text });
  }
  bindingCache.set(sf, out);
  return out;
}

/** Resolves `X`, `X()`, `ns.X` or `ns.X()` to the imported module and exported name. */
export function resolveReference(expr: ts.Expression, sf: ts.SourceFile): Binding | undefined {
  const e = ts.isCallExpression(expr) ? expr.expression : expr;
  const b = bindings(sf);
  if (ts.isIdentifier(e)) return b.get(e.text);
  if (ts.isPropertyAccessExpression(e) && ts.isIdentifier(e.expression)) {
    const ns = b.get(e.expression.text);
    if (ns && (ns.imported === '*' || ns.imported === 'default'))
      return { module: ns.module, imported: e.name.text };
  }
  return undefined;
}

export function hasDecorator(
  node: ts.Node,
  sf: ts.SourceFile,
  modules: readonly string[],
  names: ReadonlySet<string> | string,
): boolean {
  if (!ts.canHaveDecorators(node)) return false;
  for (const d of ts.getDecorators(node) ?? []) {
    const ref = resolveReference(d.expression, sf);
    if (!ref || !moduleMatches(ref.module, modules)) continue;
    if (typeof names === 'string' ? ref.imported === names : names.has(ref.imported)) return true;
  }
  return false;
}

export function isNestController(node: ts.ClassDeclaration, sf: ts.SourceFile): boolean {
  return hasDecorator(node, sf, NEST, 'Controller');
}

export function isEntityClass(node: ts.ClassDeclaration, sf: ts.SourceFile): boolean {
  return hasDecorator(node, sf, ENTITY_MODULES, 'Entity') || hasDecorator(node, sf, NEST_MONGOOSE, 'Schema');
}

export function isNestHttpMethod(node: ts.MethodDeclaration, sf: ts.SourceFile): boolean {
  return hasDecorator(node, sf, NEST, NEST_HTTP_METHODS);
}

function exportsNames(sf: ts.SourceFile): Set<string> {
  const names = new Set<string>();
  const exported = (n: ts.Node) =>
    ts.canHaveModifiers(n) && (ts.getModifiers(n) ?? []).some((m) => m.kind === ts.SyntaxKind.ExportKeyword);
  const isDefault = (n: ts.Node) =>
    ts.canHaveModifiers(n) && (ts.getModifiers(n) ?? []).some((m) => m.kind === ts.SyntaxKind.DefaultKeyword);
  for (const s of sf.statements) {
    if (ts.isExportAssignment(s)) names.add('default');
    if (ts.isFunctionDeclaration(s) && exported(s)) names.add(isDefault(s) ? 'default' : (s.name?.text ?? 'default'));
    if (ts.isClassDeclaration(s) && exported(s)) names.add(isDefault(s) ? 'default' : (s.name?.text ?? 'default'));
    if (ts.isVariableStatement(s) && exported(s))
      for (const d of s.declarationList.declarations) if (ts.isIdentifier(d.name)) names.add(d.name.text);
    if (ts.isExportDeclaration(s) && !s.moduleSpecifier && s.exportClause && ts.isNamedExports(s.exportClause))
      for (const e of s.exportClause.elements) names.add(e.name.text);
  }
  return names;
}

/** Static framework tags for one module (spec MODEL-002, FW-001). */
export function frameworkTags(sf: ts.SourceFile, relativePath: string): string[] {
  const tags = new Set<string>();
  const imported = new Set<string>();
  for (const s of sf.statements)
    if (ts.isImportDeclaration(s) && ts.isStringLiteral(s.moduleSpecifier)) {
      imported.add(s.moduleSpecifier.text);
      if (s.moduleSpecifier.text === '@prisma/client' && !s.importClause?.isTypeOnly) tags.add('prisma.client');
    }
  let routeCalls = false;
  const visit = (node: ts.Node): void => {
    if (ts.isClassDeclaration(node)) {
      if (isNestController(node, sf)) tags.add('nest.endpoint');
      if (hasDecorator(node, sf, GRAPHQL_RESOLVERS, 'Resolver')) tags.add('graphql.endpoint');
      if (hasDecorator(node, sf, NEST, 'Injectable')) tags.add('nest.provider');
      if (hasDecorator(node, sf, NEST, 'Module')) tags.add('nest.module');
      if (isEntityClass(node, sf)) tags.add('persistence.entity');
    } else if (ts.isNewExpression(node)) {
      const ref = resolveReference(node.expression, sf);
      if (ref && ref.module === 'mongoose' && ref.imported === 'Schema') tags.add('mongoose.schema');
    } else if (ts.isCallExpression(node) && ts.isPropertyAccessExpression(node.expression)) {
      const first = node.arguments[0];
      if (
        ROUTE_METHODS.has(node.expression.name.text) &&
        first &&
        (ts.isStringLiteral(first) || ts.isNoSubstitutionTemplateLiteral(first)) &&
        first.text.startsWith('/')
      )
        routeCalls = true;
    }
    ts.forEachChild(node, visit);
  };
  visit(sf);
  if (routeCalls)
    for (const [modules, tag] of ROUTER_FRAMEWORKS)
      if ([...imported].some((m) => moduleMatches(m, modules))) tags.add(tag);
  const segments = relativePath.split('/');
  const file = segments[segments.length - 1];
  const names = exportsNames(sf);
  if (segments.includes('app') && /^route\.[cm]?[jt]sx?$/.test(file) && [...names].some((n) => NEXT_ROUTE_EXPORTS.has(n)))
    tags.add('next.endpoint');
  const pages = segments.indexOf('pages');
  if (pages >= 0 && segments[pages + 1] === 'api' && names.has('default')) tags.add('next.endpoint');
  return [...tags].sort();
}
