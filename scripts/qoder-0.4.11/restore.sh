#!/bin/bash
# 將 Qoder 還原成原始版本的程式。
# 用法：restore.sh

set -u
umask 022
export PATH="/usr/bin:/bin:/usr/sbin:/sbin"
unset ELECTRON_RUN_AS_NODE 2>/dev/null || true

PATCH_DIR="$HOME/Library/Application Support/QoderPatch"
STAGED_APP="$PATCH_DIR/Qoder.app"
APP="/Applications/Qoder.app"
BACKUP="/Applications/Qoder.app.original-0.4.11"
PLIST="$HOME/Library/LaunchAgents/com.qoder.twpatch.plist"
LOG="$PATCH_DIR/install.log"
LOCK_DIR="$PATCH_DIR/install.lock.d"
MAIN_EXE="$APP/Contents/MacOS/Qoder"
LSREGISTER="/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister"

EXPECTED_VERSION="0.4.11"
PATCHED_ASAR_FILE="e87d266a3f2518df89116117d0e31a5803cde957ade9bfc0524364fe7eaa2e2c"
ORIGINAL_ASAR_FILE="0d50e5a4c05a0510345933b08081a4767bfbf95633c314f6738d4652a213acfc"
ORIGINAL_HEADER="97845e339dea91d6a278e257a5f8255735c4a988ddeee3cc6cae749e49478ddc"

mkdir -p "$PATCH_DIR" 2>/dev/null || true

say() {
  printf '%s\n' "$*"
}

log() {
  printf '%s %s\n' "$(/bin/date '+%Y-%m-%d %H:%M:%S')" "$*" >>"$LOG" 2>/dev/null
  say "$*"
}

plist_value() {
  /usr/libexec/PlistBuddy -c "Print :$2" "$1/Contents/Info.plist" 2>/dev/null
}

asar_hash() {
  /usr/bin/shasum -a 256 "$1/Contents/Resources/app.asar" 2>/dev/null | /usr/bin/awk '{print $1}'
}

header_hash() {
  plist_value "$1" "ElectronAsarIntegrity:Resources/app.asar:hash"
}

app_version() {
  plist_value "$1" CFBundleShortVersionString
}

qoder_main_pids() {
  /bin/ps -axo pid=,command= | /usr/bin/awk -v exe="$MAIN_EXE" '
    {
      pid = $1
      line = $0
      sub(/^[ \t]+/, "", line)
      sub(/^[0-9]+[ \t]+/, "", line)
      if (index(line, exe) != 1) next
      if (line ~ /(^|[ \t])--(type|sdk|eval)(=|[ \t]|$)/) next
      if (line ~ /--utility-sub-type/) next
      if (line ~ /\.(mjs|cjs)([ \t]|$)/) next
      print pid
    }'
}

qoder_is_running() {
  [ -n "$(qoder_main_pids)" ]
}

acquire_lock() {
  local other
  if /bin/mkdir "$LOCK_DIR" 2>/dev/null; then
    printf '%s\n' "$$" >"$LOCK_DIR/pid" 2>/dev/null || true
    return 0
  fi
  other="$(/bin/cat "$LOCK_DIR/pid" 2>/dev/null || true)"
  if [ -n "$other" ] && /bin/kill -0 "$other" 2>/dev/null; then
    return 1
  fi
  /bin/rm -rf "$LOCK_DIR" 2>/dev/null || true
  if /bin/mkdir "$LOCK_DIR" 2>/dev/null; then
    printf '%s\n' "$$" >"$LOCK_DIR/pid" 2>/dev/null || true
    return 0
  fi
  return 1
}

release_lock() {
  /bin/rm -rf "$LOCK_DIR" 2>/dev/null || true
}

verify_original() {
  local app="$1" label="$2" actual_version actual_asar actual_header
  actual_version="$(app_version "$app")"
  actual_asar="$(asar_hash "$app")"
  actual_header="$(header_hash "$app")"
  if [ "$actual_version" != "$EXPECTED_VERSION" ]; then
    log "$label 版本不符：$actual_version（預期 $EXPECTED_VERSION）"
    return 1
  fi
  if [ "$actual_asar" != "$ORIGINAL_ASAR_FILE" ]; then
    log "$label 的 app.asar 雜湊不符。"
    return 1
  fi
  if [ "$actual_header" != "$ORIGINAL_HEADER" ]; then
    log "$label 的 Info.plist 完整性雜湊不符。"
    return 1
  fi
  if ! /usr/bin/codesign --verify --deep --strict "$app" >/dev/null 2>&1; then
    log "$label 的簽章驗證失敗。"
    return 1
  fi
  return 0
}

launch_and_wait() {
  local rc i pids
  log "正在啟動 Qoder 進行測試。"
  /usr/bin/open -n "$APP" >>"$LOG" 2>&1
  rc=$?
  if [ "$rc" -ne 0 ]; then
    log "open 指令失敗（代碼 $rc）。"
    return 1
  fi
  i=0
  while [ "$i" -lt 25 ]; do
    /bin/sleep 1
    if qoder_is_running; then
      break
    fi
    i=$((i + 1))
  done
  if ! qoder_is_running; then
    log "等了 25 秒仍未偵測到 Qoder 主程式。"
    return 1
  fi
  pids="$(printf '%s ' $(qoder_main_pids))"
  log "Qoder 主程式已出現（PID: $pids），觀察 8 秒確認沒有立即結束。"
  for i in 1 2 3 4; do
    /bin/sleep 2
    if ! qoder_is_running; then
      log "Qoder 啟動後又結束了。"
      return 1
    fi
  done
  return 0
}

restore() {
  local installed_asar previous_app
  /bin/launchctl bootout "gui/$(id -u)/com.qoder.twpatch" >/dev/null 2>&1 || true
  /bin/rm -f "$PLIST" 2>/dev/null || true

  if qoder_is_running; then
    log "Qoder 正在執行。請先完全結束 Qoder（⌘Q），再執行一次。"
    return 4
  fi

  if [ ! -d "$APP" ]; then
    log "找不到目前的 Qoder：$APP"
    return 2
  fi

  installed_asar="$(asar_hash "$APP")"

  if [ "$installed_asar" = "$ORIGINAL_ASAR_FILE" ]; then
    log "目前的 Qoder 已經是原始版本，不需要還原。"
    if [ -d "$BACKUP" ]; then
      log "原始版備份仍在：$BACKUP"
    fi
    return 0
  fi

  if [ "$installed_asar" != "$PATCHED_ASAR_FILE" ]; then
    log "目前 Qoder 的內容不是已知的繁中補丁，為避免損毀資料，取消還原。"
    return 2
  fi

  if [ ! -d "$BACKUP" ]; then
    log "找不到原始版備份：$BACKUP"
    log "請重新安裝官方 Qoder $EXPECTED_VERSION，或從 Time Machine 還原。"
    return 2
  fi

  if ! verify_original "$BACKUP" "原始版備份"; then
    log "原始版備份驗證失敗，為避免覆蓋目前 App，取消還原。"
    return 3
  fi

  if [ -e "$STAGED_APP" ]; then
    previous_app="$PATCH_DIR/Qoder.app.previous-$(/bin/date +%Y%m%d-%H%M%S)"
    log "暫存位置已有其他 App，先移到：$previous_app"
    if ! /bin/mv "$STAGED_APP" "$previous_app"; then
      log "無法清空暫存位置，取消還原。"
      return 5
    fi
  fi

  log "正在把繁中版移到暫存位置：$STAGED_APP"
  if ! /bin/mv "$APP" "$STAGED_APP"; then
    log "無法移開繁中版 App，取消還原。"
    return 5
  fi

  log "正在放回原始版 App。"
  if ! /bin/mv "$BACKUP" "$APP"; then
    log "無法放回原始版 App；正在把繁中版放回原位。"
    /bin/mv "$STAGED_APP" "$APP" 2>/dev/null || true
    return 6
  fi

  if ! verify_original "$APP" "還原後的 App"; then
    log "還原後驗證失敗；繁中版仍保留在 $STAGED_APP。"
    return 7
  fi

  "$LSREGISTER" -f "$APP" >/dev/null 2>&1 || true

  if launch_and_wait; then
    log "已還原成原始 Qoder，並重新啟動。繁中版保留在 $STAGED_APP，可再次套用。"
    return 0
  fi

  log "原始 Qoder 已放回 /Applications/Qoder.app，但自動啟動測試未通過；請手動開啟。"
  return 8
}

if ! acquire_lock; then
  log "安裝程序正在執行，請稍後再還原。"
  exit 9
fi
restore
rc=$?
release_lock
exit "$rc"
