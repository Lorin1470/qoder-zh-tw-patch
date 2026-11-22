# -*- coding: utf-8 -*-
"""Build a patched Qoder CN 0.5.17 app bundle in the patch staging folder.

Copies the installed app with ditto, repacks app.asar with the generated
0.5.17 patches, swaps in the Sites extension files + catalog, refreshes the
ElectronAsarIntegrity hash, and ad-hoc signs the result. The installed app is
never touched; scripts/qoder-0.5.17-macos/install.sh performs the swap.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STAGE = ROOT / "work" / "0517-stage"
SITES = ROOT / "work" / "0517-sites-stage"

REPLACE = [
    "out/renderer/assets/D7G81Cst.js",
    "out/renderer/assets/UnNhyzqB.js",
    "out/renderer/assets/DMzt2vcU.js",
    "out/renderer/assets/ClMoALKS.js",
    "out/renderer/assets/B7xIIv6H.js",
    "out/renderer/assets/KSrj1L-v.js",
    "out/renderer/assets/CFNPMAwa.js",
    "out/renderer/assets/Bp5ml99Y.js",
    "out/renderer/assets/Cx4X391Y.js",
    "out/renderer/assets/D1eLu6vA.js",
    "out/renderer/assets/A_9LZ4mC.js",
    "out/renderer/assets/BHmloleD.js",
    "out/renderer/assets/B01Tds90.js",
    "out/renderer/index.html",
    "out/main/electronMain.js",
    "out/main/chunks/C1jqE3Um.js",
]

SITES_FILES = [
    "dist/browser/view.cjs",
    "dist/browser/publishPreview.cjs",
    ".qoder-app-plugin/plugin.json",
]


def run(cmd, **kw):
    r = subprocess.run(cmd, capture_output=True, text=True, **kw)
    if r.returncode != 0:
        raise SystemExit(f"command failed: {' '.join(cmd)}\n{r.stdout}\n{r.stderr}")
    return r


def plist_get(plist, key):
    r = subprocess.run(
        ["/usr/libexec/PlistBuddy", "-c", f"Print :{key}", str(plist)],
        capture_output=True, text=True,
    )
    if r.returncode != 0:
        raise SystemExit(f"plist read failed for {key}")
    return r.stdout.strip()


def sha256(path):
    import hashlib

    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--app", default="/Applications/Qoder CN.app")
    ap.add_argument(
        "--dest",
        default=os.path.expanduser(
            "~/Library/Application Support/QoderPatch/Qoder CN.app"
        ),
    )
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    app = Path(args.app)
    dest = Path(args.dest)
    if not app.is_dir():
        raise SystemExit(f"app not found: {app}")
    version = plist_get(app / "Contents/Info.plist", "CFBundleShortVersionString")
    if version != "0.5.17":
        raise SystemExit(f"expected Qoder 0.5.17, found {version}")
    if dest.exists():
        if not args.force:
            raise SystemExit(f"staging folder already exists: {dest}")
        shutil.rmtree(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)

    print(f"copying {app} -> {dest}")
    run(["ditto", str(app), str(dest)])

    asar = dest / "Contents/Resources/app.asar"
    with tempfile.NamedTemporaryFile(suffix=".asar", delete=False) as f:
        tmp_asar = Path(f.name)
    try:
        r = run(
            [sys.executable, str(ROOT / "tools/repack_asar.py"),
             "--src", str(asar),
             "--root", str(STAGE / "out"),
             "--out", str(tmp_asar),
             "--replace", *REPLACE]
        )
        info = json.loads(r.stdout)
        tmp_asar.replace(asar)
    finally:
        if tmp_asar.exists():
            tmp_asar.unlink()

    plist = dest / "Contents/Info.plist"
    run(["/usr/libexec/PlistBuddy", "-c",
         f"Set :ElectronAsarIntegrity:Resources/app.asar:hash {info['header_hash']}",
         str(plist)])

    ext = dest / "Contents/Resources/extensions"
    for rel in SITES_FILES:
        shutil.copyfile(SITES / rel, ext / "qoder.sites" / rel)
    shutil.copyfile(SITES / "catalog.v1.json", ext / "catalog.v1.json")

    for junk in ("Contents/CodeResources", "Contents/_CodeSignature"):
        p = dest / junk
        if p.is_dir():
            shutil.rmtree(p)
        elif p.exists():
            p.unlink()

    run(["codesign", "--force", "--deep", "--sign", "-", str(dest)])
    run(["codesign", "--verify", "--deep", "--strict", str(dest)])
    run(["/usr/bin/xattr", "-dr", "com.apple.quarantine", str(dest)])

    result = {
        "app": str(dest),
        "version": plist_get(plist, "CFBundleShortVersionString"),
        "asar_size": asar.stat().st_size,
        "asar_sha256": sha256(asar),
        "header_hash": plist_get(plist, "ElectronAsarIntegrity:Resources/app.asar:hash"),
        "catalog_sha256": sha256(ext / "catalog.v1.json"),
        "header_from_repack": info["header_hash"],
    }
    if result["header_hash"] != result["header_from_repack"]:
        raise SystemExit("Info.plist integrity hash mismatch after write")
    (dest.parent / "staged-0517.json").write_text(
        json.dumps(result, indent=2) + "\n", "utf-8"
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()