# -*- coding: utf-8 -*-
"""Build zh-TW dictionaries for Qoder 0.5.13.

Same pipeline as 0.5.12 (zh-HK base + Taiwan-term Converter + OVERRIDES),
reading freshly extracted 0.5.13 sources from work/0513-dict.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_zh_tw_0512 as base  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
base.DICT = ROOT / "work" / "0513-dict"

if __name__ == "__main__":
    base.build()