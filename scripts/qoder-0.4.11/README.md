# Qoder 0.4.11 參考安裝腳本

這些是開發與驗證時實際使用的腳本，**不是通用的一鍵安裝器**。它們針對 Qoder 0.4.11 的版本、雜湊與目錄結構寫死檢查，請先閱讀再執行。

| 腳本 | 用途 |
| --- | --- |
| `install.sh` | 主程式繁中版的延後套用：備份、替換 App、驗證簽章、啟動測試、失敗還原。支援 `wait`、`now`、`check`。 |
| `restore.sh` | 還原 `/Applications/Qoder.app.original-0.4.11`。 |
| `sites_tw_apply.sh` | 套用 Sites 的三個繁中檔案並重新簽章。 |
| `sites_catalog_apply.sh` | 更新 `extensions/catalog.v1.json` 的雜湊與 manifest，修正擴充套件完整性檢查。 |

## 使用前提

- Qoder 已完全結束（`⌘Q`）。`now` 模式不會自己關閉 Qoder。
- 主程式安裝器假設已有一個修改後的 App 在：

  ```
  ~/Library/Application Support/QoderPatch/Qoder.app
  ```

- Sites 安裝器假設待套用檔案在：

  ```
  ~/Library/Application Support/QoderPatch/sites_stage/
  ```

  可由專案根目錄的 `scripts/build-sites-patch.sh` 產生，再複製到上述位置。

- 本目錄**沒有**包含 LaunchAgent plist；`wait` 模式需要你自行建立 launchd job，或直接使用 `now` 模式手動套用。

## 建議順序

1. 備份 Qoder。
2. 套用主程式繁中版（`install.sh` 或其對應流程）。
3. 產生並套用 Sites 繁中檔案（`sites_tw_apply.sh`）。
4. 更新擴充套件清單（`sites_catalog_apply.sh`）。
5. 重新開啟 Qoder，選擇「繁體中文」。

每一步都有版本／雜湊檢查；若 Qoder 更新，請先更新腳本中的常數，不要直接執行。
