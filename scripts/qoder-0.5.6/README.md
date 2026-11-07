# Qoder 0.5.6 繁中補丁：安裝／還原腳本

這兩個腳本是 0.5.6 實際使用過的參考實作，內含版本、大小、`app.asar` 雜湊與 `Info.plist` 完整性雜湊檢查。

## 檔案

- `install.sh`：延後套用安裝器。用法 `install.sh [wait|now|check]`
  - `check`：只檢查暫存 App 與目前 App 狀態，不修改任何東西
  - `now`：Qoder 已結束時立即套用
  - `wait`：待命，偵測到 Qoder 完全結束後自動套用並重開
- `restore.sh`：把 `/Applications/Qoder.app` 還原成原始版

## 使用前提

1. 修改完成、已重新簽章的完整 App 暫存於：

   ```
   ~/Library/Application Support/QoderPatch/Qoder.app
   ```

2. 目前的 `/Applications/Qoder.app` 是未修改的原始 0.5.6（雜湊需與腳本內的 `ORIGINAL_ASAR_FILE` 相符）。
3. 準備好原始版備份（腳本會把目前的 App 移到 `BACKUP` 指定的位置）。

## 常數需依你的環境調整

`install.sh` 與 `restore.sh` 開頭的常數是針對 0.5.6 建置結果寫死的，換版本或重新建置後雜湊會變，請改成你自己的值：

```
BACKUP                     # 套用時原版的移動目的地
EXPECTED_VERSION           # 0.5.6
EXPECTED_ASAR_SIZE         # 補丁後 app.asar 大小
EXPECTED_ASAR_FILE         # 補丁後 app.asar SHA-256
EXPECTED_HEADER            # 補丁後 Info.plist ElectronAsarIntegrity 雜湊
ORIGINAL_ASAR_FILE         # 原始 app.asar SHA-256
```

## 自動套用（wait 模式）

若要讓安裝器在「使用者結束 Qoder 後」自動套用，可建立一個 LaunchAgent，
以 `install.sh wait` 為 `ProgramArguments`、`RunAtLoad` 為 true，路徑請用**你自己的家目錄**：

```
~/Library/LaunchAgents/com.qoder.twpatch056.plist
```

載入：

```bash
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.qoder.twpatch056.plist
```

安裝器成功後會自行移除該 LaunchAgent。此 plist 內含機器特定路徑，**請勿提交到版本庫**。
