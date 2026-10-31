#!/bin/bash
# Extract the installed Qoder app.asar into work/original for local patch generation.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
APP="${1:-/Applications/Qoder.app}"
OUT="${2:-$ROOT/work/original}"

if [ ! -f "$APP/Contents/Resources/app.asar" ]; then
  echo "找不到 app.asar：$APP/Contents/Resources/app.asar" >&2
  exit 1
fi
if ! command -v npx >/dev/null 2>&1; then
  echo "需要 Node.js 的 npx 才能解出 app.asar。" >&2
  exit 1
fi

mkdir -p "$OUT"
npx --yes @electron/asar extract "$APP/Contents/Resources/app.asar" "$OUT"
echo "已解出到：$OUT"
