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


## 2026-11-14｜公開歷史備份之六檔實際位元組交叉驗證

**直接讀取公開 Google Drive 保存目錄中的六個原版檔案**，以檔案實際內容重新計算 MD5，再與使用者 2026-11-10 的 `danmemore_legacy_audit 3(1).json` 比對。不是只看檔名、資料夾或大小。來源根目錄：[公開 1～8 階段遊戲保存資料](https://drive.google.com/drive/folders/1xqzfdevOO7ph1ppck9t8TiwzJVXpr4Yb)。

| 實際下載的來源檔案 | Bytes | 來源 MD5 | 與使用者 actual MD5 | 與目標 reference MD5 |
|---|---:|---|---|---|
| [`1/files/font/number.png`](https://drive.google.com/file/d/10R6WbzibeaPdk4j9p84Kiwo9rjY477nG/view) | 7,381 | `6a4472aceca14d70941cf36550f8475c` | 相同 | **不同** |
| [`3/files/ui_atlas/home_gacha/gacha_top_move_parts_text.json`](https://drive.google.com/file/d/1AyGqmjguRJak07rA6FXKz0HwkPGMgZm9/view) | 4,267 | `8f9fc8481cdd78e7096d011414979214` | 相同 | **不同** |
| [`1/master/divide_enc/adventureMission.enc`](https://drive.google.com/file/d/11OBZg2uVM-9UkRM38W33cmCLOCRA45ia/view) | 3,264 | `1d2535a366dae1a9a9eea2318f9d2291` | 相同 | **不同** |
| [`1/master/divide_enc/downloadVoicePhase.enc`](https://drive.google.com/file/d/1BOkdzkeAmBs5ynNVni5_l39Amf6qilsT/view) | 480 | `fa0a993ffded0d9cc82648a190fe5c4d` | 相同 | **不同** |
| [`1/master/divide_enc/lotteryWeightGroup.enc`](https://drive.google.com/file/d/1cPDa01KZCqtyXNIOQ8K_unkRuRwwg5s8/view) | 1,824 | `2db4673d890dacec2463e74219ae8b79` | 相同 | **不同** |
| [`1/master/divide_enc/subscription.enc`](https://drive.google.com/file/d/1xg63X5Z5Qcjy-jJNez2IiIsQwVDFG-j3/view) | 8,272 | `42d7c60903489c4261ea67721ff3f1fa` | 相同 | **不同** |

**結果：6/6 與使用者原始異常備份 byte-exact 相同，0/6 符合目標 reference MD5。** 來源本身的歷史版本仍未獨立認證，所以這是同位元組重複的確證，不是可證明正確的第二份來源。這份 Google Drive 的文件 `Directory.txt` 也註明某些歷史素材可能未保留，不代表版本完整。

另外六個 `novelCommand*.enc` 未完成這種雲端實際位元組交叉驗證：雲端原版劇情目錄包含很多檔案，目前頁面清單最多只顯示首批 1,000 個，無法依此宣稱它們的 MD5。它們仍僅具有使用者自己備份已解密、結構分析的證據，**不是已修復**。

下輪應尋找與上述來源及使用者歷史備份 **不同來源且版本可追溯** 的 2023–2024 完整快取，優先六個劇情檔。任何來源必須逐項對比 size+MD5 才可進入備援候選；無法找到時不放寬 import 完整性驗證。未將下載到的原版遊戲位元組提交到 Git、發佈成 Release 或推入掌機。PR 仍 Draft。


## 2026-11-14｜Phase 3 抽卡背景實體目錄交叉查驗

此次**實際唯讀列出** [公開 EU 保存備份／Phase 3／lottery／background](https://drive.google.com/drive/folders/1ARlnZjQj3R94mZmA0T4t1FbivN-T8xQp) 的全部 705 個直屬檔案（少於清單工具單頁上限 1,000），與以下兩份可確認來源交叉比對：

1. [DanMemoRe main 的原版抽卡背景關聯資料](https://github.com/salniper/DanMemoRe/blob/main/data/danmemore-gacha-art.json)，共 2,236 個 lottery banner：692 筆 `background.source=archive`，1,544 筆 `background.source=text-fallback`。
2. 2026-11-10 使用者提供的實際稽核 JSON（`danmemore_legacy_audit 3(1).json`）：Phase 3 的 1,544 筆 `missing_from_historical_catalog` 路徑，且歷史來源 `3/project.manifest` SHA-256 `6521b16593f16e42b05d0ae13ef13b6d12b16630695e727283da7d747fcc9564`。另外直接取得並解析該公開備份的 `3/project.manifest`（8,252,359 bytes、33,325 個資產條目，450 個數字命名的抽卡背景條目），確認其版本 `4ab12a6c3f219553661ff647ae79e322`，SHA-256 與稽核綁定值相同。

**實測數量：**

| 分類 | 數量 | 證據與限制 |
|---|---:|---|
| 公開資料夾直屬檔案 | 705 | 完整列出檔名，不是影像位元組 MD5 驗證 |
| 數字命名 `<lotteryId>.png` | 702 | 只看已列出的目錄項目 |
| 對應抽卡關聯表 `archive` | **692/692 找到同名檔** | 尚未逐一下載確認 692 個檔案的參考 MD5 |
| 對應 `text-fallback`（稽核的 1,544 項） | **0/1,544 有同名實體檔** | 僅適用這份公開保存目錄；不能推論其他備份、APK 或日本版也沒有 |
| 多出的數字 PNG，未被目前抽卡關聯表使用 | **10** | 原版備份中存在，應保留、不得當成缺失素材的修復 |
| 非數字命名通用 PNG | **3** | `background.png`、`background1.png`、`background2.png` |

另外 10 個未被當前 2,236 個抽卡項目使用的原版實體圖片 ID：

`171000006, 171000007, 171000008, 171000009, 171000247, 171000248, 171000491, 171000492, 171001294, 171001295`。

**結論：** 早前把 Phase 3 的 1,544 項僅稱作「參考與舊目錄差異、實體狀況未知」，現在可以進一步確認：**這份公開保存來源確實沒有這 1,544 個相同路徑的原版圖片**，並非單純 JSON 名稱缺口；但使用者裝置的完整 14 GB `contents` 尚未掛載，因此不能宣稱已對使用者本機進行 1,544 項實體查驗，也不能宣稱這 1,544 張在世界上沒有其他留存版本。

此查驗是**目錄存在性檢查**，沒有取得新的 1,544 張圖片，也沒有宣稱逐張 MD5 完全符合；用於後續鎖定版本可追溯的**其他獨立來源**。原版復原仍優先保留原始檔案，嚴格分開「原圖」、「原圖但未被現行 banner 使用」與「生成文字替代圖」三類，不以替代圖冒充原版。本次沒有改動或安裝任何原版遊戲資料，PR 維持 Draft、不得直接合併到 main。


## 2026-11-14｜抽卡背景第二次交叉鑑證：450 / 252 / 10 分類與原位元組抽驗

**這節補充前一節的 692 張「同名檔存在」結論；不能把「同名存在」等同「原版 reference MD5 已驗證」。**

直接讀取並交叉比對：
- [Alpha 10 參考 `data/manifests/project.manifest.3`](https://github.com/salniper/DanMemoRe/blob/main/data/manifests/project.manifest.3)：34,869 個總資產，內含 **1,994** 個數字命名抽卡背景參考；
- [公開歷史 Phase 3 project.manifest](https://drive.google.com/file/d/1lrGc8FCOL59uynh-mCobP_dDmyiJjccw/view)：SHA-256 `6521b16593f16e42b05d0ae13ef13b6d12b16630695e727283da7d747fcc9564`（**與使用者原始稽核鎖定的歷史 Phase 3 SHA-256 完全一致**），33,325 個總資產，其中 450 個數字命名背景條目，另有 3 個通用背景；
- [抽卡關聯表](https://github.com/salniper/DanMemoRe/blob/main/data/danmemore-gacha-art.json)：2,236 個 lottery ID，其中 692 標記 `archive`、1,544 標記 `text-fallback`；
- [公開歷史抽卡背景實體目錄](https://drive.google.com/drive/folders/1ARlnZjQj3R94mZmA0T4t1FbivN-T8xQp)：702 個數字命名檔案、3 個通用背景（目錄中的全部 705 個直屬檔案）。

**交叉集合結果（僅針對公開保存來源）：**

| 分類 | 數量 | 鑑證結論 |
|---|---:|---|
| 實體存在，登錄於參考／歷史 Manifest，且在現行抽卡關聯表使用 | **440** | 參考 size 均等於雲端檔案 size；仍非逐檔 MD5 驗證 |
| 實體存在，登錄於 Manifest，但**未**被現行 2,236 個 banner 使用 | **10** | 原版實體素材須保留；雲端辨識的檔案格式是 WebP，檔名仍為 `.png` |
| 實體存在、現行抽卡關聯表使用，但**不在** Alpha 10 參考／歷史 Manifest | **252** | 無這份 Manifest 提供的預期 MD5；不能假稱已驗證為指定版本 |
| Alpha 10 參考 Manifest 有列出，但這份歷史目錄**不存在**的背景 | **1,544** | 對應 `text-fallback`，0 張實體命中；不代表其他獨立版本也缺少 |
| 三張通用背景 | **3** | 不屬於數字 lottery ID 圖片 |

上列數量互相可校驗：`440 + 10 = 450`（歷史 Manifest），`440 + 252 = 692`（現行 archive banner），`450 + 252 = 702`（公開實體數字命名圖片），`450 + 1544 = 1994`（Alpha 10 參考 Manifest）。

**原始檔案實際位元組抽驗：**

| 雲端來源 | 實際大小 | 實際 MD5 | 參考 MD5 / 判定 |
|---|---:|---|---|
| [`171002252.png`](https://drive.google.com/file/d/1JxsQcqbRXv-ciaiBELc-GAzZTfHIaRIf/view) | 446,475 | `ff83a06a0466ebad6039c2b7456f38a1` | **完全相同**（PNG 檔頭） |
| [`171000006.png`](https://drive.google.com/file/d/1cXl2xFgS7CmZk7ttZIFUd7-TcBlIkkMl/view) | 330,918 | `2683eb2e90ba13a4a60664f3926cdb9a` | **完全相同**（檔名為 PNG、原始檔頭實際是 `RIFF ... WEBP`） |
| [`171002068.png`](https://drive.google.com/file/d/1CJHOH8G0VjHIHHIW5g8EpIGnMtOoxwAQ/view) | 387,028 | `d7b567763bb463b05b1695bcee03b859` | **沒有** Alpha 10／歷史 Manifest 對應條目可作原版 MD5 驗收 |

注意：**這一輪是 2/450 筆已實際取得並與參考 MD5 全同，不是 450/450 全通過。** 另外一個檔案已取得內容指紋，但其是否符合其他遊戲版本原版資產仍未知。雲端目錄中，450 筆有參考的檔案大小雖全相符，也不會因此提升到 MD5 驗證。雲端 MIME 分類還指出不少 `.png` 檔案實際為 WebP；**保留原始位元組及原始路徑，不要依副檔名批次轉檔或重壓縮**，避免讓原版參考 MD5 失效。

進一步恢復仍優先處理 **6 個劇情命令、4 個 Master、2 個視覺資源**這 12 個 reference MD5 不符檔案。對另外 252 張未入 manifest 的原圖則單獨留存來源／觀察到的位元組指紋，絕不當成 1,544 張缺圖的「已修復」。使用者 14 GB 裝置備份沒有在此輪進行實體讀取，原版 import、AYN Thor、main 都沒有修改；PR 保持 Draft。


## 2026-11-14｜已在隔離工作環境實際重建 40 個 reference-exact 資源（v2）

不再只是短暫 CI 的 33 檔證據。此輪從[公開 EU 2023-12-22 原始 APK](https://drive.google.com/file/d/1KMT429Dr15OyKtWv16FumBY0CyXoi8de/view) 取得 **80,881,609 bytes** 的原始安裝包，**實際重新計算 SHA-256**，結果與獨立釘選值
`36713f18a6e9fec3302384b8d67383b12761f782d73932cb62b31b230053c3b6` 完全相同。

對照使用者 2026-11-10 的 `danmemore_legacy_audit 3(1).json`，以及已經存在於其 ChatGPT Library 的 `DanMemoRe_Resource_Recovery_Pack_v1.zip`（SHA-256
`af8fd295752c57aff28d796e9b3ad719cb2d6766a99c2c7251e2775e1c3d8dfc`）：

- **33/33 原始 Phase-1 啟動素材**：只從 SHA-pinned EU APK 中允許的 `assets/common/` / `assets/` 路徑提取，逐一比對 reference+historical MD5 及長度；不缺、不重複。合計 **3,323,167 bytes** 原版素材；
- **7/7 修復後 phase.manifest**：從舊版 47 KB 驗證套件讀取，獨立比對 19 項異常稽核內相應的 reference+historical MD5 及長度；
- 用**新名稱、非覆寫**方式實際寫入私有交付套件 `DanMemoRe_Original_40_ByteExact_Overlay_v2.zip`：**40 項 reference-exact 資源 + 2 份非遊戲位元組的說明／指紋檔**，ZIP 成品大小 **3,192,292 bytes**；
- **整包 SHA-256：** `df39400c3f664546332cb77087373249399a675b878eb460715c8a0f62b40780`；
- 封裝後重新開啟 ZIP，CRC、每項的實際資料、每項 MD5 與 40 項 SHA-256 指紋清單均通過；未將原始 APK 包入新 ZIP，且未將原版資產位元組提交 GitHub；
- `RESTORE_STATUS.json` 標示 **`original_game_import_authorized=false`**、**`original_story_battle_gacha_verified=false`**、**`owner_ayn_thor_installed=false`**，並列出 12 個尚未解決的 reference MD5 不符檔案。

**保存位置：** 生成套件已在**這次 ChatGPT 對話的隔離工作環境**建立並提供下載，不在 GitHub 程式庫，也**不表示使用者已下載、安裝或套用**。不用急著下載；未來若需重建，必須從 SHA-pinned 原始 APK + 使用者既有 reference-exact 7 Manifest 套件再逐項核驗，不能改從未驗證鏡像直接採用。

**適用範圍限制：** 這份 ZIP 是**部分原版資料獨立 overlay**，不是完整遊戲。剩下 **12 個不符 MD5 的舊備份內容**與 **1,544 項 Phase-3 缺少實體參考原圖**尚未補齊，25 個觀察到的劇情 opcode 仍然 **0/25 原版 handler 已映射**。不得將此套件當作已通過 Legacy Import、劇情、戰鬥、抽卡或 AYN Thor 真機驗收；不得覆蓋歷史 RAR、原 APK、`contents`、已安裝 App 或 `main`，PR #1 保持 Draft。


## 2026-11-14｜完整原版檔案恢復的 fail-closed 整合器（不代表遊戲已修好）

新增 [`tools/assemble_reference_exact_recovery.py`](../tools/assemble_reference_exact_recovery.py) 與 [合成安全驗證](../tools/test_assemble_reference_exact_recovery.py)。這是**只接受完整 reference-exact 輸入**的單次修復整合路徑，避免一邊找到素材、一邊錯誤宣稱已完成。

- 必須提供使用者的 2026-11-10 稽核 JSON 與已重建、全部 reference-MD5 相符的 **40 檔 v2 overlay ZIP**；會再次完整重算 33 啟動素材及 7 個 phase.manifest 的參考大小／MD5，防止舊 ZIP 被更動。
- 接受一個或多個額外 **獨立候選 ZIP**，直接掃 ZIP、不解壓整份遊戲快取。6 個劇情檔 + 4 個 Master + 2 個視覺檔，以原版的 reference **size + MD5** 跨檔名精確搜尋；1,544 張背景只接受原版稽核指出的**精確路徑**和 reference size + MD5。
- 對索引筆數、路徑穿越、壓縮成員類型、symlink、加密 ZIP、單檔大小、累計解壓讀取量設上限；任何缺失、來源位元組變動或同名錯誤都**不得**經由 `--apply` 輸出不完整成果。
- 只有 **40 + 12 + 1,544 = 1,596** 項全部通過參考指紋時，才允許產生**全新、隔離、非覆寫**的資料夾；仍須通過完整 14 GB 快取的分相匯入和原版 native 實機驗收才可稱遊戲復原。
- 不提交任何遊戲原版位元組、解密金鑰、存檔或外部 APK 到 GitHub。來源的歷史獨立性仍需另行查證，不可單靠工具輸出的 MD5 命中判定。

在持有資料的本機，只讀檢查：

```sh
python3 tools/assemble_reference_exact_recovery.py \
  --audit '/path/to/danmemore_legacy_audit.json' \
  --verified40 '/path/to/DanMemoRe_Original_40_ByteExact_Overlay_v2.zip' \
  --candidate-zip '/path/to/independent-cache-1.zip' \
  --candidate-zip '/path/to/independent-cache-2.zip'
```

取得 **全部 1,556 項新的** reference-exact 來源、確認輸出目的地尚未存在後，才考慮 `--output-dir /path/to/new-separate-overlay --apply`。任何原版 import 授權或掌機驗收都必須另行進行。

**本輪真實使用者輸入的結果：** 對 Library 內 `danmemore_19_payload.json` 重新解碼逐項對照實際稽核，並將其中 12 個異常原始位元組放進**臨時、未對外發佈**的候選 ZIP；再次查得 **reference-exact 命中 0/12**。已驗證的 40 檔 v2 package 在本輪重新逐項通過；現有輸入沒有新增的 1,544 項 PNG 位元組，所以 reference-exact 新增為 **0/1,544**。沒有產生新的完整遊戲 ZIP，沒有修改使用者原始資料、既有 v2 套件或 AYN Thor。

在本輪獨立隔離工作環境中執行純合成驗證：1,596 檔全命中時新資料夾可建立且逐檔內容正確、沒有候選時不得 staging、ZIP 內穿越路徑拒絕、40 檔 overlay 一旦遭更動即拒絕；四類案例成功。**這不等於 GitHub CI 或原版實機驗收已執行**。目前 12 個加密／視覺來源、1,544 張原圖與 25 個未映射劇情 opcode 仍未完成，原版完整戰鬥、抽卡、持續存檔亦未完成最終驗收，PR 維持 Draft。


## 2026-11-14｜原始來源驗證器的二次校核與直接目錄讀取

已唯讀審核前一輪提交的 `assemble_reference_exact_recovery.py`。此前 GitHub PR 的 4 個工作流程全綠，**但是新增整合器與其測試未納入這些 CI 工作**；不可把綠燈解釋為整合器已通過測試或遊戲已修復。

發現並修正兩項安全／來源處理缺口：

1. **基礎 40 檔的 TOCTOU 風險**：舊邏輯只在 `discover()` 驗證 40 檔，`stage_all()` 複製前若來源 ZIP 被替換或修改，可能把不符合 reference MD5 的位元組寫入新的資料夾。現在在 staging 開始前重新完整驗證 ZIP，且在寫入**每一檔**時重新檢查 size、MD5、ZIP 成員安全性與唯一性。若有變動即拒絕，失敗暫存目錄清理。
2. **不必把原始 14 GB 重新壓縮**：新增 `--candidate-dir`（可重複），支援直接從持有者現有的解壓資料夾或其 `contents/` 子資料夾按 **完整原始路徑**讀取 12 個異常檔與 1,544 張背景。只讀取稽核清單列出的相對路徑，不遍歷所有遊戲檔；拒絕可見的目錄與檔案符號連結、過大的候選與偏離 MD5 的位元組。從目錄讀取的候選於 staging 時會再次以 reference size／MD5 核驗。跨名稱搜尋仍限候選 ZIP。
3. **固定原本的兩個來源錨點**：命令列入口要求使用者 2026-11-10 的原始稽核 JSON SHA-256 `fd929c2ace550fe2b7a59dcff7294be756b29adcf81f92aadd89849b3c5c6f4c` 與此前已交付、驗證的 40 檔 v2 ZIP SHA-256 `df39400c3f664546332cb77087373249399a675b878eb460715c8a0f62b40780`；避免用任意改寫的稽核檔自行偽造「參考」雜湊。若使用者另有等價、但重新打包的 ZIP，須先另外驗證，不直接放寬 pin。

從本機已存在的原始解壓內容**只讀**檢查（不會安裝／修改掌機或原始 RAR）：

```sh
python3 tools/assemble_reference_exact_recovery.py \
  --audit '/path/to/danmemore_legacy_audit 3(1).json' \
  --verified40 '/path/to/DanMemoRe_Original_40_ByteExact_Overlay_v2.zip' \
  --candidate-dir '/path/to/extracted/contents'
```

可與 `--candidate-zip` 混用，但來源不齊時仍是 `INCOMPLETE_REFERENCE_SOURCES_NOT_IMPORTABLE`，不會產出「完整版」。不指定 `--apply` 即純唯讀，不建立任何復原目錄；取得全部 1,556 個另外缺失的 reference-exact 候選後也仍不是遊戲實機驗收。

補了四個**待執行**合成測試：40 檔在發現後被換包、對已解壓 14 GB 資料夾逐檔來源驗證、符號連結拒絕、原稽核來源錨點被更動後拒絕。依專案 `AGENTS.md` 的目前「封包尚未完成前不執行測試／Build／GitHub Actions」指示，**本輪沒有主動執行這些新增測試，也沒有執行原版遊戲或實機驗收**。提交僅為隔離 Draft PR 的修復程式碼與待執行驗證，不改 `main`、設備、原始快取或 40 檔已驗證套件。

**真實剩餘阻塞不變：** 12 個 reference-MD5 不符的檔案仍待取得正確來源；1,544 張參考抽卡原圖尚未找到；原版劇情 25 個 opcode 仍無經證實的 native handler 對應，整體戰鬥、抽卡、存檔需另行驗收。公開 Reddit 保存者的「資料完整」回覆未附可驗證檔案，不能計算為已回收成果。


## 2026-11-14｜已修正 ZIP／資料夾來源不對稱的輸出漏寫

對前一輪 `tools/assemble_reference_exact_recovery.py` 逐行來源審查，發現一個**實際邏輯缺陷**：`stage_all()` 在 `member is None`（來自 `--candidate-dir`）分支讀回了候選資料，卻把最終 reference MD5 比對、建立輸出路徑和寫入檔案三步全部放在 `else`（只給 ZIP 成員）內。因此 **資料夾來源即使在掃描階段命中，也無法正確輸出修復檔案**；不能對先前版本聲稱完成來源資料夾 staging。

現已把 `size`／`MD5` 二次比對和寫入共同移到兩個分支之後，無論來源是 ZIP 或直接解壓的 `contents`，都必須在暫存目錄寫入前與 reference size+MD5 完全一致。出錯時走原有 `try/except` 清理機制，不留半成品。既有**待執行** `test_exact_directory_contents_without_rezipping` 涵蓋成功建立 1,596 個原版路徑，另新增 `test_directory_candidate_mutated_after_discovery_is_not_staged`：候選目錄內同大小資料在掃描後變動，必須拒絕整個輸出並刪除暫存。

**環境現況：** 本次查看 ChatGPT Library 最近 4 頁（800 條清單，尚有更多頁；而且遞迴 Google Drive Library 列表受限），有原始稽核 JSON、19 檔 payload、33+7 的 40 檔 v2 overlay，但未辨識到可存取的完整 **14 GB 六分卷 RAR 或解壓後 contents**。連結的 Drive 檔名搜尋 `contents-complete`、`DanMemoRe`、`com.eu.danmemo`、`MemoriaFreese`、`danmemo` 均未找到可用檔案，**這只是目前存取／搜尋範圍內的否定，不代表使用者本機沒有備份**。因此不能執行完整 14 GB 真實素材的唯讀查驗，也不能宣稱補回 12 個版本不符檔案或 1,544 張抽卡原圖。

**本輪工作範圍：** 修正整合器程式碼＋補待執行回歸案例＋註明來源限制；遵守 `AGENTS.md`「封包實作未完成前不執行測試、建置或 GitHub Actions」要求，**沒有執行新增測試、沒有觸發手動 CI、沒有安裝 APK 或接觸使用者原始 RAR**。PR #1 仍 Draft，`main` 和裝置未動。完成全部資源來源驗證後仍需獨立通過 original runtime story/battle/gacha/save 驗收，絕不從檔案 MD5 自動推論遊戲可玩。
