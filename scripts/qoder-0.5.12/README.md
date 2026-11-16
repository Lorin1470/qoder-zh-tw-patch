# Qoder 0.5.12 繁中補丁：產生與套用流程

以下流程在 macOS arm64 實機驗證（Qoder Desktop 0.5.12）。所有步驟假設你在 Qoder 完全結束前完成「產生」，置換 App 時 Qoder 必須不在執行。

## 前置

```bash
python3 -m pip install -r requirements.txt   # OpenCC
( cd tools/jsparse && npm install )          # acorn
```

## 1. 解出原始資源

```bash
npx @electron/asar extract /Applications/Qoder.app/Contents/Resources/app.asar work/0512-original
```

解包對 `app.asar.unpacked` 中不存在的他平台 prebuild 會報錯，`out/` 有完整解出即可。

## 2. 抽取 zh／zh-HK 原始字串並建字典

```bash
node tools/jsparse/extract_resources_0512.js   # → work/0512-dict/new_zh.json 等
python3 tools/build_zh_tw_0512.py              # → work/0512-dict/tw_base.json 等
```

## 3. 產生補丁檔

```bash
python3 tools/patch_app_files_0512.py    # → /tmp/qoder_asar_0512/out（主程式＋chunks＋選單＋splash）
python3 tools/patch_sites_tw_0512.py     # → work/0512-sites-stage（Sites 擴充）
python3 tools/patch_catalog_tw_0512.py   # → work/0512-sites-stage/catalog.v1.json
```

若官方又改版，`patch()` 會在任何錨點找不到時直接報錯，不會產出半套補丁。

## 4. 重打包 ASAR

```bash
python3 tools/repack_asar.py \
  --src /Applications/Qoder.app/Contents/Resources/app.asar \
  --root /tmp/qoder_asar_0512/out \
  --out /tmp/qoder_asar_0512/app.asar \
  --replace out/main/electronMain.js out/renderer/index.html \
    out/renderer/assets/C4HI_h4X.js out/renderer/assets/CAGvh22m.js \
    out/renderer/assets/Cc0Q_zSB.js out/renderer/assets/DnRI3XG6.js \
    out/renderer/assets/Dta6yTTQ.js out/renderer/assets/DonN8_qu.js \
    out/renderer/assets/BicF1FJE.js out/renderer/assets/ozSfTnrI.js \
    out/renderer/assets/D1eLu6vA.js
```

輸出的 `header_hash` 要寫進 `Info.plist`。

## 5. 暫存、換入、簽章（Qoder 結束時執行）

1. `ditto /Applications/Qoder.app "$HOME/Library/Application Support/QoderPatch/Qoder.app"`
2. 以重打包的 `app.asar` 覆蓋暫存 App
3. `PlistBuddy -c "Set :ElectronAsarIntegrity:Resources/app.asar:hash <header_hash>"` 更新完整性雜湊
4. 刪除 `Contents/CodeResources`
5. 換入 `work/0512-sites-stage` 的 `view.cjs`、`publishPreview.cjs`、`plugin.json` 與 `catalog.v1.json`
6. 以原 App 的 entitlements 做 ad-hoc 重簽：

```bash
codesign -d --entitlements :- /Applications/Qoder.app > /tmp/ent.plist
codesign --force --deep --sign - --entitlements /tmp/ent.plist --options runtime "$STAGED"
codesign --verify --deep --strict "$STAGED"
```

7. 備份原版後把暫存 App 移到 `/Applications/Qoder.app`，`lsregister -f` 刷新，重開 Qoder。

## 6. 選語言

「設定 → 外觀 → 語言 → 繁體中文」。原生選單列（檔案／編輯／顯示／視窗）會同步成繁中。

## 已知限制

- Qoder 每次自動更新都會整包覆蓋補丁（官方簽章驗證會失敗或直接換新），更新後需重跑本流程；錨點與雜湊依版本而異。
- Ad-hoc 重簽可能讓 macOS 重新詢問 Keychain／輔助使用權限。
