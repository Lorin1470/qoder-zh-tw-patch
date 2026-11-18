# Qoder 0.5.13 繁中補丁:Windows 安裝流程

0.5.13 的 i18n chunk(`C4HI_h4X.js`)與 Sites 擴充和 0.5.12 完全相同;主 bundle
改為 `DB5RheoM.js`(issueDrawer `B2t`、projectBoard `MBt`),原生選單函式改為
`NLx`。工具為 `tools/*_0513.py`,輸出全部放在 `work/`(不再用 `/tmp`),
Windows 與 macOS 皆可執行產生階段。

以下流程在 **Windows 10 x64、Qoder Desktop 0.5.13** 實機驗證。

## 前置

```bash
python -m pip install -r requirements.txt   # OpenCC
( cd tools/jsparse && npm install )         # acorn
```

## 1. 解出原始資源

```bash
npx @electron/asar extract "%LOCALAPPDATA%/Programs/Qoder/resources/app.asar" work/0513-original
```

## 2. 抽取字串並建字典

```bash
node tools/jsparse/extract_resources_0513.js   # → work/0513-dict/new_zh.json 等
python tools/build_zh_tw_0513.py               # → work/0513-dict/tw_base.json 等
# Sites 字典與 0.5.12 相同(Sites 擴充位元組相同):
cp work/0512-dict/sites_tw.json work/0512-dict/sites_tw_annot.json work/0513-dict/
```

## 3. 產生補丁檔

```bash
python tools/patch_app_files_0513.py    # → work/0513-stage/out
python tools/patch_sites_tw_0513.py     # → work/0513-sites-stage
python tools/patch_catalog_tw_0513.py   # → work/0513-sites-stage/catalog.v1.json
```

語法檢查(renderer 與 main 皆為 ESM):

```bash
for f in work/0513-stage/out/out/renderer/assets/*.js work/0513-stage/out/out/main/electronMain.js; do
  node --input-type=module --check < "$f" || echo "FAIL $f"
done
node --check work/0513-sites-stage/dist/browser/view.cjs
node --check work/0513-sites-stage/dist/browser/publishPreview.cjs
```

## 4. 套用(Qoder 必須完全結束)

```bash
python tools/install_win_0513.py apply
```

安裝器會:

1. 驗證版本 0.5.13、Qoder 已結束
2. 備份 `app.asar`、`Qoder.exe`、`catalog.v1.json` 與 Sites 三檔到
   `%LOCALAPPDATA%/QoderPatch/backup-0.5.13`(含原始 SHA-256 紀錄)
3. 用 `tools/repack_asar.py` 重打包
4. **更新 Qoder.exe 內嵌的 asar header 雜湊**:Windows 版 Electron 的
   `EnableEmbeddedAsarIntegrityValidation` fuse 已啟用,雜湊以
   `[{"file":"resources\\app.asar","alg":"SHA256","value":"<hash>"}]`
   形式嵌在 exe 資源區;新舊雜湊同為 64 字元,直接等長置換即可。
   這會使 exe 的 Authenticode 簽章失效,但 Windows 不強制驗證,可正常啟動。
5. 換入 Sites 三檔與 `catalog.v1.json`

若不方便手動關閉 Qoder(例如 Agent 在 Qoder 內執行),可用延後套用:

```bash
python tools/install_win_0513.py wait
```

它會等 Qoder 完全結束(最多 30 分鐘)後自動套用並重開;套用失敗會自動還原。
建議以獨立(detached)行程啟動,以免跟著 Qoder 一起被結束。

## 5. 還原

```bash
python tools/install_win_0513.py restore
```

## 6. 選語言

重開後到「**設定 → 外觀 → 語言**」選「**繁體中文**」。左側 Sites 入口顯示「站點」。

## 與 macOS 流程的差異

- 沒有 `Info.plist`、codesign、公證票據問題;改的是 exe 內嵌雜湊。
- 路徑預設為 `%LOCALAPPDATA%/Programs/Qoder/resources`,可用環境變數
  `QODER_RESOURCES` 覆寫(安裝器與 Sites/catalog 工具皆支援)。
- 0.5.13 的 `electronMain.js` 是 ESM,語法檢查要用 `--input-type=module`。

## 已知限制

- Qoder 自動更新會覆蓋補丁,更新後需重跑流程(錨點依版本而異)。
- 修改 exe 會破壞數位簽章;介意者請先備份並自行評估。
- 伺服器下發文案不在翻譯範圍。