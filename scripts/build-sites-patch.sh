#!/bin/bash
# Build the Sites zh-TW staging files and the matching extension catalog.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

[ -f data/sites_tw.json ] || { echo "缺少 data/sites_tw.json" >&2; exit 1; }
[ -f data/sites_tw_annot.json ] || { echo "缺少 data/sites_tw_annot.json" >&2; exit 1; }

python3 tools/patch_sites_tw.py
python3 tools/patch_catalog_tw.py

echo
echo "已產生 work/sites_stage："
echo "  dist/browser/view.cjs"
echo "  dist/browser/publishPreview.cjs"
echo "  .qoder-app-plugin/plugin.json"
echo "  catalog.v1.json"
echo
echo "下一步：套用到 /Applications/Qoder.app 並重新簽章，"
echo "或參考 scripts/qoder-0.4.11/sites_*_apply.sh。"
