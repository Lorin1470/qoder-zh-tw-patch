// Extract zh / zh-HK resource objects from Qoder 0.5.7 bundles using acorn.
const fs = require("fs");
const path = require("path");
const acorn = require("acorn");

const ROOT = path.resolve(__dirname, "../..");
const ASSETS = path.join(ROOT, "work/0512-original/out/renderer/assets");
const OUT = path.join(ROOT, "work/0512-dict");
fs.mkdirSync(OUT, { recursive: true });

function parse(file) {
  const src = fs.readFileSync(path.join(ASSETS, file), "utf8");
  return { src, ast: acorn.parse(src, { sourceType: "module", ecmaVersion: "latest" }) };
}

function declarators(ast) {
  const map = new Map();
  (function walk(node) {
    if (!node || typeof node.type !== "string") return;
    if (node.type === "VariableDeclarator" && node.id.type === "Identifier" && node.init) {
      if (!map.has(node.id.name)) map.set(node.id.name, node.init);
    }
    if (node.type === "FunctionDeclaration" && node.id) {
      if (!map.has(node.id.name)) map.set(node.id.name, node);
    }
    for (const key of Object.keys(node)) {
      if (key === "start" || key === "end") continue;
      const child = node[key];
      if (Array.isArray(child)) child.forEach(walk);
      else if (child && typeof child.type === "string") walk(child);
    }
  })(ast);
  return map;
}

const vm = require("vm");

function makeResolver(src, decls) {
  const cache = new Map();
  function resolve(prop) {
    if (typeof prop !== "string") return undefined;
    if (cache.has(prop)) return cache.get(prop);
    const node = decls.get(prop);
    if (!node) return undefined;
    const val = vm.runInContext("(" + src.slice(node.start, node.end) + ")", context);
    cache.set(prop, val);
    return val;
  }
  const context = vm.createContext(new Proxy({}, {
    has: (t, prop) => decls.has(prop) || cache.has(prop),
    getOwnPropertyDescriptor: (t, prop) =>
      (decls.has(prop) || cache.has(prop))
        ? { configurable: true, enumerable: true, get: () => resolve(prop) }
        : undefined,
    get: (t, prop) => resolve(prop),
  }));
  return (node, label) => {
    try {
      return vm.runInContext("(" + src.slice(node.start, node.end) + ")", context);
    } catch (e) {
      throw new Error(label + " eval failed: " + e.message);
    }
  };
}

// i18n resources: execute top-level declarations in source order with stubs,
// then read the merged Wt object.
{
  const { src, ast } = parse("C4HI_h4X.js");
  const context = vm.createContext({
    console,
    navigator: { languages: ["zh-TW"], language: "zh-TW" },
    localStorage: { getItem: () => null, setItem: () => {} },
    window: { addEventListener: () => {} },
    document: { documentElement: {} },
    setTimeout, clearTimeout, setInterval, clearInterval,
    Jt: () => ({ isInitialized: false, use: () => ({ init: () => {} }), on: () => {}, changeLanguage: () => {}, options: {} }),
    $t: {}, Zt: {},
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
        vm.runInContext(code, context, { timeout: 5000 });
        executed++;
      } catch (e) {
        skipped++;
      }
    }
  }
  const Wt = vm.runInContext("zt", context);
  if (!Wt || !Wt.zh || !Wt["zh-HK"]) throw new Error("Wt resources not available");
  fs.writeFileSync(path.join(OUT, "new_zh.json"), JSON.stringify(Wt.zh.translation));
  fs.writeFileSync(path.join(OUT, "new_zhHK.json"), JSON.stringify(Wt["zh-HK"].translation));
  console.log("i18n decls executed:", executed, "skipped:", skipped);
  console.log("i18n zh keys:", Object.keys(Wt.zh.translation).length, "zh-HK keys:", Object.keys(Wt["zh-HK"].translation).length);
}

// issueDrawer (Rf2) and projectBoard (_T2) zh resources
{
  const { src, ast } = parse("CAGvh22m.js");
  const decls = declarators(ast);
  const resolve = makeResolver(src, decls);
  for (const [constName, outName] of [["D2t", "mf2_zh.json"], ["kBt", "fT2_zh.json"]]) {
    const init = decls.get(constName);
    if (!init) throw new Error(constName + " not found");
    const obj = resolve(init, constName);
    fs.writeFileSync(path.join(OUT, outName), JSON.stringify(obj.zh));
    console.log(constName, "zh keys:", Object.keys(obj.zh).length);
  }
}