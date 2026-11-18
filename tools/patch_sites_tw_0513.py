#!/usr/bin/env python3
"""Patch the Qoder 0.5.13 Sites extension for zh-TW (Windows + macOS).

The Sites extension files in 0.5.13 are byte-identical to 0.5.12, so the
patch logic and expected hashes are unchanged; only paths differ. Set
QODER_RESOURCES to override the auto-detected resources directory.
"""
import hashlib
import json
import os
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WORK = ROOT / "work"


def resources_dir() -> Path:
    env = os.environ.get("QODER_RESOURCES")
    if env:
        return Path(env)
    if sys.platform == "darwin":
        return Path("/Applications/Qoder.app/Contents/Resources")
    if sys.platform == "win32":
        return Path(os.environ["LOCALAPPDATA"]) / "Programs/Qoder/resources"
    raise SystemExit("unsupported platform; set QODER_RESOURCES")


EXT = resources_dir() / "extensions/qoder.sites"
STAGE = WORK / "0513-sites-stage"

EXPECTED = {
    "view.cjs": "bf4a2beac5ba36358ad312761cc009f699d1638e71da3b59b7d5512ce6b1ee76",
    "publishPreview.cjs": "d2dd76d7b14a00a116ee000757110e038b373423f4b8745021c8aae232fb7ae3",
    "plugin.json": "9e30e929b16f5683b85ce832362351aba8d977d89107d10dd5c9f9ce62e87a96",
}

TW_DICT = json.loads((WORK / "0513-dict/sites_tw.json").read_text(encoding="utf-8"))
TW_ANNOT = json.loads((WORK / "0513-dict/sites_tw_annot.json").read_text(encoding="utf-8"))

TW_STATUS = {
    "active": "使用中",
    "suspended": "已暫停",
    "deleting": "刪除中",
    "deleted": "已刪除",
    "ready": "已就緒",
    "uploading": "上傳中",
    "verifying": "驗證中",
    "failed": "失敗",
    "queued": "排隊中",
    "running": "執行中",
    "succeeded": "已完成",
    "cancelled": "已取消",
    "superseded": "已被取代",
}

TW_PREFIX = r"/^zh[_-](tw|hant|hk|mo)([_-]|$)/.test(l)"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def ensure(cond, msg):
    if not cond:
        raise SystemExit("PATCH ERROR: " + msg)


def patch_view(src: str) -> str:
    anchor = '},J4=e=>e.startsWith("zh")?xz:uz;'
    ensure(src.count(anchor) == 1, "view selector anchor missing")
    payload = json.dumps(TW_DICT, ensure_ascii=True, separators=(",", ":"))
    new_selector = (
        ',__QODER_SITES_TW__=' + payload + ','
        'J4=e=>{let l=String(e||"").toLowerCase();return '
        + TW_PREFIX + '?__QODER_SITES_TW__:l.startsWith("zh")?xz:uz};'
    )
    src = src.replace(anchor, "}" + new_selector, 1)
    src = patch_status(src)
    ensure("__QODER_SITES_TW__" in src, "view dictionary not injected")
    return src


def patch_preview(src: str) -> str:
    anchor = '},p7=e=>e.startsWith("zh")?up:fp;'
    ensure(src.count(anchor) == 1, "preview selector anchor missing")
    payload = json.dumps(TW_DICT, ensure_ascii=True, separators=(",", ":"))
    new_selector = (
        ',__QODER_SITES_TW__=' + payload + ','
        'p7=e=>{let l=String(e||"").toLowerCase();return '
        + TW_PREFIX + '?__QODER_SITES_TW__:l.startsWith("zh")?up:fp};'
    )
    src = src.replace(anchor, "}" + new_selector, 1)

    annot_anchor = 'H7=e=>e.toLowerCase().startsWith("zh")?pp:vp;'
    ensure(src.count(annot_anchor) == 1, "annotation selector anchor missing")
    annot_payload = json.dumps(TW_ANNOT, ensure_ascii=True, separators=(",", ":"))
    annot_selector = (
        'H7=e=>{let l=String(e||"").toLowerCase();return '
        + TW_PREFIX + '?__QODER_SITES_TW_ANNOT__:l.startsWith("zh")?mp:Pp};'
    )
    src = src.replace(
        annot_anchor,
        '__QODER_SITES_TW_ANNOT__=' + annot_payload + "," + annot_selector,
        1,
    )
    src = patch_status(src)
    ensure("__QODER_SITES_TW__" in src, "preview dictionary not injected")
    ensure("__QODER_SITES_TW_ANNOT__" in src, "annotation dictionary not injected")
    return src


def patch_status(src: str) -> str:
    obj_start = src.find('{active:["Active"')
    ensure(obj_start >= 0, "status map missing")
    func_start = src.rfind("function ", 0, obj_start)
    ensure(func_start >= 0, "status function start missing")
    header = src[func_start:obj_start]
    m = re.fullmatch(r"function (\w+)\(e,(\w+)\)\{return", header)
    ensure(m is not None, f"status function header unexpected: {header[:80]}")
    name, loc = m.group(1), m.group(2)
    mid = src.find("}[e]?.[", obj_start)
    ensure(mid >= 0, "status indexing missing")
    obj = src[obj_start: mid + 1]
    ensure(obj.startswith("{active:"), "status map parse failed")
    end_marker = '"Awaiting confirmation")}'
    end = src.find(end_marker, mid)
    ensure(end >= 0, "status function end missing")
    end += len(end_marker)
    tw_obj = json.dumps(TW_STATUS, ensure_ascii=True, separators=(",", ":"))
    replacement = (
        'function ' + name + '(e,' + loc + '){let l=String(' + loc + '||"").toLowerCase();'
        'if(' + TW_PREFIX + ')return ' + tw_obj + '[e]??"待確認";'
        'let o=' + obj + ';'
        'return o[e]?.[l.startsWith("zh")?1:0]'
        '??(l.startsWith("zh")?"待确认":"Awaiting confirmation")}'
    )
    src = src[:func_start] + replacement + src[end:]
    ensure(src.count("function " + name + "(e," + loc + "){") == 1, "status function count unexpected")
    return src


def patch_plugin(src: str) -> str:
    data = json.loads(src)
    changed = 0
    for section in ("views", "sidebarNavItems"):
        for item in data.get("contributes", {}).get(section, []):
            title = item.get("title")
            if not isinstance(title, dict):
                continue
            translations = title.setdefault("translations", {})
            translations.setdefault("zh-CN", "站点")
            for code in ("zh-TW", "zh-Hant", "zh-HK", "zh-MO"):
                translations.setdefault(code, "站點")
            changed += 1
    ensure(changed == 3, f"unexpected title count: {changed}")
    return json.dumps(data, ensure_ascii=False, indent=2) + "\n"


def main():
    view_src = EXT / "dist/browser/view.cjs"
    preview_src = EXT / "dist/browser/publishPreview.cjs"
    plugin_src = EXT / ".qoder-app-plugin/plugin.json"

    for name, path in (
        ("view.cjs", view_src),
        ("publishPreview.cjs", preview_src),
        ("plugin.json", plugin_src),
    ):
        actual = sha256(path)
        ensure(actual == EXPECTED[name], f"{name} hash mismatch: {actual}")

    if STAGE.exists():
        shutil.rmtree(STAGE)
    (STAGE / "dist/browser").mkdir(parents=True)
    (STAGE / ".qoder-app-plugin").mkdir(parents=True)

    new_view = patch_view(view_src.read_text(encoding="utf-8"))
    (STAGE / "dist/browser/view.cjs").write_text(new_view, encoding="utf-8", newline="")

    new_preview = patch_preview(preview_src.read_text(encoding="utf-8"))
    (STAGE / "dist/browser/publishPreview.cjs").write_text(new_preview, encoding="utf-8", newline="")

    new_plugin = patch_plugin(plugin_src.read_text(encoding="utf-8"))
    (STAGE / ".qoder-app-plugin/plugin.json").write_text(new_plugin, encoding="utf-8", newline="")

    for name, rel in (
        ("view.cjs", "dist/browser/view.cjs"),
        ("publishPreview.cjs", "dist/browser/publishPreview.cjs"),
        ("plugin.json", ".qoder-app-plugin/plugin.json"),
    ):
        path = STAGE / rel
        print(f"{name}\t{path.stat().st_size}\t{sha256(path)}")


if __name__ == "__main__":
    main()