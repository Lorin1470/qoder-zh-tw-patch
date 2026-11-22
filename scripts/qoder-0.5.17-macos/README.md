# Qoder CN 0.5.17 繁體中文補丁:macOS 流程

0.5.17 變更了 i18n 結構與主 bundle，0.5.13 的工具無法直接沿用。這組流程在
**macOS 15.7.7 arm64、Qoder CN 0.5.17**（`/Applications/Qoder CN.app`）上建置，
安裝器會延後到 Qoder CN 完全結束後才替換 App，並自動重開。

> Qoder CN 與國際版 Qoder 的 renderer 資源相同，只有 `out/main/electronMain.js`
> 不同。本流程以 Qoder CN 的 `app.asar` 為來源。

## 前置

```bash
python3 -m pip install -r requirements.txt   # OpenCC
( cd tools/jsparse && npm install )         # acorn
```

## 1. 解出原始資源

```bash
npx @electron/asar extract "/Applications/Qoder CN.app/Contents/Resources/app.asar" work/cn-original
# 解壓時缺少 app.asar.unpacked 的 prebuild 會回報 Unable to extract some files，可忽略
```

Sites 擴充不在 `app.asar` 內，另外複製：

```bash
mkdir -p work/0517-sites-original/dist/browser work/0517-sites-original/.qoder-app-plugin
cp "/Applications/Qoder CN.app/Contents/Resources/extensions/qoder.sites/dist/browser/view.cjs" work/0517-sites-original/dist/browser/
cp "/Applications/Qoder CN.app/Contents/Resources/extensions/qoder.sites/dist/browser/publishPreview.cjs" work/0517-sites-original/dist/browser/
cp "/Applications/Qoder CN.app/Contents/Resources/extensions/qoder.sites/.qoder-app-plugin/plugin.json" work/0517-sites-original/.qoder-app-plugin/
```

## 2. 建字典

```bash
QODER_ASSETS="$PWD/work/cn-original/out/renderer/assets" node tools/jsparse/extract_resources_0517.js
python3 tools/build_zh_tw_0517.py
node tools/jsparse/extract_sites_dict.js \
  work/0517-sites-original/dist/browser/view.cjs \
  work/0517-sites-original/dist/browser/publishPreview.cjs \
  > work/0517-dict/sites_raw.json
python3 tools/build_sites_tw_0517.py
```

`extract_resources_0517.js` 會以 acorn 執行頂層宣告，抽出 `Ye` 的 zh／zh-HK
資源；`build_zh_tw_0517.py` 以 zh-HK 為底、套用 `tools/tw.py` 的台灣用語規則，
輸出 `work/0517-dict/tw_base.json`。

## 3. 產生補丁檔

```bash
python3 tools/patch_app_files_0517.py    # → work/0517-stage/out/out/...
python3 tools/patch_sites_tw_0517.py     # → work/0517-sites-stage
python3 tools/patch_catalog_tw_0517.py   # → work/0517-sites-stage/catalog.v1.json
```

語法檢查：

```bash
for f in work/0517-stage/out/out/renderer/assets/*.js \
         work/0517-stage/out/out/main/electronMain.js \
         work/0517-stage/out/out/main/chunks/C1jqE3Um.js; do
  node --input-type=module --check < "$f" || echo "FAIL $f"
done
node --check work/0517-sites-stage/dist/browser/view.cjs
node --check work/0517-sites-stage/dist/browser/publishPreview.cjs
```

### 0.5.17 錨點

- **i18n**：`out/renderer/assets/D7G81Cst.js`；`Ye` 已含 zh-HK 與 ko-KR。
  在 `,Ae="loop.language";` 之後注入 `Ye["zh-TW"]={translation:…}`。
- **語言清單／正規化**：`UnNhyzqB.js` 的 `Oe` 與 `Xe`；設定頁下拉的值來自
  `Xe(language)`，因此只要清單含 zh-TW、`Xe` 會把 `zh-tw`／`zh-hant` 映到
  `zh-TW`，既有 UI 就會顯示與送出 zh-TW。
- **主 bundle**：`DMzt2vcU.js`（頭像選單、登入頁語言、agent builder）。
  這個檔案內嵌約兩萬筆單字 IME 字典，轉換器只處理含 **2 個以上**漢字的字串
  常值，模板文字一律轉換。
- **acorn 位移**：acorn 回報的是 UTF-16 code unit 位移，bundle 內含 emoji
  （星體字元）時必須以 UTF-16 切片，否則後續所有 range 都會錯位。
- **原生選單**：`electronMain.js` 的 `wHt`（非混淆）依系統 locale 回傳選單；
  `zh-tw`／`zh-hant`／`zh-hk`／`zh-mo` 走繁中選單。
- **主程序語言清單**：`out/main/chunks/C1jqE3Um.js` 的 `bn` 與 `Wi`。
- **Sites**：`view.cjs` 選取器 `T4`、狀態表 `gs`；`publishPreview.cjs` 選取器
  `p7`／`H7`、狀態表 `PL`。`plugin.json` 的 `title.translations` 補上
  `zh-TW: 網站`，`catalog.v1.json` 同步更新三個檔案雜湊與 manifest。

## 4. 建置暫存 App

```bash
python3 tools/build_staged_app_0517.py
# → ~/Library/Application Support/QoderPatch/Qoder CN.app
```

它會 ditto 複製已安裝的 App、用 `tools/repack_asar.py` 重打包 `app.asar`、
更新 `Info.plist` 的 `ElectronAsarIntegrity` 雜湊、換入 Sites 三檔與
`catalog.v1.json`、移除舊簽章資源，最後以 ad-hoc 重新簽章並驗證。

## 5. 套用

```bash
bash scripts/qoder-0.5.17-macos/install.sh now    # Qoder CN 必須已完全結束
# 或在 Qoder CN 內操作時，用延後套用：
bash scripts/qoder-0.5.17-macos/install.sh wait
```

`wait` 會等 Qoder CN 完全結束後自動套用並重開；失敗會自動還原。安裝器會把
原始 App 備份為 `/Applications/Qoder CN.app.pre-tw-0.5.17`。

## 6. 選語言

重開後點右上角頭像，把語言改成「**繁體中文**」；或到「設定 → 外觀 → 語言」。
左側 Sites 入口會顯示「網站」。

## 還原

```bash
bash scripts/qoder-0.5.17-macos/install.sh restore
# 狀態檢查
bash scripts/qoder-0.5.17-macos/install.sh check
```

## 已知限制

- 只涵蓋 `tools/tw.py` 有規則的台灣用語；`build_zh_tw_0517.py` 的
  `build_report.json` 會列出剩餘的簡體／港式用語（目前 79 條）。
- Qoder 更新會覆蓋補丁，更新後需重新產生並套用。
- Ad-hoc 重簽可能讓 macOS 再次詢問 Keychain／TCC 權限。
- 伺服器下發的活動文案不在翻譯範圍。