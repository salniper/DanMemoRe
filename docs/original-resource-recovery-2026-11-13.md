# DanMemoRe 原版資源復原驗證｜2026-11-13

**本輪只處理原版遊戲資料，不改動 Android Preview UI。**

## 來源驗證結果

- 使用者先前提供的 19 個異常檔仍應視為原備份版本：長度與 MD5 符合使用者的稽核紀錄，但不符合新版參考目錄；不得將「檔案可解析」視為版本相符。
- 7 個 Phase Manifest 已由先前獨立修復程序生成參考 MD5 完全相符的檔案；這些修復仍需保留來源及個別驗證。
- Phase 1 另有 33 個實際缺失的檔案（LWF、標題圖、音樂、UI Atlas/網路配置等）。
- **2026-11-13 實際 CI 原版來源驗證：33/33** 個缺失項目在 SHA-1/ARM64 SHA-256 雙重固定的 EU 15.1.0 XAPK 中找到 *預期 ZIP 路徑、大小與 MD5 都完全一致* 的候選。大部分位於 `com.eu.danmemo.apk`，主題 BGM 位於 `AssetPack1.apk`。三個相同指紋的其他位置也被辨識，但**只能採用預期位置**。證據：[原版 XAPK 實測](https://github.com/salniper/DanMemoRe/actions/runs/43402296656)。
- 同一份 XAPK 的**剩餘 12 項**版本不符檔案的直接 APK 成員掃描仍是 **0/12** 參考完全相符；其中 4 個 Master、6 個 NovelCommand 密文及 2 個 UI/字型檔，**未通過原版參考 MD5**。
- Phase 3 有 **1,544 個項目沒有歷史備份目錄條目**。這與上面 33 個「歷史目錄存在但檔案遺失」屬於**不同問題**，不能當作已補齊或自動算入 12 個 MD5 不符檔案。

## 可以安全恢復的部分

來源索引僅包含 33 個對應檔案的預期大小與 MD5：
[`data/legacy-bootstrap-reference-33.json`](../data/legacy-bootstrap-reference-33.json)。

讀取原版 XAPK 的來源驗證器：
[`tools/audit_original_xapk_bootstrap33.py`](../tools/audit_original_xapk_bootstrap33.py)。

將 33 個檔案恢復至**本機全新資料夾**：
[`tools/stage_original_xapk_bootstrap33.py`](../tools/stage_original_xapk_bootstrap33.py)。

```bash
# 先唯讀檢查；輸出路徑必須尚不存在
python3 tools/stage_original_xapk_bootstrap33.py \
  --xapk /path/to/pristine-EU-15.1.0.xapk \
  --index data/legacy-bootstrap-reference-33.json \
  --output /path/to/new-bootstrap33-overlay

# 再自行授權套用；只在上述新資料夾建立 33 個來源精確檔案
python3 tools/stage_original_xapk_bootstrap33.py \
  --xapk /path/to/pristine-EU-15.1.0.xapk \
  --index data/legacy-bootstrap-reference-33.json \
  --output /path/to/new-bootstrap33-overlay \
  --apply
```

輸入原版 XAPK 必須先通過預定 SHA-1 `37894ddb200914278a5f8780e0c6e3da2d750b7c` 與原始 ARM64 `libapp.so` 的 SHA-256 `e49a8cc7991f8946365a28aebad605ce566b034826dd4b34a982ab18b38303b3`。**其他版號不可冒用**。

匯出的是*獨立部分修復 overlay*；不是原始遊戲客戶端或完整內容包。它不能使 12 個不符的資料自動通過 MD5，更不能宣稱 1,544 個 Phase 3 條目全部找到。原版大型音樂或圖檔不放進 Git，沒有覆蓋備份或修改遊戲安裝。

## 下一個來源目標

1. 將經驗證的 33 個檔案，在使用者本機與其 7 份 Manifest overlay 分開保留並核對。
2. 對 12 個仍不符版本建立可信的原始檔來源清單，逐個比對 size+MD5；「可解密」僅供內容研究，不能當作通過參考雜湊。
3. 追查 Phase 3 的 1,544 個目錄差異：按類型和原版資產包歸類，先確認其中哪些實際缺失，不能直接推定 1,544 個檔案都不存在。

**安全界線：PR 保持 Draft；主分支、已安裝 App、完整備份及其授權資料不變；原版遊戲可玩狀態仍未驗收。**
