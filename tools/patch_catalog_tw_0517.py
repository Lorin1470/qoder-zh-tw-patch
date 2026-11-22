# -*- coding: utf-8 -*-
"""Update the packaged extension catalog for the zh-TW Sites patch (0.5.17).

Reads the installed Qoder CN catalog.v1.json (override the resources dir with
QODER_RESOURCES) and stages the updated copy in
work/0517-sites-stage/catalog.v1.json. Run BEFORE replacing app files.
"""

import hashlib
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STAGE = ROOT / "work" / "0517-sites-stage"

TARGETS = {
    ".qoder-app-plugin/plugin.json",
    "dist/browser/publishPreview.cjs",
    "dist/browser/view.cjs",
}


def resources_dir() -> Path:
    env = os.environ.get("QODER_RESOURCES")
    if env:
        return Path(env)
    if sys.platform == "darwin":
        return Path("/Applications/Qoder CN.app/Contents/Resources")
    raise SystemExit("unsupported platform; set QODER_RESOURCES")


def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    catalog_path = resources_dir() / "extensions/catalog.v1.json"
    data = json.loads(catalog_path.read_text("utf-8"))
    plugins = data.get("plugins")
    if not isinstance(plugins, list):
        raise SystemExit("catalog has no plugins list")
    entries = [p for p in plugins if p.get("id") == "qoder.sites"]
    if len(entries) != 1:
        raise SystemExit(f"expected one qoder.sites entry, found {len(entries)}")
    entry = entries[0]

    manifest = json.loads((STAGE / ".qoder-app-plugin/plugin.json").read_text("utf-8"))
    if manifest.get("id") != "qoder.sites":
        raise SystemExit("staged plugin.json is not qoder.sites")

    hashes = {rel: sha256(STAGE / rel) for rel in TARGETS}

    files = entry.get("files")
    if not isinstance(files, list):
        raise SystemExit("qoder.sites entry has no files list")
    seen = set()
    for record in files:
        path = record.get("path")
        if path in TARGETS:
            record["sha256"] = hashes[path]
            seen.add(path)
    missing = TARGETS - seen
    if missing:
        raise SystemExit(f"catalog is missing records: {sorted(missing)}")

    entry["manifest"] = manifest
    out = STAGE / "catalog.v1.json"
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", "utf-8")

    check = json.loads(out.read_text("utf-8"))
    ce = [p for p in check["plugins"] if p.get("id") == "qoder.sites"][0]
    titles = [
        v["title"]["translations"]["zh-TW"]
        for v in ce["manifest"]["contributes"]["views"]
    ]
    if titles != ["網站", "網站"]:
        raise SystemExit(f"unexpected zh-TW view titles: {titles}")
    print(f"catalog original: {sha256(catalog_path)}")
    print(f"catalog staged:   {sha256(out)}")
    for rel, digest in hashes.items():
        print(f"{rel}: {digest}")


if __name__ == "__main__":
    main()