# -*- coding: utf-8 -*-
"""Patch the Qoder 0.5.17 Sites extension for zh-TW.

Reads the pristine 0.5.17 extension copy from work/0517-sites-original and
stages the patched files in work/0517-sites-stage. The catalog hashes are
updated separately by patch_catalog_tw_0517.py after this runs.
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ORIG = ROOT / "work" / "0517-sites-original"
DICT = ROOT / "work" / "0517-dict"
STAGE = ROOT / "work" / "0517-sites-stage"

TW_RE = r"/^zh[_-](?:tw|hant)(?:-|$)/"


def compact(obj):
    return json.dumps(obj, ensure_ascii=True, separators=(",", ":"))


def patch(src, old, new, label):
    if src.count(old) != 1:
        raise SystemExit(f"[{label}] expected 1 occurrence, found {src.count(old)}")
    return src.replace(old, new, 1)




def patch_status_map(src, func_name, loc_name, status_payload, label):
    old = f"function {func_name}(e,{loc_name}){{return{{active:"
    new = (
        f"function {func_name}(e,{loc_name}){{"
        f'const zl=String({loc_name}||"").toLowerCase().replace(/_/g,"-");'
        f'if({TW_RE}.test(zl))return {status_payload}[e]??"待確認";'
        "return{active:"
    )
    return patch(src, old, new, label)


def patch_view():
    src = (ORIG / "dist/browser/view.cjs").read_text("utf-8")
    payload = compact(json.loads((DICT / "sites_tw.json").read_text("utf-8")))
    status = compact(json.loads((DICT / "sites_status_tw.json").read_text("utf-8")))
    old = 'T4=e=>e.startsWith("zh")?Du:Au;'
    new = (
        f"__QODER_SITES_TW__={payload},"
        'T4=e=>{let l=String(e||"").toLowerCase().replace(/_/g,"-");'
        f"return{TW_RE}.test(l)?__QODER_SITES_TW__:l.startsWith(\"zh\")?Du:Au}};"
    )
    src = patch(src, old, new, "view-selector")
    src = patch_status_map(src, "gs", "n", status, "view-status")
    out = STAGE / "dist/browser/view.cjs"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(src, "utf-8")
    print(f"wrote view.cjs ({len(src)} chars)")


def patch_preview():
    src = (ORIG / "dist/browser/publishPreview.cjs").read_text("utf-8")
    view = compact(json.loads((DICT / "sites_tw.json").read_text("utf-8")))
    annot = compact(json.loads((DICT / "sites_tw_annot.json").read_text("utf-8")))
    status = compact(json.loads((DICT / "sites_status_tw.json").read_text("utf-8")))

    old = 'p7=e=>e.startsWith("zh")?up:fp;'
    new = (
        f"__QODER_SITES_TW__={view},__QODER_SITES_TW_ANNOT__={annot},"
        'p7=e=>{let l=String(e||"").toLowerCase().replace(/_/g,"-");'
        f"return{TW_RE}.test(l)?__QODER_SITES_TW__:l.startsWith(\"zh\")?up:fp}};"
    )
    src = patch(src, old, new, "preview-selector")

    old = 'H7=e=>e.toLowerCase().startsWith("zh")?pp:vp;'
    new = (
        'H7=e=>{let l=String(e||"").toLowerCase().replace(/_/g,"-");'
        f"return{TW_RE}.test(l)?__QODER_SITES_TW_ANNOT__:l.startsWith(\"zh\")?pp:vp}};"
    )
    src = patch(src, old, new, "preview-annotation-selector")
    src = patch_status_map(src, "PL", "r", status, "preview-status")
    out = STAGE / "dist/browser/publishPreview.cjs"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(src, "utf-8")
    print(f"wrote publishPreview.cjs ({len(src)} chars)")


def patch_manifest():
    data = json.loads((ORIG / ".qoder-app-plugin/plugin.json").read_text("utf-8"))
    seen = 0

    def walk(node):
        nonlocal seen
        if isinstance(node, dict):
            tr = node.get("translations")
            if isinstance(tr, dict) and "zh-CN" in tr and "zh-TW" not in tr:
                tr["zh-TW"] = tr["zh-CN"].replace("站点", "網站")
                seen += 1
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    walk(data)
    if seen != 3:
        raise SystemExit(f"expected 3 translated titles, patched {seen}")
    out = STAGE / ".qoder-app-plugin/plugin.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", "utf-8")
    print(f"wrote plugin.json ({seen} zh-TW titles)")


def main():
    patch_view()
    patch_preview()
    patch_manifest()


if __name__ == "__main__":
    main()