# DanMemoRe 原版資源復原驗證｜2026-11-13

**本輪只處理原版遊戲資料，不改動 Android Preview UI。**

## 來源驗證結果

- 使用者先前提供的 19 個異常檔仍應視為原備份版本：長度與 MD5 符合使用者的稽核紀錄，但不符合新版參考目錄；不得將「檔案可解析」視為版本相符。
- 7 個 Phase Manifest 已由先前獨立修復程序生成參考 MD5 完全相符的檔案；這些修復仍需保留來源及個別驗證。
- Phase 1 另有 33 個實際缺失的檔案（LWF、標題圖、音樂、UI Atlas/網路配置等）。
- **2026-11-13 實際 CI 原版來源驗證：33/33** 個缺失項目在 SHA-1/ARM64 SHA-256 雙重固定的 EU 15.1.0 XAPK 中找到 *預期 ZIP 路徑、大小與 MD5 都完全一致* 的候選。大部分位於 `com.eu.danmemo.apk`，主題 BGM 位於 `AssetPack1.apk`。三個相同指紋的其他位置也被辨識，但**只能採用預期位置**。證據：[原版 XAPK 實測](https://github.com/salniper/DanMemoRe/actions/runs/43402296656)。
- 同一份 XAPK 的**剩餘 12 項**版本不符檔案的直接 APK 成員掃描仍是 **0/12** 參考完全相符；其中 4 個 Master、6 個 NovelCommand 密文及 2 個 UI/字型檔，**未通過原版參考 MD5**。
- Phase 3 有 **1,544 個項目沒有歷史備份目錄條目**，重新分類後確認 **1,544/1,544 全部位於 `3/files/lottery/background/`，屬於抽卡背景 PNG 的參考目錄差異**。這與上面 33 個「歷史目錄存在但檔案遺失」屬於**不同問題**，不能當作已補齊或自動算入 12 個 MD5 不符檔案。是否實際缺失檔案位元組，仍要對比完整備份。

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


## 2026-11-14｜實際擷取驗證與使用者待辦

- **使用者明確表示：尚未下載資源恢復套件**。此工作列為 **待下載**，不可在報告中改記成已交付或已安裝，不需要求睡覺中的使用者操作。
- 使用者尚未下載的檔案名稱：`DanMemoRe_Resource_Recovery_Pack_v1.zip`。本次容器已重新檢查 ZIP CRC，**11/11 成員通過**。SHA-256：`af8fd295752c57aff28d796e9b3ad719cb2d6766a99c2c7251e2775e1c3d8dfc`；套件含 7 份已驗證 Manifest、來源索引及缺口報告，**不含 33 個原始素材位元組**。
- 新的 [原版 GitHub CI 實際擷取結果](https://github.com/salniper/DanMemoRe/actions/runs/43489490766)：**33/33 素材從雙重鎖定雜湊的 EU 15.1.0 XAPK 擷取到私有暫存資料夾，再逐檔驗證落盤 MD5；合計 3,323,167 bytes**。工作完成後暫存資料夾清除，不發佈原版素材的 Actions Artifact。這項成果證實工具可實際恢復原版檔案，但並不表示使用者的 14GB 備份或 AYN Thor 已恢復。
- 新的 [`tools/restore_bootstrap33_pinned_local.py`](../tools/restore_bootstrap33_pinned_local.py) 提供使用者端一鍵來源取得與安全預驗證。預設唯讀；**只有主動加上 `--apply` 才會建立全新的 33 檔案 overlay**。傳送至掌機前仍需要使用者確認。
- 再核對使用者提供的 19 份異常檔與原始稽核 JSON：**19/19 實際大小及 MD5 等於稽核登載的 actual 值**；其中 7 個 Manifest 已以獨立修復檔比對通過，剩餘 12 個對目標 reference MD5 依然不符。這只能證明檔案與稽核一致，不能推斷其內容可用或符合目標版本。
- **剩餘主要阻塞**：12 個 reference 雜湊不符（4 Master、6 NovelCommand、2 視覺素材）；1,544 個 Phase 3 抽卡背景目錄差異仍未以使用者完整備份實體逐檔核對；原版遊戲尚未可玩。

本機自動復原範例（在 DanMemoRe repo 根目錄，且輸出路徑原本不存在）：

```sh
# 只下載並驗證來源，不更動原始遊戲資料
python3 tools/restore_bootstrap33_pinned_local.py \\
  --index data/legacy-bootstrap-reference-33.json \\
  --output /path/to/new-bootstrap33-overlay

# 需使用者允許才可真的建立 33 檔案 overlay
python3 tools/restore_bootstrap33_pinned_local.py \\
  --index data/legacy-bootstrap-reference-33.json \\
  --output /path/to/new-bootstrap33-overlay \\
  --apply
```

注意：XAPK 來源是第三方下載鏡像，而非可驗證的發行者伺服器；必須同時通過事先固定的原版封裝 SHA-1 與原始 ARM64 native SHA-256，才能採用檔案。
