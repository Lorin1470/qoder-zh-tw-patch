// Report per-file CJK string-literal statistics for Qoder renderer assets.
const fs = require("fs");
const path = require("path");
const acorn = require("acorn");

const dir = process.argv[2];
const outFile = process.argv[3];
const CJK = /[\u3400-\u9fff]/;
const rows = [];
for (const name of fs.readdirSync(dir)) {
  if (!name.endsWith(".js")) continue;
  const src = fs.readFileSync(path.join(dir, name), "utf8");
  if (!CJK.test(src)) continue;
  let ast;
  try {
    ast = acorn.parse(src, {
      ecmaVersion: "latest",
      sourceType: "module",
      allowReturnOutsideFunction: true,
      allowAwaitOutsideFunction: true,
      allowHashBang: true,
    });
  } catch (e) {
    rows.push({ name, size: src.length, error: e.message.slice(0, 80) });
    continue;
  }
  const strings = [];
  (function walk(n) {
    if (!n || typeof n !== "object") return;
    if (n.type === "Literal" && typeof n.value === "string" && !n.regex && CJK.test(n.value)) {
      strings.push(n.value);
    } else if (n.type === "TemplateElement" && CJK.test(n.value.raw)) {
      strings.push(n.value.raw);
    }
    for (const k in n) {
      if (k === "start" || k === "end" || k === "loc") continue;
      const v = n[k];
      if (Array.isArray(v)) v.forEach(walk);
      else if (v && typeof v === "object") walk(v);
    }
  })(ast);
  if (!strings.length) continue;
  const uniq = [...new Set(strings)];
  rows.push({
    name,
    size: src.length,
    count: strings.length,
    uniq: uniq.length,
    chars: strings.join("").length,
    samples: uniq.slice(0, 4).map((s) => s.replace(/\s+/g, " ").slice(0, 60)),
  });
}
rows.sort((a, b) => (b.chars || 0) - (a.chars || 0));
fs.writeFileSync(outFile, JSON.stringify(rows, null, 1));
console.log("files:", rows.length);
for (const r of rows.slice(0, Number(process.argv[4] || 40))) {
  console.log(`${r.name}\tsize=${r.size}\tcount=${r.count}\tuniq=${r.uniq}\tchars=${r.chars}\t${(r.samples || []).join(" | ")}`);
}