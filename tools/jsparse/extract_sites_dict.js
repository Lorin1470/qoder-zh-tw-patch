// Extract the Sites zh-CN dictionaries (plain string maps) from the minified
// view.cjs / publishPreview.cjs bundles so they can be converted to zh-TW.
const fs = require("fs");

function findObject(src, marker) {
  const start = src.indexOf(marker);
  if (start < 0) throw new Error("marker not found: " + marker);
  let i = start + marker.length - 1; // at '{'
  let depth = 0;
  let inStr = false;
  let quote = "";
  for (; i < src.length; i++) {
    const c = src[i];
    if (inStr) {
      if (c === "\\") { i++; continue; }
      if (c === quote) inStr = false;
      continue;
    }
    if (c === '"' || c === "'" || c === "`") { inStr = true; quote = c; continue; }
    if (c === "{") depth++;
    else if (c === "}" && --depth === 0) return src.slice(start + marker.length - 1, i + 1);
  }
  throw new Error("unterminated object: " + marker);
}

const viewSrc = fs.readFileSync(process.argv[2], "utf8");
const previewSrc = fs.readFileSync(process.argv[3], "utf8");
const view = Function("return (" + findObject(viewSrc, ",Du={") + ")")();
const annot = Function("return (" + findObject(previewSrc, "var pp={") + ")")();
process.stdout.write(JSON.stringify({ view, annot }));