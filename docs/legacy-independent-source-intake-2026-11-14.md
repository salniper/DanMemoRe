# DanMemoRe｜獨立原版素材來源盤點（2026-11-14）

本頁只記錄可追溯線索和未通過的證據門檻，**不是已找回素材清單**。目前 PR #1 是 Draft，不更動 main、個人備份、AYN Thor、舊版內容或匯入安全規則。

## 正在追查的確切缺口

- 12 個現存但與 reference MD5 不符的資源：6 個 `novelCommand*.enc`、4 個 `1/master/divide_enc/*.enc`、`1/files/font/number.png` 和 `3/files/ui_atlas/home_gacha/gacha_top_move_parts_text.json`。
- Phase 3 中 1,544 個 reference 索引列有、目前公開歷史素材目錄卻沒有同路徑原圖的 `3/files/lottery/background/<ID>.png`。這一分類**不代表**所有歷史版本都無原圖。
- 既有 40 個 reference-exact 資源（33 個啟動素材 + 7 個 phase.manifest）已有獨立部分修復 ZIP v2；未取得完整 14 GB 歷史使用者資料的原版實機驗收。

## 本輪公開來源交叉查證（僅發現線索，沒有新檔案驗證）

| 線索 | 可確認資訊 | 可否作為獨立正確來源 |
| --- | --- | --- |
| 2026-09-28 Reddit [資料保存協尋討論](https://www.reddit.com/r/DanmachiMemoriaFreese/comments/1ws4zzo/does_anyone_still_have_downloaded_danmemo_game/) | 一位留言者說「據所知仍有下載完整遊戲」，另一位表示自己也在開發離線版本；但討論本文／可見回覆未給相容的 ZIP、檔案 hash、版本／區域與快取擷取日期 | **待認證**，不能列為已找回；也沒有向當事人發送訊息 |
| 討論中重貼的 [公開 Drive 備份](https://drive.google.com/drive/folders/1xqzfdevOO7ph1ppck9t8TiwzJVXpr4Yb) | 與使用者既有 14 GB 保存來源高度重疊；既有紀錄的六檔實際位元組抽驗與使用者相同，而不符合 reference MD5 | **非獨立第二套來源**；不能將鏡像重複計算 |
| [Softonic 上架的 EU 15.1.0 APK](https://danmachi-memoria-freese-kun.en.softonic.com/android) | 網頁揭示的 APK SHA-256 `36713f18a6e9fec3302384b8d67383b12761f782d73932cb62b31b230053c3b6`，與本專案已釘選、找回 33 個資源的 APK SHA-256 相同 | **同一 APK 位元組**，不是新的完整下載快取；12 個異常檔的缺口不變 |
| [APKPure EU 15.1.0](https://apkpure.net/danmachi-memoria-freese/com.eu.danmemo/download) | 顯示 `com.eu.danmemo` 15.1.0 安裝包；目前專案已對同版本可取得原版 XAPK 的六個內嵌 APK 做過 12 檔精確指紋掃描，0/12 | **安裝包不等於安裝後完整快取**；只比對前述釘選來源，不擴大為所有版本不存在 |
| [WFS 日本版官方記念 App](https://play.google.com/store/apps/details?id=com.danmemo) | Google Play 說明提供故事回顧、角色名簿等記念功能 | **不同應用／用途**，不能把日本記念版當作 EU 15.1.0 完整戰鬥與抽卡快取 |

搜尋範圍限制：上述是公開索引與討論可見資料的盤點，不代表私人 Discord、未公開備份或全部網路來源皆不存在。**本輪沒有取得新實體位元組，因此 12 個原版 MD5 缺口及 1,544 張 reference 原圖缺口都沒有下降。**

## 下次取得獨立保存候選時的最小驗證流程

1. 先確認 **EU / US / JP / TW 區域、實際 package ID、APK 版本與 SHA-256、快取大致建立日期**。特別標示是否為「完整下載後的遊戲快取」，不是單純 APK、XAPK、音樂提取包或本專案舊保存資料鏡像。
2. 先請保存者只提供**匿名檔案目錄與相關 12 個目標的相對路徑、大小、MD5**，以及 Phase 3 `lottery/background` 的數量／檔名清單。不要提供帳密、存檔、使用者 token、個人照片或裝置識別資料。
3. 若能合法取得保存者同意供比對的原始 ZIP／資料夾，在本機走現有唯讀工具：
   - `tools/verify_remaining_legacy_candidates.py --candidate-zip` 或 `--scan-candidate-zip-all-paths`（只評估 12 個）
   - `tools/assemble_reference_exact_recovery.py --candidate-zip` / `--candidate-dir`（合併 40、12、1,544 的 reference-exact 盤點；預設唯讀）
4. 僅從**完整路徑 + reference size + MD5** 完全相符的檔案建立候選；位元組命中不自動證明版本／合法來源獨立性，更不等於原版實機通過。未經認證不得跳過匯入 MD5 驗證。

## 順序與操作界線

**第一優先：取得可證明獨立的 EU 2023–2024 遊戲下載快取。** 其次才對其他區域的歷史素材做逐檔交叉驗證，禁止僅因名字相同混用。繼續保留原版劇情指令（目前 0/25 handler 驗證）、戰鬥、抽卡、存檔的獨立後續驗收。暫不增加 Preview UI。

本輪沒有聯繫社群、下載新候選、變更遊戲檔案或宣稱恢復完成。依 `AGENTS.md` 在封包實作階段尚未執行合成測試、Build、GitHub Actions 或裝置安裝。
