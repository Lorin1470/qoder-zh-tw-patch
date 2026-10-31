# -*- coding: utf-8 -*-
"""Update the packaged extension catalog for the zh-TW Sites patch."""

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CATALOG = Path("/Applications/Qoder.app/Contents/Resources/extensions/catalog.v1.json")
PLUGIN = ROOT / "work" / "sites_stage" / ".qoder-app-plugin" / "plugin.json"
STAGE = ROOT / "work" / "sites_stage" / "catalog.v1.json"

TARGETS = {
    ".qoder-app-plugin/plugin.json": "plugin.json",
    "dist/browser/publishPreview.cjs": "publishPreview.cjs",
    "dist/browser/view.cjs": "view.cjs",
}


def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    data = json.loads(CATALOG.read_text("utf-8"))
    plugins = data.get("plugins")
    if not isinstance(plugins, list):
        raise SystemExit("catalog has no plugins list")
    entries = [p for p in plugins if p.get("id") == "qoder.sites"]
    if len(entries) != 1:
        raise SystemExit(f"expected one qoder.sites entry, found {len(entries)}")
    entry = entries[0]

    manifest = json.loads(PLUGIN.read_text("utf-8"))
    if manifest.get("id") != "qoder.sites":
        raise SystemExit("staged plugin.json is not qoder.sites")

    hashes = {}
    for rel, name in TARGETS.items():
        hashes[name] = sha256(ROOT / "work" / "sites_stage" / "dist" / "browser" / name) if name != "plugin.json" else sha256(PLUGIN)

    files = entry.get("files")
    if not isinstance(files, list):
        raise SystemExit("qoder.sites entry has no files list")
    seen = set()
    for record in files:
        path = record.get("path")
        if path in TARGETS:
            record["sha256"] = hashes[TARGETS[path]]
            seen.add(path)
    missing = set(TARGETS) - seen
    if missing:
        raise SystemExit(f"catalog is missing records: {sorted(missing)}")

    entry["manifest"] = manifest
    STAGE.parent.mkdir(parents=True, exist_ok=True)
    STAGE.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", "utf-8")

    check = json.loads(STAGE.read_text("utf-8"))
    ce = [p for p in check["plugins"] if p.get("id") == "qoder.sites"][0]
    assert ce["manifest"]["contributes"]["views"][0]["title"]["translations"]["zh-TW"] == "站點"
    for record in ce["files"]:
        if record["path"] in TARGETS:
            assert record["sha256"] == hashes[TARGETS[record["path"]]], record["path"]

    print(f"catalog original: {sha256(CATALOG)}")
    print(f"catalog staged:   {sha256(STAGE)}")
    for name, digest in hashes.items():
        print(f"{name}: {digest}")
    print(f"plugins: {len(plugins)}, qoder.sites files: {len(files)}")


if __name__ == "__main__":
    main()
