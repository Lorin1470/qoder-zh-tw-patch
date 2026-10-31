# Qoder 繁體中文（台灣）在地化補丁

非官方專案，為 **Qoder Desktop 0.4.11（macOS arm64）** 加入繁體中文（台灣用語），並把內建的 **Sites** 擴充套件一起繁中化。

目前已在 macOS 15.7.7 arm64、Qoder 0.4.11 上實際套用並驗證：

- 主介面、原生選單、設定頁
- 左側「站點」入口
- Sites 入口頁：探索 Sites、我的站點、與我共用、新增站點、尚未建立站點
- Sites 的發佈預覽與標註字串

## 這個補丁做了什麼

1. **主程式 i18n**：注入 `zh-TW` 資源，並把語言選項接到 Qoder 的設定流程。
2. **Sites 擴充套件**：原本所有 `zh-*` 都會落到簡中字典；補丁加入台灣繁中字典，並以正則辨識 `zh-TW`、`zh-Hant`、`zh-HK`、`zh-MO`。
3. **擴充套件完整性清單**：Qoder 會用 `catalog.v1.json` 驗證內建擴充套件的檔案雜湊。只改翻譯檔會讓 Sites 入口被停用，因此補丁同時更新三個檔案的雜湊與 `manifest`。
4. **重新簽章**：修改 App 資源後以 ad-hoc 簽章重新簽署，並在套用前備份、啟動失敗時自動還原。

## 收錄與不包含

**收錄**

- `tools/`：繁中轉換、i18n 注入、Sites 字典注入、ASAR 重打包工具
- `translations/zh-TW/`：主程式繁中翻譯（已建置完成）
- `data/sites_tw.json`、`data/sites_tw_annot.json`：Sites 221 條介面字串與 13 條標註字串
- `scripts/qoder-0.4.11/`：0.4.11 實際使用的參考安裝／還原腳本

**不包含**

- Qoder App、`app.asar`、解出的原始程式碼或任何活動資料
- 帳號、Keychain、個人檔案或本機日誌
- LaunchAgent plist（內含機器特定的絕對路徑，請依需要自行建立）

Qoder 為其權利人所有。本專案只提供工具與翻譯資料；請從**你自己安裝的 Qoder** 產生補丁，不要重新散布 Qoder 的二進位檔或原始碼。

## 需求

- macOS（測試於 macOS 15.7.7 arm64）
- Qoder Desktop **0.4.11**
- Python 3.9+
- Node.js / `npx`（只用來解出 `app.asar`）
- 可寫入 `/Applications/Qoder.app` 的權限

```bash
python3 -m pip install -r requirements.txt
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

## 翻譯方針

- 以 OpenCC `s2twp` 為基礎，再用 `tools/tw.py` 的台灣用語覆寫修正。
- 採用台灣常見 UI 用語：設定、檔案、資料夾、程式碼、使用者、搜尋、載入、儲存、螢幕、網路。
- `Agent`、`PR` 等開發／品牌術語保留英文。
- 伺服器下發的活動文案（例如「1024｜创造力集结」）只有英文／簡中版本，不在本補丁的翻譯範圍。

## 已知限制

- Qoder 更新會覆蓋補丁，更新後需要重新產生並套用。
- Ad-hoc 重簽可能讓 macOS 再次詢問 Keychain／TCC 權限。
- 部分遠端文案、活動頁或新功能字串可能不在翻譯檔中。
- 本補丁針對 0.4.11 的檔案結構與雜湊；其他版本請先確認再使用。

## 免責聲明

本專案與 Qoder 官方無關，不提供任何保證。修改應用程式與重新簽章有其風險，請務必先備份。Qoder 的商標、UI 文字與其他內容屬其權利人；本專案不散布 Qoder 的二進位檔或原始碼，翻譯資料僅用於介面在地化。

## 授權

程式碼採 MIT License，見 [LICENSE](LICENSE)。翻譯資料不主張對 Qoder 原始內容的權利。
