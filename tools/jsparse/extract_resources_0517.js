// Extract zh / zh-HK resource objects from Qoder 0.5.17 bundles using acorn.
const fs = require("fs");
const path = require("path");
const vm = require("vm");
const acorn = require("acorn");

const ROOT = path.resolve(__dirname, "../..");
const ASSETS = process.env.QODER_ASSETS
  ? path.resolve(process.env.QODER_ASSETS)
  : path.join(ROOT, "work/0517-original/out/renderer/assets");
const OUT = path.join(ROOT, "work/0517-dict");
fs.mkdirSync(OUT, { recursive: true });

function parse(file) {
  const src = fs.readFileSync(path.join(ASSETS, file), "utf8");
  return { src, ast: acorn.parse(src, { sourceType: "module", ecmaVersion: "latest" }) };
}

{
  const { src, ast } = parse("D7G81Cst.js");
  const context = vm.createContext({
    console,
    navigator: { languages: ["zh-TW"], language: "zh-TW" },
    localStorage: { getItem: () => null, setItem: () => {} },
    window: { addEventListener: () => {} },
    document: { documentElement: {} },
    setTimeout, clearTimeout, setInterval, clearInterval,
    // imported from UnNhyzqB.js / ClMoALKS.js
    Xe: (v) => v || "en",
    g: {
      isInitialized: true,
      options: { fallbackLng: ["en"] },
      use: () => ({ init: () => {} }),
      on: () => {},
      changeLanguage: () => {},
      addResourceBundle: () => {},
      language: "en",
    },
    Te: ["en"], Qe: (v) => v, et: (a, b) => a || b[0], tt: () => true,
    it: () => {}, nt: () => {}, ot: {},
  });
  let executed = 0, skipped = 0;
  for (const node of ast.body) {
    if (node.type !== "FunctionDeclaration") continue;
    try {
      vm.runInContext(src.slice(node.start, node.end), context);
    } catch (e) {
      skipped++;
    }
  }
  for (const node of ast.body) {
    if (node.type === "ClassDeclaration") {
      try {
        vm.runInContext(src.slice(node.start, node.end), context);
      } catch (e) {
        skipped++;
      }
      continue;
    }
    if (node.type !== "VariableDeclaration") continue;
    for (const d of node.declarations) {
      if (!d.init) continue;
      const code = "var " + src.slice(d.start, d.end) + ";";
      try {
        vm.runInContext(code, context, { timeout: 20000 });
        executed++;
      } catch (e) {
        skipped++;
      }
    }
  }
  const Ye = vm.runInContext("Ye", context);
  if (!Ye || !Ye.zh || !Ye["zh-HK"]) throw new Error("Ye resources not available");
  fs.writeFileSync(path.join(OUT, "new_zh.json"), JSON.stringify(Ye.zh.translation));
  fs.writeFileSync(path.join(OUT, "new_zhHK.json"), JSON.stringify(Ye["zh-HK"].translation));
  console.log("i18n decls executed:", executed, "skipped:", skipped);
  console.log(
    "i18n zh keys:", Object.keys(Ye.zh.translation).length,
    "zh-HK keys:", Object.keys(Ye["zh-HK"].translation).length,
  );
}