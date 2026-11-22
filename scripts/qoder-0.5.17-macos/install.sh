#!/bin/bash
# 套用 Qoder CN 繁體中文（台灣用語）補丁的安裝程式（0.5.17）。
# 用法：install.sh [wait|now|check|restore]

set -u
umask 022
export PATH="/usr/bin:/bin:/usr/sbin:/sbin"
unset ELECTRON_RUN_AS_NODE 2>/dev/null || true

PATCH_DIR="$HOME/Library/Application Support/QoderPatch"
STAGED_APP="$PATCH_DIR/Qoder CN.app"
APP="/Applications/Qoder CN.app"
BACKUP="/Applications/Qoder CN.app.pre-tw-0.5.17"
PLIST="$HOME/Library/LaunchAgents/com.qodercn.twpatch0517.plist"
LOG="$PATCH_DIR/install_0517.log"
LOCK_DIR="$PATCH_DIR/install_0517.lock.d"
MAIN_EXE="$APP/Contents/MacOS/Qoder CN"
LSREGISTER="/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister"

EXPECTED_VERSION="0.5.17"
EXPECTED_ASAR_SIZE="174598478"
EXPECTED_ASAR_FILE="8c3b8e92e7f3d04b48b6182721980af16273d1cb79fb002a8157886722232096"
EXPECTED_HEADER="7f24d06d40faa1d025a946b0d7eb3f64b1698c4e018fce771c7d436573eaa9b4"
ORIGINAL_ASAR_FILE="da16d204d46e7f912e753125c50519a2480b2c13faced8e8ef7036875ba130f7"

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
      if (line ~ /\.(mjs|cjs|js)([ \t]|$)/) next
      print pid
    }'
}

qoder_is_running() {
  [ -n "$(qoder_main_pids)" ]
}

qoder_renderer_pids() {
  /bin/ps -axo pid=,command= | /usr/bin/awk -v helper="$APP/Contents/Frameworks/Qoder CN Helper (Renderer).app/Contents/MacOS/Qoder CN Helper (Renderer)" '
    {
      pid = $1
      line = $0
      sub(/^[ \t]+/, "", line)
      sub(/^[0-9]+[ \t]+/, "", line)
      if (index(line, helper) != 1) next
      if (line ~ /--type=renderer([ \t]|$)/) print pid
    }'
}

kill_patched_main() {
  local pids i p
  pids="$(qoder_main_pids)"
  [ -z "$pids" ] && return 0
  log "正在結束測試啟動的 Qoder CN（PID: $(printf '%s ' $pids)）"
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

verify_staged_fast() {
  local actual_header actual_version actual_size
  if [ ! -d "$STAGED_APP" ]; then
    log "找不到暫存的繁中版 App：$STAGED_APP"
    return 1
  fi
  actual_version="$(app_version "$STAGED_APP")"
  actual_header="$(header_hash "$STAGED_APP")"
  actual_size="$(/usr/bin/stat -f %z "$STAGED_APP/Contents/Resources/app.asar" 2>/dev/null)"
  if [ "$actual_version" != "$EXPECTED_VERSION" ]; then
    log "暫存 App 版本不符：$actual_version（預期 $EXPECTED_VERSION）"
    return 1
  fi
  if [ "$actual_header" != "$EXPECTED_HEADER" ]; then
    log "暫存 App 的 Info.plist 完整性雜湊不符，取消套用。"
    return 1
  fi
  if [ "$actual_size" != "$EXPECTED_ASAR_SIZE" ]; then
    log "暫存 App 的 app.asar 大小不符，取消套用。"
    return 1
  fi
  if [ -e "$STAGED_APP/Contents/CodeResources" ]; then
    log "暫存 App 仍帶有舊的簽章資源，取消套用。"
    return 1
  fi
  return 0
}

verify_staged() {
  local actual_asar actual_catalog
  if ! verify_staged_fast; then
    return 1
  fi
  actual_asar="$(asar_hash "$STAGED_APP")"
  if [ "$actual_asar" != "$EXPECTED_ASAR_FILE" ]; then
    log "暫存 App 的 app.asar 雜湊不符，取消套用。"
    return 1
  fi
  actual_catalog="$(/usr/bin/shasum -a 256 "$STAGED_APP/Contents/Resources/extensions/catalog.v1.json" 2>/dev/null | /usr/bin/awk '{print $1}')"
  if [ -z "$actual_catalog" ]; then
    log "暫存 App 缺少 Sites catalog，取消套用。"
    return 1
  fi
  if ! /usr/bin/codesign --verify --deep --strict "$STAGED_APP" >/dev/null 2>&1; then
    log "暫存 App 的簽章驗證失敗，取消套用。"
    return 1
  fi
  if ! /usr/bin/codesign -d --entitlements :- "$STAGED_APP" 2>/dev/null | /usr/bin/grep -q "com.apple.security.cs.allow-jit"; then
    log "暫存 App 缺少 JIT 權限（entitlements），取消套用。"
    return 1
  fi
  if ! /usr/bin/codesign -d --entitlements :- "$STAGED_APP/Contents/Frameworks/Qoder CN Helper (Renderer).app" 2>/dev/null | /usr/bin/grep -q "com.apple.security.cs.allow-jit"; then
    log "暫存 App 的 Renderer 缺少 JIT 權限，取消套用。"
    return 1
  fi
  return 0
}

verify_installed_patched() {
  local actual_asar actual_header actual_version
  actual_version="$(app_version "$APP")"
  actual_asar="$(asar_hash "$APP")"
  actual_header="$(header_hash "$APP")"
  if [ "$actual_version" != "$EXPECTED_VERSION" ]; then
    log "安裝後版本不符：$actual_version"
    return 1
  fi
  if [ "$actual_asar" != "$EXPECTED_ASAR_FILE" ]; then
    log "安裝後的 app.asar 雜湊不符。"
    return 1
  fi
  if [ "$actual_header" != "$EXPECTED_HEADER" ]; then
    log "安裝後的 Info.plist 完整性雜湊不符。"
    return 1
  fi
  if ! /usr/bin/codesign --verify --deep --strict "$APP" >/dev/null 2>&1; then
    log "安裝後的簽章驗證失敗。"
    return 1
  fi
  return 0
}

launch_and_wait() {
  local rc i pids
  log "正在啟動 Qoder CN 進行測試。"
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
    log "等了 25 秒仍未偵測到 Qoder CN 主程式。"
    return 1
  fi
  i=0
  while [ "$i" -lt 20 ]; do
    if [ -n "$(qoder_renderer_pids)" ]; then
      break
    fi
    /bin/sleep 1
    i=$((i + 1))
  done
  if [ -z "$(qoder_renderer_pids)" ]; then
    log "Qoder CN 主程式已啟動，但 20 秒內沒有建立畫面行程（renderer）。"
    return 1
  fi
  pids="$(printf '%s ' $(qoder_main_pids))"
  log "Qoder CN 主程式已出現（PID: $pids），觀察 8 秒確認沒有立即結束。"
  for i in 1 2 3 4; do
    /bin/sleep 2
    if ! qoder_is_running; then
      log "Qoder CN 啟動後又結束了。"
      return 1
    fi
  done
  if [ -z "$(qoder_renderer_pids)" ]; then
    log "Qoder CN 的畫面行程在啟動後結束了。"
    return 1
  fi
  return 0
}

rollback() {
  local failed_app
  failed_app="$PATCH_DIR/Qoder CN.app.failed-$(/bin/date +%Y%m%d-%H%M%S)"
  kill_patched_main
  if [ -d "$APP" ]; then
    log "把無法啟動的繁中版移到：$failed_app"
    if ! /bin/mv "$APP" "$failed_app"; then
      log "無法移開繁中版 App；原始版仍在 $BACKUP，請手動放回 /Applications/Qoder CN.app。"
      /bin/rm -f "$PLIST" 2>/dev/null || true
      return 1
    fi
  fi
  if [ -d "$BACKUP" ]; then
    if ! /bin/mv "$BACKUP" "$APP"; then
      log "無法放回原始 App（備份仍在 $BACKUP），請手動處理。"
      /bin/rm -f "$PLIST" 2>/dev/null || true
      return 1
    fi
  else
    log "找不到原始 App 備份 $BACKUP，無法自動還原。"
    /bin/rm -f "$PLIST" 2>/dev/null || true
    return 1
  fi
  "$LSREGISTER" -f "$APP" >/dev/null 2>&1 || true
  if launch_and_wait; then
    log "已還原成原始 Qoder CN，並重新啟動。"
  else
    log "原始 Qoder CN 已放回 /Applications/Qoder CN.app，但自動啟動測試未通過；請手動開啟。"
  fi
  /bin/rm -f "$PLIST" 2>/dev/null || true
  return 0
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

apply_once_locked() {
  local installed_version installed_asar
  if ! verify_staged_fast; then
    return 1
  fi

  installed_version="$(app_version "$APP")"
  installed_asar="$(asar_hash "$APP")"

  if [ "$installed_version" = "$EXPECTED_VERSION" ] && [ "$installed_asar" = "$EXPECTED_ASAR_FILE" ]; then
    log "繁中補丁已經套用，不需要再次安裝。"
    /bin/rm -f "$PLIST" 2>/dev/null || true
    return 0
  fi

  if [ "$installed_version" != "$EXPECTED_VERSION" ]; then
    log "目前 Qoder CN 版本是 ${installed_version:-未知}，不是 $EXPECTED_VERSION；為避免覆蓋新版，取消套用。"
    return 2
  fi

  if [ "$installed_asar" != "$ORIGINAL_ASAR_FILE" ]; then
    log "目前 Qoder CN 的 app.asar 與原始 $EXPECTED_VERSION 不同（可能已更新或修改過），取消套用。"
    return 2
  fi

  if [ -e "$BACKUP" ]; then
    log "備份位置已存在：$BACKUP。為避免覆蓋既有備份，取消套用。"
    return 3
  fi

  if qoder_is_running; then
    log "Qoder CN 仍在執行，取消這次套用。"
    return 4
  fi

  /usr/bin/osascript -e 'display notification "正在套用繁中版，請稍候約 15 秒，先不要重新開啟 Qoder CN。" with title "Qoder 繁體中文"' >/dev/null 2>&1 || true

  log "正在把原始 App 移到備份：$BACKUP"
  if ! /bin/mv "$APP" "$BACKUP"; then
    log "無法移動原始 App，取消套用。"
    return 5
  fi

  log "正在安裝繁中版 App。"
  if ! /bin/mv "$STAGED_APP" "$APP"; then
    log "無法安裝繁中版 App；正在放回原始 App。"
    /bin/mv "$BACKUP" "$APP" 2>/dev/null || true
    return 6
  fi
  /usr/bin/xattr -dr com.apple.quarantine "$APP" >/dev/null 2>&1 || true

  if ! verify_installed_patched; then
    log "安裝後驗證失敗，開始還原。"
    rollback
    return 7
  fi

  "$LSREGISTER" -f "$APP" >/dev/null 2>&1 || true

  if launch_and_wait; then
    log "繁中補丁套用成功，Qoder CN 已重新啟動。"
    /usr/bin/osascript -e 'display notification "繁中版已套用。請點右上角頭像，把語言改成「繁體中文」。" with title "Qoder 繁體中文"' >/dev/null 2>&1 || true
    /bin/rm -f "$PLIST" 2>/dev/null || true
    return 0
  fi

  log "繁中版 Qoder CN 無法正常啟動，開始還原。"
  rollback
  return 8
}

wait_mode() {
  local quiet rc seen
  if ! verify_staged; then
    log "暫存繁中版驗證失敗；安裝器結束。"
    /bin/rm -f "$PLIST" 2>/dev/null || true
    exit 1
  fi
  log "繁中補丁安裝器已待命，等待 Qoder CN 完全結束後自動套用。"
  quiet=0
  seen=0
  while :; do
    if qoder_is_running; then
      if [ "$seen" -eq 0 ]; then
        log "偵測到 Qoder CN 正在執行；完全結束 Qoder CN 後就會套用。"
        seen=1
      fi
      quiet=0
    elif [ "$seen" -eq 0 ]; then
      /bin/sleep 1
      continue
    else
      quiet=$((quiet + 1))
      if [ "$quiet" -ge 2 ]; then
        log "Qoder CN 已結束，開始套用繁中補丁。"
        apply_once
        rc=$?
        case "$rc" in
          0)
            exit 0
            ;;
          2|3)
            log "這次不套用；安裝器結束，詳細原因見上方。"
            /bin/rm -f "$PLIST" 2>/dev/null || true
            exit "$rc"
            ;;
          1|5|6|7|8)
            log "套用失敗（代碼 $rc）；安裝器結束。"
            /bin/rm -f "$PLIST" 2>/dev/null || true
            exit "$rc"
            ;;
          *)
            log "這次未能套用（代碼 $rc），稍後再試。"
            quiet=0
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
    log "Qoder CN 正在執行。請先完全結束 Qoder CN（⌘Q），再執行一次。"
    return 4
  fi
  if ! verify_staged; then
    log "暫存繁中版驗證失敗；取消套用。"
    return 1
  fi
  apply_once
  rc=$?
  if [ "$rc" -eq 0 ]; then
    /bin/rm -f "$PLIST" 2>/dev/null || true
  fi
  return "$rc"
}

restore_mode() {
  local failed_app
  if qoder_is_running; then
    log "Qoder CN 正在執行。請先完全結束 Qoder CN（⌘Q），再執行一次。"
    return 4
  fi
  if [ ! -d "$BACKUP" ]; then
    log "找不到原始版備份 $BACKUP，無法還原。"
    return 1
  fi
  if ! acquire_lock; then
    log "另一個安裝程序正在執行，這次先不還原。"
    return 9
  fi
  failed_app="$PATCH_DIR/Qoder CN.app.patched-$(/bin/date +%Y%m%d-%H%M%S)"
  if [ -d "$APP" ]; then
    log "把已套用的繁中版移到：$failed_app"
    /bin/mv "$APP" "$failed_app" || { release_lock; return 5; }
  fi
  if ! /bin/mv "$BACKUP" "$APP"; then
    log "無法放回原始 App（備份仍在 $BACKUP），請手動處理。"
    release_lock
    return 6
  fi
  release_lock
  "$LSREGISTER" -f "$APP" >/dev/null 2>&1 || true
  log "已還原成原始 Qoder CN。"
  return 0
}

check_mode() {
  local staged_ver staged_asar staged_header installed_ver installed_asar installed_header state
  say "Qoder CN 繁體中文補丁狀態（0.5.17）"
  say "----------------------"
  if [ -d "$STAGED_APP" ]; then
    staged_ver="$(app_version "$STAGED_APP")"
    staged_asar="$(asar_hash "$STAGED_APP")"
    staged_header="$(header_hash "$STAGED_APP")"
    say "暫存繁中版：$STAGED_APP"
    say "  版本：${staged_ver:-讀取失敗}"
    say "  app.asar 雜湊：${staged_asar:-讀取失敗}"
    if [ "$staged_ver" = "$EXPECTED_VERSION" ] && [ "$staged_asar" = "$EXPECTED_ASAR_FILE" ] && [ "$staged_header" = "$EXPECTED_HEADER" ] && /usr/bin/codesign --verify --deep --strict "$STAGED_APP" >/dev/null 2>&1; then
      say "  內容與簽章：驗證通過"
    else
      say "  內容與簽章：驗證失敗"
    fi
  else
    say "暫存繁中版：不存在（$STAGED_APP）"
  fi

  if [ -d "$APP" ]; then
    installed_ver="$(app_version "$APP")"
    installed_asar="$(asar_hash "$APP")"
    installed_header="$(header_hash "$APP")"
    if [ "$installed_asar" = "$EXPECTED_ASAR_FILE" ]; then
      state="已套用繁中補丁"
    elif [ "$installed_asar" = "$ORIGINAL_ASAR_FILE" ]; then
      state="原始版本（尚未套用）"
    else
      state="內容未知"
    fi
    say "目前 App：$APP"
    say "  版本：${installed_ver:-讀取失敗}"
    say "  狀態：$state"
    if /usr/bin/codesign --verify --deep --strict "$APP" >/dev/null 2>&1; then
      say "  簽章：驗證通過"
    else
      say "  簽章：驗證失敗"
    fi
  else
    say "目前 App：不存在（$APP）"
  fi

  if [ -d "$BACKUP" ]; then
    say "原始版備份：存在（$BACKUP）"
  else
    say "原始版備份：尚未建立"
  fi

  if [ -d "$APP" ] && qoder_is_running; then
    say "Qoder CN 主程式：執行中（PID: $(printf '%s ' $(qoder_main_pids))）"
  else
    say "Qoder CN 主程式：未執行"
  fi

  if [ -f "$PLIST" ]; then
    say "自動安裝器：已排入（$PLIST）"
  else
    say "自動安裝器：未排入"
  fi

  if [ -f "$LOG" ]; then
    say "最近記錄："
    /usr/bin/tail -n 8 "$LOG" | /usr/bin/sed 's/^/  /'
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
  restore)
    restore_mode
    exit $?
    ;;
  *)
    say "用法：$0 [wait|now|check|restore]"
    exit 64
    ;;
esac