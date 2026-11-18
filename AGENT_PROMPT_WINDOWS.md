# Agent 安裝提示詞（Qoder 0.5.13 繁中補丁・Windows）

把下面「提示詞」整段複製給你的 Agent（需具備 shell 權限、可修改 `%LOCALAPPDATA%\Programs\Qoder`）。
它會在你的機器上就地產生並套用補丁，不會下載或散布 Qoder 的任何二進位檔。

macOS 版（0.5.6）請見 [AGENT_PROMPT.md](AGENT_PROMPT.md)。

---

## 提示詞

你是一位在 Windows 上協助安裝「Qoder 繁體中文（台灣）補丁」的 Agent。請嚴格依照下列步驟逐步執行，每步做完都要驗證；任何一步失敗就停止並回報原因，不要跳過或猜測。

**授權與限制**：使用者已授權你修改 `%LOCALAPPDATA%\Programs\Qoder`，但你要先備份、可還原。你**不得**上傳或散布 Qoder 的 App、`app.asar`、解出的原始碼或任何帳號資料。

### 0. 版本檢查
- 讀 `%LOCALAPPDATA%\Programs\Qoder\resources\build-manifest.json` 的 `productVersion`，必須是 `0.5.13`。不是就停止，並說明本提示詞只支援 0.5.13（其他版本錨點不同，需重新盤點）。
- 記錄原始 `resources\app.asar` 與 `Qoder.exe` 的 SHA-256，供最後驗證與還原。

### 1. 取得工具與翻譯資料
- `git clone https://github.com/Lorin1470/qoder-zh-tw-patch.git`（或使用使用者既有的 clone），後續步驟都在 repo 根目錄執行。
- `python -m pip install -r requirements.txt`（OpenCC）。
- `( cd tools/jsparse && npm install )`（acorn）。
- 確認 `work/0513-dict/` 內有：`tw_base.json`、`mf2_tw.json`、`fT2_tw.json`、`sites_tw.json`、`sites_tw_annot.json`（已內附，不需重建）。

### 2. 解包（保留 `out/` 結構）
- `npx --yes @electron/asar extract "%LOCALAPPDATA%/Programs/Qoder/resources/app.asar" work/0513-original`
- 確認 `work/0513-original/out/main` 與 `work/0513-original/out/renderer` 存在。
- `app.asar.unpacked` 原生檔解出時的警告可忽略。

### 3. 產生補丁
- `python tools/patch_app_files_0513.py` → 輸出到 `work/0513-stage/out`（13 個檔案）。任何錨點找不到會直接報錯，不會產出半套補丁。
- `python tools/patch_sites_tw_0513.py` → 輸出到 `work/0513-sites-stage`（會先驗證 Sites 三檔的原始 SHA-256）。
- `python tools/patch_catalog_tw_0513.py` → 更新 `catalog.v1.json` 的雜湊與 manifest（**必須在換檔之前執行**，它會讀目前安裝中的 catalog）。
- 語法檢查：對 `work/0513-stage/out/out/renderer/assets/*.js` 與 `out/main/electronMain.js` 用 `node --input-type=module --check`（0.5.13 的 main 是 ESM）；對 Sites 的 `view.cjs`、`publishPreview.cjs` 用 `node --check`。任一失敗就停止。

### 4. 套用（Qoder 必須完全結束）

**注意：如果你就在 Qoder 裡面執行，關閉 Qoder 會中斷你自己的行程。** 因此預設使用「延後套用」：

- 以**獨立（detached）行程**啟動 `python tools/install_win_0513.py wait`，stdout 導向 `work/0513-apply.log`。Python 範例：

  ```python
  import subprocess, sys
  log = open('work/0513-apply.log', 'w')
  subprocess.Popen(
      [sys.executable, 'tools/install_win_0513.py', 'wait'],
      stdout=log, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
      creationflags=0x00000008 | 0x00000200 | 0x04000000,  # DETACHED | NEW_PROCESS_GROUP | BREAKAWAY_FROM_JOB
  )
  ```

- 確認監看行程存在且 log 顯示 `waiting for Qoder to close...`。
- 請使用者**完全結束 Qoder**（不是只關視窗）。監看程式會在 Qoder 結束後自動：
  1. 備份 `app.asar`、`Qoder.exe`、`catalog.v1.json` 與 Sites 三檔到 `%LOCALAPPDATA%\QoderPatch\backup-0.5.13`（含原始 SHA-256 紀錄；備份已存在會拒絕執行）。
  2. 用 `tools/repack_asar.py` 重打包 ASAR。
  3. 把 `Qoder.exe` 資源區內嵌的 asar header 雜湊等長置換成新的（Windows 的 `EnableEmbeddedAsarIntegrityValidation` fuse 已啟用，**沒更新雜湊會無法啟動**）。
  4. 換入 Sites 三檔與 `catalog.v1.json`。
  5. 重開 Qoder。套用失敗會自動還原備份再重開。
- 若使用者不在 Qoder 內操作 Agent，也可請使用者先關閉 Qoder，再直接執行 `python tools/install_win_0513.py apply`。

### 5. 驗證並回報
- Qoder 重開後，讀 `work/0513-apply.log` 確認出現 `patch applied` 與 `Qoder relaunched`。
- 驗證安裝中的 `app.asar` header hash 與 log 中的 `header_hash` 一致、`Qoder.exe` 內含該雜湊、Sites 三檔與 catalog 和 `work/0513-sites-stage` 的 SHA-256 相符。
- 請使用者到「**設定 → 外觀 → 語言**」確認可選「**繁體中文**」；切換後介面應為台灣用語（檔案、設定、搜尋、載入、儲存、站點），左側 Sites 入口顯示「站點」。
- 回報：每步結果、原始與補丁後 `app.asar` 的 SHA-256、`header_hash`、最終語言狀態。
- 全程不得把 Qoder 二進位、`app.asar` 或解出的原始碼上傳到任何地方。

### 還原
- 任何時候要還原：關閉 Qoder 後執行 `python tools/install_win_0513.py restore`（會先驗證備份檔的 SHA-256 再還原）。

### 已知限制
- Qoder 自動更新會整包覆蓋補丁，更新後需重跑流程；錨點與雜湊依版本而異。
- 修改 `Qoder.exe` 會使其 Authenticode 簽章失效（Windows 不強制驗證，可正常啟動）；介意者請先備份並自行評估。