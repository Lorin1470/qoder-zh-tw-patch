#!/bin/bash
# 套用 Qoder Sites 擴充套件的繁體中文（台灣用語）增量補丁。
# 用法：sites_tw_apply.sh [wait|now|check]

set -u
umask 022
export PATH="/usr/bin:/bin:/usr/sbin:/sbin"
unset ELECTRON_RUN_AS_NODE 2>/dev/null || true

PATCH_DIR="$HOME/Library/Application Support/QoderPatch"
STAGE="$PATCH_DIR/sites_stage"
APP="/Applications/Qoder.app"
SNAP="$PATCH_DIR/Qoder.app.pre-sites"
ENT="$PATCH_DIR/sites_entitlements.plist"
PLIST="$HOME/Library/LaunchAgents/com.qoder.twpatch.sites.plist"
LABEL="com.qoder.twpatch.sites"
LOG="$PATCH_DIR/sites.log"
LOCK_DIR="$PATCH_DIR/install.lock.d"
MAIN_EXE="$APP/Contents/MacOS/Qoder"
LSREGISTER="/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister"

EXPECTED_VERSION="0.4.11"
EXPECTED_ASAR="e87d266a3f2518df89116117d0e31a5803cde957ade9bfc0524364fe7eaa2e2c"
EXPECTED_HEADER="b30416f26287d6d665f5c2fc8b299ed235c97a2d2292b2c47fe0c2fe42b6c7d9"

ORIG_VIEW="d9bdf065433b9f1c2d689a1cfb20f358f3c0e327e9cb75175a104a9320c117f2"
ORIG_PREVIEW="168420b414e5baf7f729ae935ff4b3bd1d64127f2673483361d0f4bc387da47c"
ORIG_PLUGIN="d3ccf5fd6ed7c2e10ef35dbed8a300dfcab2d9f675a1cea792fc2e932f3cc204"

NEW_VIEW="8318870fdd5bc5ba48695b06a26aa02d90cc1b3ec6db25588adae2c584f7e242"
NEW_PREVIEW="75476358befd2fd99f17f5761f0729b1d64c652c8b8e541447b3130d6ad73397"
NEW_PLUGIN="bcc5a76dae039f7f6a8c88842ea0774c679015b00d387819417238e1b793e19e"

SITES_DIR="$APP/Contents/Resources/extensions/qoder.sites"
VIEW="$SITES_DIR/dist/browser/view.cjs"
PREVIEW="$SITES_DIR/dist/browser/publishPreview.cjs"
PLUGIN="$SITES_DIR/.qoder-app-plugin/plugin.json"

mkdir -p "$PATCH_DIR" 2>/dev/null || true

say() {
  printf '%s\n' "$*"
}

log() {
  printf '%s %s\n' "$(/bin/date '+%Y-%m-%d %H:%M:%S')" "$*" >>"$LOG" 2>/dev/null
  say "$*"
}

notify() {
  /usr/bin/osascript -e "display notification \"$1\" with title \"Qoder 繁體中文\"" >/dev/null 2>&1 || true
}

plist_value() {
  /usr/libexec/PlistBuddy -c "Print :$2" "$1/Contents/Info.plist" 2>/dev/null
}

app_version() {
  plist_value "$1" CFBundleShortVersionString
}

asar_hash() {
  /usr/bin/shasum -a 256 "$1/Contents/Resources/app.asar" 2>/dev/null | /usr/bin/awk '{print $1}'
}

header_hash() {
  plist_value "$1" "ElectronAsarIntegrity:Resources/app.asar:hash"
}

file_hash() {
  /usr/bin/shasum -a 256 "$1" 2>/dev/null | /usr/bin/awk '{print $1}'
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

kill_patched_main() {
  local pids i p
  pids="$(qoder_main_pids)"
  [ -z "$pids" ] && return 0
  log "正在結束測試啟動的 Qoder（PID: $(printf '%s ' $pids)）"
  for p in $pids; do
    /bin/kill -TERM "$p" 2>/dev/null || true
  done
  for i in 1 2 3 4 5 6 7 8 9 10; do
    /bin/sleep 1
    pids="$(qoder_main_pids)"
    [ -z "$pids" ] && return 0
  done
  for p in $pids; do
    /bin/kill -KILL "$p" 2>/dev/null || true
  done
  /bin/sleep 1
  return 0
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

cleanup_plist() {
  /bin/rm -f "$PLIST" 2>/dev/null || true
  (
    /bin/sleep 2
    /usr/bin/launchctl bootout "gui/$(/usr/bin/id -u)/$LABEL" >/dev/null 2>&1 || true
  ) >/dev/null 2>&1 &
}

verify_stage() {
  local h
  if [ ! -f "$STAGE/view.cjs" ] || [ ! -f "$STAGE/publishPreview.cjs" ] || [ ! -f "$STAGE/plugin.json" ]; then
    log "找不到待套用的 Sites 繁中檔案：$STAGE"
    return 1
  fi
  h="$(file_hash "$STAGE/view.cjs")"; [ "$h" = "$NEW_VIEW" ] || { log "view.cjs 校驗失敗。"; return 1; }
  h="$(file_hash "$STAGE/publishPreview.cjs")"; [ "$h" = "$NEW_PREVIEW" ] || { log "publishPreview.cjs 校驗失敗。"; return 1; }
  h="$(file_hash "$STAGE/plugin.json")"; [ "$h" = "$NEW_PLUGIN" ] || { log "plugin.json 校驗失敗。"; return 1; }
  /usr/bin/grep -q "__QODER_SITES_TW__" "$STAGE/view.cjs" || { log "view.cjs 缺少繁中標記。"; return 1; }
  /usr/bin/grep -q "__QODER_SITES_TW__" "$STAGE/publishPreview.cjs" || { log "publishPreview.cjs 缺少繁中標記。"; return 1; }
  /usr/bin/grep -q '"zh-TW": "站點"' "$STAGE/plugin.json" || { log "plugin.json 缺少 zh-TW 標題。"; return 1; }
  return 0
}

verify_base() {
  local v a h
  if [ ! -d "$APP" ]; then
    log "找不到 Qoder App：$APP"
    return 1
  fi
  v="$(app_version "$APP")"
  a="$(asar_hash "$APP")"
  h="$(header_hash "$APP")"
  if [ "$v" != "$EXPECTED_VERSION" ]; then
    log "目前 Qoder 版本是 ${v:-未知}，不是 $EXPECTED_VERSION；取消套用。"
    return 1
  fi
  if [ "$a" != "$EXPECTED_ASAR" ]; then
    log "目前 Qoder 的 app.asar 與已套用繁中補丁的 $EXPECTED_VERSION 不同；取消套用。"
    return 1
  fi
  if [ "$h" != "$EXPECTED_HEADER" ]; then
    log "目前 Qoder 的 Info.plist 完整性雜湊不符；取消套用。"
    return 1
  fi
  return 0
}

ext_state() {
  local v p j
  if [ ! -f "$VIEW" ] || [ ! -f "$PREVIEW" ] || [ ! -f "$PLUGIN" ]; then
    say "unknown"
    return
  fi
  v="$(file_hash "$VIEW")"
  p="$(file_hash "$PREVIEW")"
  j="$(file_hash "$PLUGIN")"
  if [ "$v" = "$ORIG_VIEW" ] && [ "$p" = "$ORIG_PREVIEW" ] && [ "$j" = "$ORIG_PLUGIN" ]; then
    say "original"
  elif [ "$v" = "$NEW_VIEW" ] && [ "$p" = "$NEW_PREVIEW" ] && [ "$j" = "$NEW_PLUGIN" ]; then
    say "patched"
  else
    say "unknown"
  fi
}

launch_and_wait() {
  local rc i pids
  if ! qoder_is_running; then
    log "正在重新啟動 Qoder。"
    /usr/bin/env -u ELECTRON_RUN_AS_NODE /usr/bin/open -n "$APP" >>"$LOG" 2>&1
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
  else
    log "Qoder 已在執行，不重複啟動。"
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

rollback() {
  local failed_app
  if [ ! -d "$SNAP" ]; then
    log "找不到套用前的快照，無法自動還原。"
    notify "Sites 繁中化失敗，且找不到備份；請查看 sites.log。"
    return 1
  fi
  failed_app="$PATCH_DIR/Qoder.app.failed-sites-$(/bin/date +%Y%m%d-%H%M%S)"
  kill_patched_main
  log "正在還原套用前的 Qoder。"
  if ! /bin/mv "$APP" "$failed_app"; then
    log "無法移開目前的 App；備份仍在 $SNAP，請手動處理。"
    notify "Sites 繁中化失敗，無法自動還原；請查看 sites.log。"
    return 1
  fi
  if ! /bin/mv "$SNAP" "$APP"; then
    log "無法放回備份（備份在 $SNAP）；受損 App 在 $failed_app。"
    /bin/mv "$failed_app" "$APP" 2>/dev/null || true
    notify "Sites 繁中化失敗，無法自動還原；請查看 sites.log。"
    return 1
  fi
  "$LSREGISTER" -f "$APP" >/dev/null 2>&1 || true
  if launch_and_wait; then
    log "已還原成套用前的 Qoder，並重新啟動。"
    notify "Sites 繁中化失敗，已還原原本的 Qoder。"
  else
    log "已放回備份，但自動啟動測試未通過；請手動開啟 Qoder。"
    notify "Sites 繁中化失敗，已還原但無法自動啟動；請手動開啟 Qoder。"
  fi
  return 0
}

apply_once_locked() {
  local state rc

  if ! verify_stage; then
    notify "Sites 繁中化取消：待套用檔案校驗失敗。"
    return 1
  fi
  if ! verify_base; then
    notify "Sites 繁中化取消：Qoder 版本或內容與預期不同。"
    return 2
  fi

  state="$(ext_state)"
  if [ "$state" = "patched" ]; then
    log "Sites 繁中化已經套用，不需要再次安裝。"
    cleanup_plist
    if ! qoder_is_running; then
      launch_and_wait || return 7
    fi
    return 0
  fi
  if [ "$state" != "original" ]; then
    log "Sites 擴充套件內容不是預期的原始版本，取消套用。"
    notify "Sites 繁中化取消：擴充套件內容與預期不同。"
    return 2
  fi

  if qoder_is_running; then
    log "Qoder 仍在執行，取消這次套用。"
    return 4
  fi

  if [ -e "$SNAP" ]; then
    log "備份位置已存在：$SNAP。為避免覆蓋既有備份，取消套用。"
    notify "Sites 繁中化取消：備份位置已存在。"
    return 3
  fi

  notify "正在套用 Sites 繁中化，請稍候約 20 秒，先不要開啟 Qoder。"

  if ! /usr/bin/codesign -d --entitlements :- "$APP" >"$ENT" 2>/dev/null; then
    log "無法讀取 Qoder 的 entitlements，取消套用。"
    notify "Sites 繁中化取消：無法讀取簽章資訊。"
    return 5
  fi
  if ! /usr/bin/grep -q "<key>com.apple.security.cs.allow-jit</key>" "$ENT" 2>/dev/null; then
    log "讀到的 entitlements 不完整，取消套用。"
    notify "Sites 繁中化取消：簽章資訊不完整。"
    return 5
  fi

  log "正在建立套用前快照：$SNAP"
  if ! /bin/cp -cR "$APP" "$SNAP" >>"$LOG" 2>&1; then
    log "APFS 快照失敗，改用完整複製。"
    /bin/rm -rf "$SNAP" 2>/dev/null || true
    if ! /usr/bin/ditto "$APP" "$SNAP" >>"$LOG" 2>&1; then
      log "無法建立套用前快照，取消套用。"
      /bin/rm -rf "$SNAP" 2>/dev/null || true
      notify "Sites 繁中化取消：無法建立備份。"
      return 5
    fi
  fi
  if [ ! -x "$SNAP/Contents/MacOS/Qoder" ] || ! /usr/bin/codesign --verify --strict "$SNAP" >>"$LOG" 2>&1; then
    log "套用前快照驗證失敗，取消套用。"
    /bin/rm -rf "$SNAP" 2>/dev/null || true
    notify "Sites 繁中化取消：備份驗證失敗。"
    return 5
  fi

  log "正在寫入 Sites 繁中檔案。"
  if ! /bin/cp -f "$STAGE/view.cjs" "$VIEW" || ! /bin/cp -f "$STAGE/publishPreview.cjs" "$PREVIEW" || ! /bin/cp -f "$STAGE/plugin.json" "$PLUGIN"; then
    log "複製檔案失敗，開始還原。"
    rollback
    return 6
  fi
  /bin/chmod 644 "$VIEW" "$PREVIEW" "$PLUGIN" 2>/dev/null || true
  /usr/bin/xattr -d com.apple.quarantine "$VIEW" "$PREVIEW" "$PLUGIN" >/dev/null 2>&1 || true

  if [ -e "$APP/Contents/CodeResources" ]; then
    log "移除舊的公證票據。"
    /bin/rm -f "$APP/Contents/CodeResources" 2>/dev/null || true
  fi

  log "正在重新簽署 Qoder（只簽外層）。"
  if ! /usr/bin/codesign --force --sign - --entitlements "$ENT" "$APP" >>"$LOG" 2>&1; then
    log "重新簽署失敗，開始還原。"
    rollback
    return 6
  fi

  log "正在驗證安裝結果。"
  if [ "$(ext_state)" != "patched" ] || ! /usr/bin/codesign --verify --deep --strict "$APP" >>"$LOG" 2>&1; then
    log "安裝後驗證失敗，開始還原。"
    rollback
    return 6
  fi
  if ! /usr/bin/codesign -d --entitlements :- "$APP" 2>/dev/null | /usr/bin/grep -q "com.apple.security.cs.allow-jit"; then
    log "重新簽署後 entitlements 不完整，開始還原。"
    rollback
    return 6
  fi

  "$LSREGISTER" -f "$APP" >/dev/null 2>&1 || true

  if launch_and_wait; then
    log "Sites 繁中化套用成功，Qoder 已重新啟動。"
    notify "Sites 繁中化完成，Qoder 已重新開啟。"
    cleanup_plist
    return 0
  fi

  log "套用後的 Qoder 無法正常啟動，開始還原。"
  rollback
  return 7
}

apply_once() {
  local rc
  if ! acquire_lock; then
    log "另一個安裝程序正在執行，這次先不套用。"
    return 9
  fi
  apply_once_locked
  rc=$?
  release_lock
  return "$rc"
}

wait_mode() {
  local quiet rc seen started
  if ! verify_stage; then
    notify "Sites 繁中化取消：待套用檔案不完整。"
    cleanup_plist
    exit 1
  fi
  log "Sites 繁中化安裝器已待命，等待 Qoder 完全結束後自動套用。"
  quiet=0
  seen=0
  started="$(/bin/date +%s)"
  while :; do
    if qoder_is_running; then
      if [ "$seen" -eq 0 ]; then
        log "偵測到 Qoder 正在執行；完全結束 Qoder 後就會套用。"
        seen=1
      fi
      quiet=0
    else
      if [ "$seen" -eq 0 ] && [ $(( $(/bin/date +%s) - started )) -lt 5 ]; then
        /bin/sleep 1
        continue
      fi
      quiet=$((quiet + 1))
      if [ "$quiet" -ge 2 ]; then
        log "Qoder 已結束，開始套用 Sites 繁中化。"
        apply_once
        rc=$?
        case "$rc" in
          0)
            exit 0
            ;;
          4|9)
            log "這次暫時無法套用（代碼 $rc），稍後再試。"
            quiet=0
            ;;
          *)
            log "套用結束（代碼 $rc）。"
            cleanup_plist
            exit "$rc"
            ;;
        esac
      fi
    fi
    /bin/sleep 1
  done
}

now_mode() {
  local rc
  if qoder_is_running; then
    log "Qoder 正在執行。請先完全結束 Qoder（⌘Q），再執行一次。"
    return 4
  fi
  apply_once
  rc=$?
  if [ "$rc" -eq 0 ]; then
    cleanup_plist
  fi
  return "$rc"
}

check_mode() {
  local v a h state
  say "Qoder Sites 繁體中文補丁狀態"
  say "----------------------------"
  say "待套用檔案：$STAGE"
  if verify_stage >/dev/null 2>&1; then
    say "  校驗：通過"
  else
    say "  校驗：失敗"
  fi
  if [ -d "$APP" ]; then
    v="$(app_version "$APP")"
    a="$(asar_hash "$APP")"
    h="$(header_hash "$APP")"
    state="$(ext_state)"
    case "$state" in
      original) state="原始（尚未套用 Sites 補丁）" ;;
      patched) state="已套用 Sites 繁中補丁" ;;
      *) state="未知" ;;
    esac
    say "目前 App：$APP"
    say "  版本：${v:-讀取失敗}"
    say "  Sites 擴充套件：$state"
    if [ "$a" = "$EXPECTED_ASAR" ] && [ "$h" = "$EXPECTED_HEADER" ]; then
      say "  主程式繁中補丁：已套用"
    else
      say "  主程式繁中補丁：內容不符"
    fi
    if /usr/bin/codesign --verify --deep --strict "$APP" >/dev/null 2>&1; then
      say "  簽章：驗證通過"
    else
      say "  簽章：驗證失敗"
    fi
  else
    say "目前 App：不存在（$APP）"
  fi
  if [ -d "$SNAP" ]; then
    say "套用前快照：存在（$SNAP）"
  else
    say "套用前快照：不存在"
  fi
  if qoder_is_running; then
    say "Qoder 主程式：執行中（PID: $(printf '%s ' $(qoder_main_pids))）"
  else
    say "Qoder 主程式：未執行"
  fi
  if [ -f "$PLIST" ]; then
    say "自動安裝器：已排入（$PLIST）"
  else
    say "自動安裝器：未排入"
  fi
  if [ -f "$LOG" ]; then
    say "最近記錄："
    /usr/bin/tail -n 10 "$LOG" | /usr/bin/sed 's/^/  /'
  fi
}

case "${1:-wait}" in
  wait)
    wait_mode
    ;;
  now)
    now_mode
    exit $?
    ;;
  check|--check)
    check_mode
    exit 0
    ;;
  *)
    say "用法：$0 [wait|now|check]"
    exit 64
    ;;
esac
