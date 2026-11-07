# Qoder 繁體中文（台灣）在地化補丁

非官方專案，為 **Qoder Desktop（macOS arm64）** 加入繁體中文（台灣用語），並把內建的 **Sites** 擴充套件一起繁中化。

目前支援並實機驗證的版本：

- **0.5.6**（最新，見下方「0.5.6 版變更」）
- 0.4.11（舊版，工具保留於 `tools/*.py` 與 `scripts/qoder-0.4.11/`）

兩個版本都在 macOS 15.7.7 arm64 上實際套用並驗證：

- 主介面、原生選單、設定頁
- 左側「站點」入口
- Sites 入口頁：探索 Sites、我的站點、與我共用、新增站點、尚未建立站點
- Sites 的發佈預覽與標註字串

> 想讓 Agent 幫你安裝？把 **[AGENT_PROMPT.md](AGENT_PROMPT.md)** 裡的提示詞整段貼給具 shell 權限、可修改 `/Applications/Qoder.app` 的 Agent，它會在你的機器上就地產生並套用補丁。

## 0.5.6 版變更

0.5.6 是大改版，檔案結構與錨點全部改變，0.4.11 的補丁無法沿用，因此重寫了一組 `*_056.py` 腳本與新字典：

- **目錄結構**：由 `main/`、`renderer/` 改為 `out/main/`、`out/renderer/`，所有 renderer 檔案名稱重新雜湊。
- **i18n 集中化**：整個 i18next 內聯在 `out/renderer/assets/DidgxRds.js`。補丁在此注入 `zh-TW` 資源、把 `zh-TW` 加入語言清單與可用語言過濾器，並讓 locale 正規化把 `zh-tw`／`zh-hant` 映射到 `zh-TW`。
- **語言設定位置**：0.5.6 的語言選項在「**設定 → 外觀 → 語言**」（不是「一般」）。
- **原生繁中**：0.5.6 內建完整的「繁體中文（香港）」`zh-HK` 字典，但官方把設定下拉與驗證器限制為只開放 `zh`／`en`，所以畫面上看不到，而且港版用語（用戶／配置／網絡）不是台灣用語。本補丁另外建立真正的 `zh-TW` 台灣用語字典，而非重用港版。
- **字串抽取改用 acorn**：舊的啟發式掃描器在含複雜正則／模板字串的 bundle（markdown parser 等）會誤判字串邊界而破壞程式碼。0.5.6 版改用真正的 JS 解析器 `acorn`（`tools/jsparse/extract_ranges.js`）取得精確的字串與模板 range，只轉換其中的中文。
- **Sites 擴展**：錨點改為 `J4`／`z7`／`g7`；`catalog.v1.json` 仍以 plugin id 搜尋、與版本無關。

0.5.6 的字典位於 `work/056-dict/`（`tw_base.json` 主程式、`mf2_tw.json` issueDrawer、`fT2_tw.json` projectBoard、`sites_tw.json`＋`sites_tw_annot.json` Sites）。

## 這個補丁做了什麼

1. **主程式 i18n**：注入 `zh-TW` 資源，並把語言選項接到 Qoder 的設定流程。
2. **Sites 擴充套件**：原本所有 `zh-*` 都會落到簡中字典；補丁加入台灣繁中字典，並以正則辨識 `zh-TW`、`zh-Hant`、`zh-HK`、`zh-MO`。
3. **擴充套件完整性清單**：Qoder 會用 `catalog.v1.json` 驗證內建擴充套件的檔案雜湊。只改翻譯檔會讓 Sites 入口被停用，因此補丁同時更新三個檔案的雜湊與 `manifest`。
4. **重新簽章**：修改 App 資源後以 ad-hoc 簽章重新簽署，並在套用前備份、啟動失敗時自動還原。

## 收錄與不包含

**收錄**

- `tools/`：繁中轉換、i18n 注入、Sites 字典注入、ASAR 重打包工具（`*_056.py` 為 0.5.6 版）
- `tools/jsparse/`：以 acorn 抽取 JS 字串 range 的小工具（0.5.6 使用）
- `translations/zh-TW/`：0.4.11 主程式繁中翻譯（已建置完成）
- `work/056-dict/`：0.5.6 繁中翻譯（主程式、issueDrawer、projectBoard、Sites）
- `data/sites_tw.json`、`data/sites_tw_annot.json`：0.4.11 Sites 221 條介面字串與 13 條標註字串
- `scripts/qoder-0.4.11/`、`scripts/qoder-0.5.6/`：各版實際使用的參考安裝／還原腳本

**不包含**

- Qoder App、`app.asar`、解出的原始程式碼或任何活動資料
- 帳號、Keychain、個人檔案或本機日誌
- LaunchAgent plist（內含機器特定的絕對路徑，請依需要自行建立）

Qoder 為其權利人所有。本專案只提供工具與翻譯資料；請從**你自己安裝的 Qoder** 產生補丁，不要重新散布 Qoder 的二進位檔或原始碼。

## 需求

- macOS（測試於 macOS 15.7.7 arm64）
- Qoder Desktop **0.5.6**（或舊版 0.4.11）
- Python 3.9+
- Node.js / `npx`（解出 `app.asar`；0.5.6 另需 acorn 解析字串）
- 可寫入 `/Applications/Qoder.app` 的權限

```bash
python3 -m pip install -r requirements.txt
# 0.5.6：安裝 acorn（僅供 tools/jsparse 使用）
( cd tools/jsparse && npm install )
```

## 使用流程

> 以下流程會修改 `/Applications/Qoder.app`。請先備份整個 App，並在 Qoder 完全結束時操作。

### 1. 解出原始 App 資源

```bash
./scripts/extract-qoder.sh
# 預設解到 work/original
```

這個資料夾只用於本機產生補丁，已被 `.gitignore` 排除。

### 2. 主程式繁中化

```bash
python3 tools/patch_app_files.py
```

輸出會寫到 `/tmp/qoder_asar/out`。接著用 `tools/repack_asar.py` 重建 ASAR：

接著用 `tools/repack_asar.py` 重建 ASAR，`--replace` 要列出 `patch_app_files.py` 產生的每一個檔案。完整的替換、`Info.plist` 完整性雜湊更新、移除舊公證票據與 ad-hoc 重簽流程，請參考 `scripts/qoder-0.4.11/install.sh`。那份腳本是 0.4.11 的實際參考實作，內含版本與雜湊檢查；它假設修改後的 App 已暫存在 `~/Library/Application Support/QoderPatch/Qoder.app`，不是從零開始的一鍵安裝器。

### 3. Sites 繁中化

```bash
./scripts/build-sites-patch.sh
```

會產生：

```
work/sites_stage/dist/browser/view.cjs
work/sites_stage/dist/browser/publishPreview.cjs
work/sites_stage/.qoder-app-plugin/plugin.json
work/sites_stage/catalog.v1.json
```

把前三個檔案換入：

```
/Applications/Qoder.app/Contents/Resources/extensions/qoder.sites/
```

並把 `catalog.v1.json` 換入：

```
/Applications/Qoder.app/Contents/Resources/extensions/
```

最後重新簽章。`scripts/qoder-0.4.11/sites_tw_apply.sh` 與 `sites_catalog_apply.sh` 是實際使用的延後套用／還原腳本，內含完整性檢查與備份；使用前請先閱讀並依你的路徑調整。

### 4. 重新開啟 Qoder

到設定把語言切換成「繁體中文」，重新開啟 Qoder。Sites 入口會顯示「站點」。

### 0.5.6 流程

先安裝 acorn，並把 0.5.6 的 `app.asar` 解到 `work/056-original`（需保留 `out/main`、`out/renderer` 結構）：

```bash
( cd tools/jsparse && npm install )
npx @electron/asar extract /Applications/Qoder.app/Contents/Resources/app.asar work/056-original
```

字典已內附於 `work/056-dict/`。若要從你自己安裝的 Qoder 重新產生字典，先抽出 `DidgxRds.js` 的 zh／zh-HK 資源存成 `work/056-dict/new_zh.json`、`new_zhHK.json`，再執行 `python3 tools/build_zh_tw_056.py`。接著產生補丁：

```bash
python3 tools/patch_app_files_056.py     # 輸出到 /tmp/qoder_asar_056/out
python3 tools/patch_sites_tw_056.py      # 輸出到 work/056-sites-stage
python3 tools/patch_catalog_tw_056.py    # 更新 catalog 的雜湊與 manifest
```

用 `tools/repack_asar.py` 重建 ASAR（`--replace` 要列出所有被改的 `out/...` 檔），更新 `Info.plist` 的 `ElectronAsarIntegrity` 雜湊、移除舊公證票據、以 ad-hoc 重簽，再把 Sites 檔案與 `catalog.v1.json` 換入 App。`scripts/qoder-0.5.6/install.sh` 是實際使用的延後套用／還原腳本，內含版本與雜湊檢查；它假設修改後的 App 已暫存在 `~/Library/Application Support/QoderPatch/Qoder.app`。

重開後，到「**設定 → 外觀 → 語言**」選「繁體中文」。

## 翻譯方針

- 以 OpenCC `s2twp` 為基礎，再用 `tools/tw.py` 的台灣用語覆寫修正。
- 採用台灣常見 UI 用語：設定、檔案、資料夾、程式碼、使用者、搜尋、載入、儲存、螢幕、網路。
- `Agent`、`PR` 等開發／品牌術語保留英文。
- 伺服器下發的活動文案（例如「1024｜创造力集结」）只有英文／簡中版本，不在本補丁的翻譯範圍。

## 已知限制

- Qoder 更新會覆蓋補丁，更新後需要重新產生並套用。
- Ad-hoc 重簽可能讓 macOS 再次詢問 Keychain／TCC 權限。
- 部分遠端文案、活動頁或新功能字串可能不在翻譯檔中。
- 本補丁的腳本分別針對 0.4.11 與 0.5.6 的檔案結構與雜湊；其他版本請先確認錨點再使用。

## 免責聲明

本專案與 Qoder 官方無關，不提供任何保證。修改應用程式與重新簽章有其風險，請務必先備份。Qoder 的商標、UI 文字與其他內容屬其權利人；本專案不散布 Qoder 的二進位檔或原始碼，翻譯資料僅用於介面在地化。

## 授權

程式碼採 MIT License，見 [LICENSE](LICENSE)。翻譯資料不主張對 Qoder 原始內容的權利。
