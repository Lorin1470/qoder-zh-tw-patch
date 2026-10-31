# -*- coding: utf-8 -*-
"""Repack app.asar, replacing selected files and refreshing ASAR integrity."""

import argparse
import hashlib
import json
import struct
from pathlib import Path

BLOCK = 4194304


def parse_header(path):
    with open(path, "rb") as f:
        magic, pickle_size, _, json_len = struct.unpack("<4I", f.read(16))
        if magic != 4:
            raise SystemExit(f"unexpected asar magic {magic}")
        raw = f.read(json_len)
    return json.loads(raw), pickle_size, json_len


def walk(node, prefix=""):
    for name, child in node.get("files", {}).items():
        path = f"{prefix}/{name}"
        if "files" in child:
            yield from walk(child, path)
        else:
            yield path, child


def integrity(data):
    digest = hashlib.sha256(data).hexdigest()
    blocks = [
        hashlib.sha256(data[i:i + BLOCK]).hexdigest()
        for i in range(0, len(data), BLOCK)
    ]
    return {
        "algorithm": "SHA256",
        "hash": digest,
        "blockSize": BLOCK,
        "blocks": blocks,
    }


def build_header(json_bytes):
    size = 8 + len(json_bytes)
    pad = (-size) % 4
    pickle_size = size + pad
    prefix = struct.pack("<4I", 4, pickle_size, pickle_size - 4, len(json_bytes))
    header = prefix + json_bytes + b"\0" * pad
    assert len(header) == 8 + pickle_size
    return header


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True)
    ap.add_argument("--root", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--replace", nargs="*", default=[])
    args = ap.parse_args()

    src = Path(args.src)
    root = Path(args.root)
    out = Path(args.out)
    replace = {p.strip("/"): (root / p.strip("/")).read_bytes() for p in args.replace}

    header, _, _ = parse_header(src)
    entries = list(walk(header))
    missing = set(replace) - {p.lstrip("/") for p, _ in entries}
    if missing:
        raise SystemExit(f"not in asar: {sorted(missing)}")

    cursor = 0
    old_offsets = {}
    for path, node in entries:
        rel = path.lstrip("/")
        if rel in replace:
            data = replace[rel]
            node["size"] = len(data)
            node["integrity"] = integrity(data)
        if "offset" in node:
            old_offsets[rel] = int(node["offset"])
            node["offset"] = str(cursor)
            cursor += node["size"]

    raw = json.dumps(header, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    header_bytes = build_header(raw)
    header_hash = hashlib.sha256(raw).hexdigest()

    with open(src, "rb") as f:
        f.seek(4)
        data_start_old = 8 + struct.unpack("<I", f.read(4))[0]
    with open(src, "rb") as fsrc, open(out, "wb") as fout:
        fout.write(header_bytes)
        for path, node in entries:
            if "offset" not in node:
                continue
            rel = path.lstrip("/")
            if rel in replace:
                data = replace[rel]
            else:
                fsrc.seek(data_start_old + old_offsets[rel])
                data = fsrc.read(node["size"])
                if len(data) != node["size"]:
                    raise SystemExit(f"short read for {rel}")
            fout.write(data)

    print(json.dumps({
        "out": str(out),
        "header_hash": header_hash,
        "data_bytes": cursor,
        "replaced": sorted(replace),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
