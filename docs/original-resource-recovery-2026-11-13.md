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

### Phase 3 抽卡背景：實體檔案核對工具已備妥

新增 [`tools/audit_phase3_lottery_background_files.py`](../tools/audit_phase3_lottery_background_files.py) 與合成資料回歸測試。在使用者完整備份可供程式讀取時，執行：

```sh
python3 tools/audit_phase3_lottery_background_files.py \\
  --audit '/path/to/danmemore_legacy_audit 3(1).json' \\
  --contents /path/to/original/contents
```

工具會針對稽核紀錄的 1,544 條 `3/files/lottery/background/*.png` 參考索引，逐檔以**實際檔案大小及 MD5**區分已驗證、缺少、版本不同或無法讀取；全程唯讀、不印出圖片內容、不移動檔案。

**目前只完成分析器與合成測試，沒有取得使用者完整 14 GB 內容目錄，因此 1,544 個檔案的實體驗證結果仍然未知。**

## 2026-11-14｜12 項異常檔的 ZIP 直接唯讀比對

- 擴充 `tools/verify_remaining_legacy_candidates.py`，新增 `--candidate-zip`；可直接讀取本機的候選 ZIP 備份，**不需解壓 14 GB 內容，也不需下載復原套件**。
- 僅允許精確的 12 個資源路徑（可選單一 `contents/` 前綴）；不接受 basename 猜測、重複目標、ZIP 內 symlink、加密成員或超出讀取上限的內容；不寫出任何原版遊戲位元組。
- 獨立 ZIP 候選仍必須逐一符合 reference size+MD5；即使 12/12 全部符合，也**不等於通過原版匯入與實機驗收**。
- 新增合成回歸測試，涵蓋參考完全一致、原備份版本不符、重複路徑、symlink、非精確路徑、索引與解壓大小限制。僅合成測試；**目前沒有取得第二份真實歷史備份，因此無新增通過驗證的原版資源**。

在 repo 根目錄（**唯讀**）使用：

```sh
python3 tools/verify_remaining_legacy_candidates.py \\
  --audit '/path/to/danmemore_legacy_audit.json' \\
  --candidate-zip '/path/to/independent-contents.zip'
```

未對 `main`、既有備份、掌機或加密素材做任何修改；PR 保留 Draft。

## 2026-11-14｜原版 XAPK 所有路徑之 size+MD5 精確搜尋

過去比對 12 個異常資源時只看 **basename**，可能遺漏裝在其他路徑的相同位元組。新版 `audit_original_xapk_asset_candidates.py` 在所有內嵌 APK 安全 ZIP 成員中以 12 個目標 reference size 篩選，再以 MD5 驗證；維持原始 XAPK SHA-1 與 ARM64 native SHA-256 的驗證門檻。列出檔名相符與**任意檔名的完全相同位元組**兩類數量，未找到的檔案不得視為已恢復。新增改名精確命中、同長不同雜湊及掃描候選上限合成測試。

本變更只在原 Draft PR 與隔離 CI 測試，沒有將私有原版位元組加入 Git、沒有修改使用者備份、沒有對 AYN Thor 安裝。原版 XAPK 執行結果以 CI 真實報告為準。

### 2026-11-14｜原版實測：全路徑內容指紋掃描結果

[GitHub Actions 原始 EU 15.1.0 XAPK 實測](https://github.com/salniper/DanMemoRe/actions/runs/43566946806) 已完成並成功驗證來源（`ORIGINAL_ARM64_VERIFIED`）。搜尋全部六個內嵌 APK 的安全 ZIP 成員，按剩餘 12 個 reference size 篩選，合計 **2 個**大小符合的 ZIP 成員進入 MD5 比對；**0/12** 目標在任意路徑找到 reference size+MD5 完全一致的檔案。原本的 basename 精確搜尋也仍是 **0/12**。

這是**實際原始安裝包 ZIP 成員**的排除結果，不是全部遊戲內容來源的否定：歷史安裝後下載的完整快取、OBB、其他 container 格式、其他版本區域仍未掃到。下一步必須取得**獨立、版本可溯源的完整遊戲快取／歷史來源**，逐項驗證 12 個目標；不可將同一份備份的鏡像認作獨立來源，也不可用這個陰性結果放寬 MD5 import gate。遊戲素材位元組沒有提交或散佈。

## 2026-11-14｜獨立完整快取來源盤點（下一輪）

- 社群公開討論：[DanMemo 資料保存協尋](https://www.reddit.com/r/DanmachiMemoriaFreese/comments/1ws4zzo/does_anyone_still_have_downloaded_danmemo_game/)（2026-09-28）。留言中一位使用者表示保存完整下載資料，**尚未提供可驗證檔案、版本或 SHA**，不得計入已恢復成果。
- 討論提供的 [公開 Google Drive 備份資料夾](https://drive.google.com/drive/folders/1xqzfdevOO7ph1ppck9t8TiwzJVXpr4Yb) 已實際唯讀檢視元資料：有 1～8 phase、`cache`、`voice_root` 等子目錄，並含 `com.eu.danmemo_2023-12-22.apk`（80,881,609 bytes）、`1/master/divide_enc`、`1/master/divide_novel_command_enc`、`1/files/font/number.png`（7,381 bytes）。這與目前專案使用的歷史公開保存來源高度重疊，**不能直接視為獨立第二套備份**；同大小更不代表 reference MD5 相符。
- 工具 `tools/verify_remaining_legacy_candidates.py` 增加 `--scan-candidate-zip-all-paths`：不解壓大型 ZIP，依稽核 JSON 的 12 個 reference size 篩選任何路徑，再比對 MD5；輸出每一個目標的完全相符檔案路徑（上限 8 個）、舊版相同位元組的命中數，**絕不更改 importer 或宣稱獨立來源已認證**。限制 ZIP entries、危險路徑、符號連結、加密及展開總位元組；包含合成拒絕測試。
- 使用方式：

```sh
python3 tools/verify_remaining_legacy_candidates.py \\
  --audit '/path/to/danmemore_legacy_audit.json' \\
  --scan-candidate-zip-all-paths '/path/to/other-preserved-cache.zip'
```

**驗證界線：** 只有取得版本、日期可溯源且與目前資料不共用同一保存副本的候選來源，才能宣稱「獨立」；即使比對出 reference MD5，也不能跳過完整匯入及 AYN Thor 真機驗收。這一輪沒有取得第二份可驗證完整快取，故剩餘 12 個維持未解決。
