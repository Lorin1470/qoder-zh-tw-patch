# Agent 安裝提示詞（Qoder 0.5.6 繁中補丁）

把下面「提示詞」整段複製給你的 Agent（需具備 shell 權限、可修改 `/Applications/Qoder.app`）。
它會在你的機器上就地產生並套用補丁，不會下載或散布 Qoder 的任何二進位檔。

---

## 提示詞

你是一位在 macOS 上協助安裝「Qoder 繁體中文（台灣）補丁」的 Agent。請嚴格依照下列步驟逐步執行，每步做完都要驗證；任何一步失敗就停止並回報原因，不要跳過或猜測。

**授權與限制**：使用者已授權你修改 `/Applications/Qoder.app`，但你要先備份、可還原。你**不得**上傳或散布 Qoder 的 App、`app.asar`、解出的原始碼或任何帳號資料。

### 0. 版本檢查
- 讀 `/Applications/Qoder.app/Contents/Info.plist` 的 `CFBundleShortVersionString`，必須是 `0.5.6`。不是就停止，並說明本提示詞只支援 0.5.6。
- 記錄原始 `Contents/Resources/app.asar` 與 `Contents/Resources/extensions/catalog.v1.json` 的 SHA-256，供最後驗證與還原。

### 1. 取得工具與翻譯資料
- `git clone https://github.com/Lorin1470/qoder-zh-tw-patch.git`（或使用使用者既有的 clone）。
- `python3 -m pip install -r requirements.txt`（OpenCC）。
- `( cd tools/jsparse && npm install )`（acorn）。
- 確認 `work/056-dict/` 內有：`tw_base.json`、`mf2_tw.json`、`fT2_tw.json`、`sites_tw.json`、`sites_tw_annot.json`。

### 2. 備份（必做）
- `cp -cR /Applications/Qoder.app /Applications/Qoder.app.original-0.5.6`
- 確認備份存在且可讀。後續若部署失敗，用這個備份或 `scripts/qoder-0.5.6/restore.sh` 還原。

### 3. 解包（保留 `out/` 結構）
- `npx @electron/asar extract /Applications/Qoder.app/Contents/Resources/app.asar work/056-original`
- 確認 `work/056-original/out/main` 與 `work/056-original/out/renderer` 存在。
- `unpacked` 原生檔（sharp、node-pty 等）解出時的 ENOENT 警告可忽略。

### 4. 產生補丁
- `python3 tools/patch_app_files_056.py` → 輸出到 `/tmp/qoder_asar_056/out`（13 個 JS＋`index.html`）。
- `python3 tools/patch_sites_tw_056.py` → 輸出到 `work/056-sites-stage`。
- `python3 tools/patch_catalog_tw_056.py` → 更新 `catalog.v1.json` 的雜湊與 manifest（**必須在換掉 App 之前執行**，它會讀目前安裝中的 catalog）。
- 語法檢查：對 `/tmp/qoder_asar_056/out/out/renderer/assets/*.js` 用 `node --input-type=module --check`、對 `out/main/electronMain.js` 用 `node --check`；任一失敗就停止。

### 5. 重建 ASAR
- 用 `tools/repack_asar.py`：`--src` 指向原始 `app.asar`、`--root /tmp/qoder_asar_056/out`、`--replace` 列出所有被改的 `out/...` 相對路徑。
- 記下輸出的 `header_hash`（下一步要用）。

### 6. 組裝並重新簽章（先做暫存副本，不要直接改執行中的 App）
- 用 `cp -cR` 複製原始 App 到暫存位置。
- 換入新的 `Contents/Resources/app.asar`。
- 用 `/usr/libexec/PlistBuddy` 把 `:ElectronAsarIntegrity:Resources/app.asar:hash` 設成 `header_hash`。
- 換入 Sites 三個檔（`extensions/qoder.sites/dist/browser/view.cjs`、`publishPreview.cjs`、`.qoder-app-plugin/plugin.json`）與 `extensions/catalog.v1.json`。
- 刪除暫存 App 的 `Contents/CodeResources`（舊公證票據，修改後已失效）。
- 建立 entitlements plist，內容至少含：`com.apple.security.automation.apple-events`、`com.apple.security.cs.allow-jit`、`com.apple.security.cs.allow-unsigned-executable-memory`、`com.apple.security.cs.disable-library-validation`、`com.apple.security.device.audio-input`、`com.apple.security.network.client`、`com.apple.security.network.server`（皆為 true）。
- 以 ad-hoc 重簽（外層即可，勿加 `--deep`）：`codesign --force --sign - --entitlements <plist> <app>`。
- `codesign --verify --deep --strict <app>` 必須通過，否則停止。

### 7. 部署
- 請使用者**完全結束 Qoder（⌘Q）**，或用 `scripts/qoder-0.5.6/install.sh` 的延後套用（`wait` 模式＋LaunchAgent）。
- 套用前再次確認目前 App 版本 `0.5.6`、原始 `app.asar` 雜湊與步驟 0 記錄相符。
- 以目錄替換方式換上新 App（先把原版移到備份位置，再放入新版），執行 `lsregister -f /Applications/Qoder.app`，再 `env -u ELECTRON_RUN_AS_NODE open -n /Applications/Qoder.app`。
- 若啟動失敗，**自動還原**原始版並重開。

### 8. 驗證並回報
- 重開後請使用者到「**設定 → 外觀 → 語言**」確認可選「繁體中文」；切換後介面應為台灣用語（終端機、檔案、字型、擴充功能、站點）。
- 回報：每步結果、原始與補丁後 `app.asar` 的 SHA-256、`header_hash`、簽章驗證結果、最終語言狀態。
- 全程不得把 Qoder 二進位、`app.asar` 或解出的原始碼上傳到任何地方。
