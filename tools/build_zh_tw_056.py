# -*- coding: utf-8 -*-
"""Build zh-TW dictionaries for Qoder 0.5.6.

Base text: native zh-HK (human Traditional) where available, otherwise the
zh source; both pass through the Taiwan-term Converter. Curated OVERRIDES
from tw.py are applied last by dotted key path.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from opencc import OpenCC  # noqa: E402

from tw import Converter, OVERRIDES  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DICT = ROOT / "work" / "056-dict"

S2T = OpenCC("s2t")


def flat(o, p=""):
    for k, v in o.items():
        kp = f"{p}.{k}" if p else k
        if isinstance(v, dict):
            yield from flat(v, kp)
        else:
            yield kp, v


def set_path(o, path, value):
    parts = path.split(".")
    cur = o
    for part in parts[:-1]:
        if part not in cur or not isinstance(cur[part], dict):
            return False
        cur = cur[part]
    if parts[-1] not in cur:
        return False
    cur[parts[-1]] = value
    return True


def build():
    zh = json.loads((DICT / "new_zh.json").read_text("utf-8"))
    hk = json.loads((DICT / "new_zhHK.json").read_text("utf-8"))
    hk_flat = dict(flat(hk))
    conv = Converter()

    from_hk = 0
    from_zh = 0

    def pick(path, value):
        nonlocal from_hk, from_zh
        if path in hk_flat and isinstance(hk_flat[path], str):
            from_hk += 1
            return conv.convert(hk_flat[path])
        from_zh += 1
        return conv.convert(value) if isinstance(value, str) else value

    def walk(o, p=""):
        out = {}
        for k, v in o.items():
            kp = f"{p}.{k}" if p else k
            out[k] = walk(v, kp) if isinstance(v, dict) else pick(kp, v)
        return out

    tw = walk(zh)

    applied, skipped = [], []
    for key, value in OVERRIDES.items():
        (applied if set_path(tw, key, value) else skipped).append(key)

    (DICT / "tw_base.json").write_text(
        json.dumps(tw, ensure_ascii=False, separators=(",", ":")), "utf-8"
    )

    for name in ("mf2", "fT2"):
        src = json.loads((DICT / f"{name}_zh.json").read_text("utf-8"))
        c2 = Converter()

        def conv_tree(o):
            if isinstance(o, dict):
                return {k: conv_tree(v) for k, v in o.items()}
            if isinstance(o, list):
                return [conv_tree(v) for v in o]
            if isinstance(o, str):
                return c2.convert(o)
            return o

        (DICT / f"{name}_tw.json").write_text(
            json.dumps(conv_tree(src), ensure_ascii=False, separators=(",", ":")),
            "utf-8",
        )

    leaves = dict(flat(tw))
    leftover = {
        k: v for k, v in leaves.items()
        if isinstance(v, str) and S2T.convert(v) != v
    }
    report = {
        "total_keys": len(leaves),
        "from_zhHK": from_hk,
        "from_zh": from_zh,
        "overrides_applied": len(applied),
        "overrides_skipped": skipped,
        "simplified_leftover_count": len(leftover),
        "simplified_leftover_sample": dict(list(leftover.items())[:20]),
    }
    (DICT / "build_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), "utf-8"
    )
    print(json.dumps({k: v for k, v in report.items() if k != "simplified_leftover_sample"}, ensure_ascii=False, indent=2))
    for k, v in list(leftover.items())[:10]:
        print("LEFTOVER", k, "=", v[:80])


if __name__ == "__main__":
    build()