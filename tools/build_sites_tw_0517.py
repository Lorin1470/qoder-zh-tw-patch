# -*- coding: utf-8 -*-
"""Build the Sites extension zh-TW dictionaries for Qoder 0.5.17.

Input: work/0517-dict/sites_raw.json (zh-CN view + annotation maps, extracted
from the packaged extension by tools/jsparse/extract_sites_dict.js).
Output: sites_tw.json / sites_tw_annot.json in the same folder.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from tw import Converter  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DICT = ROOT / "work" / "0517-dict"

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

POST_RULES = [
    ("發布", "發佈"),
    ("工作台", "工作區"),
]


def convert(conv, value):
    if not isinstance(value, str):
        return value
    out = conv.convert(value)
    for old, new in POST_RULES:
        out = out.replace(old, new)
    return out


def main():
    raw = json.loads((DICT / "sites_raw.json").read_text("utf-8"))
    conv = Converter()
    for name, src_name in (("sites_tw.json", "view"), ("sites_tw_annot.json", "annot")):
        out = {k: convert(conv, v) for k, v in raw[src_name].items()}
        (DICT / name).write_text(
            json.dumps(out, ensure_ascii=False, indent=2) + "\n", "utf-8"
        )
        print(f"wrote {name} ({len(out)} keys)")
    (DICT / "sites_status_tw.json").write_text(
        json.dumps(TW_STATUS, ensure_ascii=False, indent=2) + "\n", "utf-8"
    )
    print(f"wrote sites_status_tw.json ({len(TW_STATUS)} keys)")


if __name__ == "__main__":
    main()