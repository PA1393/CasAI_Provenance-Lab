import ts from "typescript";

// Mol* namespaces and its Immutable.js dependency assign methods inherited
// from Object.prototype. Give these vetted dependencies their intended OWN
// properties without weakening Tauri's prototype freeze. Parse the source so
// comments, strings, function values and assignment return values stay correct.
const names = new Set(["toString", "toLocaleString", "valueOf", "constructor", "hasOwnProperty", "isPrototypeOf", "propertyIsEnumerable"]);
export function molstarFrozenPrototype(code: string, id: string): string | null {
  const path = id.replaceAll("\\", "/");
  if (!path.includes("/molstar/lib/") && !path.includes("/immutable/dist/")) return null;
  const helper = "__casaiDefineFrozenOwn";
  if (code.includes(helper)) throw new Error("Compatibility helper name collision");
  const source = ts.createSourceFile(id, code, ts.ScriptTarget.Latest, true, ts.ScriptKind.JS);
  let changed = false;
  const result = ts.transform(source, [context => root => {
    const visit: ts.Visitor = node => {
      if (ts.isBinaryExpression(node) && node.operatorToken.kind === ts.SyntaxKind.EqualsToken &&
        ((ts.isPropertyAccessExpression(node.left) && names.has(node.left.name.text)) || ts.isElementAccessExpression(node.left))) {
        changed = true;
        return ts.factory.createCallExpression(ts.factory.createIdentifier(helper), undefined, [
          ts.visitNode(node.left.expression, visit) as ts.Expression,
          ts.isPropertyAccessExpression(node.left) ? ts.factory.createStringLiteral(node.left.name.text) : ts.visitNode(node.left.argumentExpression, visit) as ts.Expression,
          ts.visitNode(node.right, visit) as ts.Expression,
        ]);
      }
      return ts.visitEachChild(node, visit, context);
    };
    return ts.visitNode(root, visit) as ts.SourceFile;
  }]);
  try {
    if (!changed) return null;
    return `function ${helper}(target, key, value) {
      if (${JSON.stringify([...names])}.includes(key) && !Object.prototype.hasOwnProperty.call(target, key)) {
        Object.defineProperty(target, key, { value, writable: true, enumerable: true, configurable: true });
      } else { target[key] = value; }
      return value;
    }\n` + ts.createPrinter().printFile(result.transformed[0]);
  } finally { result.dispose(); }
}
