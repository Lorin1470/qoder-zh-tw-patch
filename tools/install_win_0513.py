# -*- coding: utf-8 -*-
"""Apply / restore the Qoder 0.5.13 zh-TW patch on Windows.

Usage (Qoder must be fully closed for apply/restore):
    python tools/install_win_0513.py apply
    python tools/install_win_0513.py restore
    python tools/install_win_0513.py wait   # wait for Qoder to close, apply, relaunch

apply:
  1. verifies productVersion 0.5.13 and that Qoder.exe is not running
  2. backs up app.asar, Qoder.exe, catalog.v1.json and the three Sites files
     to %LOCALAPPDATA%/QoderPatch/backup-0.5.13 (refuses to overwrite a backup)
  3. repacks app.asar from work/0513-stage/out via tools/repack_asar.py
  4. replaces the asar header hash embedded in Qoder.exe resources
     (same-length hex swap; Electron's EnableEmbeddedAsarIntegrityValidation
     fuse is on, so the exe must carry the new header hash)
  5. swaps in the staged Sites files and catalog.v1.json

restore: copies the backup files back.

No codesign step is needed on Windows; the exe's Authenticode signature is
invalidated by the hash swap but Windows does not enforce it for launch.
"""

import argparse
import hashlib
import json
import os
import shutil
import struct
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RES = Path(os.environ.get("QODER_RESOURCES") or
           Path(os.environ["LOCALAPPDATA"]) / "Programs/Qoder/resources")
EXE = RES.parent / "Qoder.exe"
BACKUP = Path(os.environ["LOCALAPPDATA"]) / "QoderPatch" / "backup-0.5.13"
STAGE = ROOT / "work" / "0513-stage"
SITES_STAGE = ROOT / "work" / "0513-sites-stage"

REPLACE = [
    "out/main/electronMain.js",
    "out/renderer/index.html",
    "out/renderer/assets/C4HI_h4X.js",
    "out/renderer/assets/DB5RheoM.js",
    "out/renderer/assets/Cc0Q_zSB.js",
    "out/renderer/assets/D1eLu6vA.js",
    "out/renderer/assets/sJNnZRwO.js",
    "out/renderer/assets/BHeyMntc.js",
    "out/renderer/assets/B5ZSHQum.js",
    "out/renderer/assets/E8xm_B5G.js",
    "out/renderer/assets/DsRCeT1Q.js",
    "out/renderer/assets/Du7Q5KIm.js",
    "out/renderer/assets/JtrNHQW2.js",
]

BACKUP_FILES = {
    "app.asar": RES / "app.asar",
    "Qoder.exe": EXE,
    "catalog.v1.json": RES / "extensions/catalog.v1.json",
    "view.cjs": RES / "extensions/qoder.sites/dist/browser/view.cjs",
    "publishPreview.cjs": RES / "extensions/qoder.sites/dist/browser/publishPreview.cjs",
    "plugin.json": RES / "extensions/qoder.sites/.qoder-app-plugin/plugin.json",
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def asar_header_hash(path: Path) -> str:
    with path.open("rb") as f:
        magic, _, _, jl = struct.unpack("<4I", f.read(16))
        if magic != 4:
            raise SystemExit(f"not an asar: {path}")
        return hashlib.sha256(f.read(jl)).hexdigest()


def qoder_running() -> bool:
    r = subprocess.run(
        ["tasklist", "/FI", "IMAGENAME eq Qoder.exe", "/NH"],
        capture_output=True, text=True,
    )
    return "Qoder.exe" in r.stdout


def check_version():
    manifest = json.loads((RES / "build-manifest.json").read_text("utf-8"))
    v = manifest.get("productVersion")
    if v != "0.5.13":
        raise SystemExit(f"expected Qoder 0.5.13, found {v}")


def apply():
    check_version()
    if qoder_running():
        raise SystemExit("Qoder is running; close it completely first")
    if BACKUP.exists():
        raise SystemExit(f"backup already exists: {BACKUP}; restore or remove it first")
    if not (STAGE / "out").is_dir():
        raise SystemExit("run tools/patch_app_files_0513.py first")
    if not (SITES_STAGE / "catalog.v1.json").is_file():
        raise SystemExit("run patch_sites_tw_0513.py and patch_catalog_tw_0513.py first")

    orig_hashes = {name: sha256(p) for name, p in BACKUP_FILES.items()}
    old_header = asar_header_hash(RES / "app.asar")

    BACKUP.mkdir(parents=True)
    for name, p in BACKUP_FILES.items():
        shutil.copy2(p, BACKUP / name)
    (BACKUP / "original-hashes.json").write_text(
        json.dumps({"sha256": orig_hashes, "asar_header_hash": old_header}, indent=2),
        "utf-8",
    )
    print(f"backed up {len(BACKUP_FILES)} files to {BACKUP}")

    r = subprocess.run(
        [sys.executable, str(ROOT / "tools/repack_asar.py"),
         "--src", str(RES / "app.asar"),
         "--root", str(STAGE / "out"),
         "--out", str(STAGE / "app.asar"),
         "--replace", *REPLACE],
        capture_output=True, text=True,
    )
    if r.returncode != 0:
        raise SystemExit("repack failed:\n" + r.stdout + r.stderr)
    info = json.loads(r.stdout)
    new_header = info["header_hash"]
    print(f"repacked: header_hash={new_header}")

    exe = EXE.read_bytes()
    if exe.count(old_header.encode()) != 1:
        raise SystemExit("original asar header hash not found exactly once in Qoder.exe")
    exe = exe.replace(old_header.encode(), new_header.encode())
    EXE.write_bytes(exe)
    print("Qoder.exe integrity hash updated")

    shutil.copy2(STAGE / "app.asar", RES / "app.asar")
    for rel, dest in (
        ("dist/browser/view.cjs", BACKUP_FILES["view.cjs"]),
        ("dist/browser/publishPreview.cjs", BACKUP_FILES["publishPreview.cjs"]),
        (".qoder-app-plugin/plugin.json", BACKUP_FILES["plugin.json"]),
        ("catalog.v1.json", BACKUP_FILES["catalog.v1.json"]),
    ):
        shutil.copy2(SITES_STAGE / rel, dest)
    print("patch applied; start Qoder and pick 繁體中文 in 設定 → 外觀 → 語言")


def restore():
    if not BACKUP.is_dir():
        raise SystemExit(f"no backup at {BACKUP}")
    if qoder_running():
        raise SystemExit("Qoder is running; close it completely first")
    recorded = json.loads((BACKUP / "original-hashes.json").read_text("utf-8"))
    for name, p in BACKUP_FILES.items():
        b = BACKUP / name
        if sha256(b) != recorded["sha256"][name]:
            raise SystemExit(f"backup file corrupted: {name}")
        shutil.copy2(b, p)
    print("restored original files")


def wait_and_apply(timeout_s=1800):
    import time
    print("waiting for Qoder to close...", flush=True)
    deadline = time.time() + timeout_s
    while qoder_running():
        if time.time() > deadline:
            raise SystemExit("timed out waiting for Qoder to close")
        time.sleep(2)
    time.sleep(3)
    try:
        apply()
    except Exception as e:
        print(f"apply failed: {e}; restoring", flush=True)
        restore()
    subprocess.Popen([str(EXE)], cwd=str(EXE.parent),
                     creationflags=0x00000008 | 0x00000200)
    print("Qoder relaunched", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("action", choices=["apply", "restore", "wait"])
    args = ap.parse_args()
    if args.action == "apply":
        apply()
    elif args.action == "restore":
        restore()
    else:
        wait_and_apply()


if __name__ == "__main__":
    main()