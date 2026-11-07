// Emit JSON array of [start,end] source ranges for convertible string content:
// string literal interiors (excluding quotes) and template quasi text.
// Regex literals and comments are excluded by the parser.
const fs = require("fs");
const acorn = require("acorn");

const file = process.argv[2];
const sourceType = process.argv[3] || "module";
const src = fs.readFileSync(file, "utf8");
const ast = acorn.parse(src, {
  ecmaVersion: "latest",
  sourceType,
  allowReturnOutsideFunction: true,
  allowAwaitOutsideFunction: true,
  allowHashBang: true,
});
const ranges = [];
function walk(n) {
  if (!n || typeof n !== "object") return;
  if (n.type === "Literal" && typeof n.value === "string" && !n.regex) {
    ranges.push([n.start + 1, n.end - 1]);
  } else if (n.type === "TemplateElement") {
    if (n.end > n.start) ranges.push([n.start, n.end]);
  }
  for (const k in n) {
    if (k === "start" || k === "end" || k === "loc") continue;
    const v = n[k];
    if (Array.isArray(v)) v.forEach(walk);
    else if (v && typeof v === "object") walk(v);
  }
}
walk(ast);
ranges.sort((a, b) => a[0] - b[0]);
process.stdout.write(JSON.stringify(ranges));