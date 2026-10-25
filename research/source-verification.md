> 此報告記錄公開前的完整來源工作區驗收。公開副本省略無關聯絡原檔及未確認全文授權的檔案；離線公開副本驗證另見 docs/PUBLICATION.md。

# 正式資料來源獨立回查

檢查時間：2026-10-25T12:04:42.016397+00:00。結果：**pass**，共 1,244,134 個斷言、0 項失敗。

本驗收腳本不匯入主管線或 PDF 抽取程式，也不發出網路請求。

## 全量回查範圍

核心資料 3,091 筆逐筆比對原檔 SHA-256、JSON Pointer、原始值及獨立數值解析；檢查來源網址、請求、年分、地理口徑及來源家族。
2011–2025 年 × 10 個主題的 150 份全國圖表完整列舉；2023 API 的 26 列 × 86 值欄應有 2,236 筆，與 855 筆圖表分開保留。
沒有有效 legend 的數值欄排除 30 格，其中第三欄 placeholder 30 格；其餘有效欄位沒有遺漏或重複。

## 歷史 PDF 抽查

國圖歷史表 1,269 筆檢查來源雜湊與數值解析；3 份 PDF 綁定固定雜湊。另獨立視讀 5 頁，使用固定期望值抽查 28 格，以及 36 個國立館留白格沒有變成 0。這不是全文校對。
2009 年表3是「志工→工讀生」：臺北市 1,394／33；國立中央圖書館 409／0。2010 年表4改為「工讀生→志工」：臺北市 36／1,412。原始國立中央圖書館名稱與推定對應臺灣分館名稱分欄保存。

| 年度 | 原始列名 | 指標 | PDF 視讀值 | 結果 |
|---|---|---|---:|---|
| 2009 | 臺北市 | volunteers | 1394 | pass |
| 2009 | 臺北市 | student_staff | 33 | pass |
| 2009 | 國立中央圖書館 | volunteers | 409 | pass |
| 2009 | 國立中央圖書館 | student_staff | 0 | pass |
| 2009 | 國立中央圖書館 | all_staff | 495 | pass |
| 2009 | 總計 | volunteers | 8996 | pass |
| 2009 | 總計 | student_staff | 197 | pass |
| 2009 | 總計 | all_staff | 12958 | pass |
| 2010 | 臺北市 | student_staff | 36 | pass |
| 2010 | 臺北市 | volunteers | 1412 | pass |
| 2010 | 國立中央圖書館臺灣分館 | student_staff | 0 | pass |
| 2010 | 國立中央圖書館臺灣分館 | volunteers | 367 | pass |
| 2010 | 國立中央圖書館臺灣分館 | all_staff | 444 | pass |
| 2010 | 總計 | student_staff | 324 | pass |
| 2010 | 總計 | volunteers | 8941 | pass |
| 2010 | 總計 | all_staff | 12998 | pass |
| 2009 | 國立中央圖書館 | holdings_mixed | 1528469 | pass |
| 2009 | 國立中央圖書館 | acquisition_spending | 39870245 | pass |
| 2009 | 國立中央圖書館 | physical_loans | 1235390 | pass |
| 2008 | 國立中央圖書館臺灣分館 | holdings_mixed | 1471274 | pass |
| 2008 | 國立中央圖書館臺灣分館 | acquisition_spending | 16231567 | pass |
| 2008 | 國立中央圖書館臺灣分館 | physical_loans | 946172 | pass |
| 2008 | 臺北市 | population | 2622923 | pass |
| 2008 | 臺北市 | holdings_mixed | 5437454 | pass |
| 2008 | 臺北市 | physical_loans | 9218877 | pass |
| 2010 | 國立中央圖書館臺灣分館 | holdings_mixed | 1577652 | pass |
| 2010 | 國立中央圖書館臺灣分館 | acquisition_spending | 23734466 | pass |
| 2010 | 國立中央圖書館臺灣分館 | physical_loans | 1208376 | pass |

## 整併元件全量回查

共 34,302 筆元件。地方 35 份原始 JSON，逐格核對 25,184 筆 derived 資料的原值與完整原始欄位；其 14,751 筆保留資料逐筆核對整併映射。
排除的 10,433 筆均與保留列的原始值、期間、單位、館別及地理代碼相同；保留每個語意群組的所有異值。現批異值群組 0 組，不能據此推論其他來源也沒有差異。
民國年與民國年月分別轉換參考年，但保留原年月、週期、館別，沒有填成年初／年底年度總值。館別有值時維持機構範圍，不改成縣市總量。萬與冊後綴有明確轉換規則，未在原欄寫元時不猜貨幣單位。
歷史元件 1,489 筆與 derived、PDF 雜湊回查；4 個來源未提供符號保持缺值。主計總處開放授權代碼與原授權網址保留。主計總處 PDF 內容本次沒有獨立全文轉錄比對。

最終整併 JSONL 37,393 筆，與核心及元件的 ID 集合完全相同；每筆所有原有欄位及值型別均保留，沒有整併後遺漏、重複或覆寫。

## 主計總處縣市館數整包

Z091101a029 原始 HTML 644 格與長表逐格核對，原年份×縣市完整。2006–2025 年 460 格有值；1998–2005 年 184 格官方原示「-」，保留為缺值。
包含總計與22縣市，採官方改制後縣市範圍且包含國家圖書館。整併已回查 644 筆，狀態 verified；不與其他館數序列合併。授權證據為主計總處母站廣泛宣告，套用到查詢子站的範圍推論已另標。

新增批次獨立原件證據：research/ncl-2014-independent-review.json；844格，報告SHA與目前CSV綁定。Independently fixed original PDF glyph grid and visual header/row/footnote review, not human double checking.

新增批次獨立原件證據：research/ncl-2015-independent-review.json；909格，報告SHA與目前CSV綁定。Independently fixed original PDF glyph grid and visual header/row/footnote review, not human double checking.

新增批次獨立原件證據：research/ncl-2016-independent-review.json；1040格，報告SHA與目前CSV綁定。Independently fixed original PDF glyph grid and visual header/row/footnote review, not human double checking.

新增批次獨立原件證據：research/ncl-2017-independent-review.json；1040格，報告SHA與目前CSV綁定。Independently fixed original PDF glyph grid and visual header/row/footnote review, not human double checking.

新增批次獨立原件證據：research/ncl-2018-independent-review.json；1221格，報告SHA與目前CSV綁定。Independently fixed original PDF glyph grid and visual header/row/footnote review, not human double checking.

新增批次獨立原件證據：research/ncl-2019-independent-review.json；1173格，報告SHA與目前CSV綁定。Independently fixed original PDF glyph grid and visual header/row/footnote review, not human double checking.

新增批次獨立原件證據：research/ncl-2020-independent-review.json；1250格，報告SHA與目前CSV綁定。Independently fixed original PDF glyph grid and visual header/row/footnote review, not human double checking.

新增批次獨立原件證據：research/ncl-2021-independent-review.json；1236格，報告SHA與目前CSV綁定。Independently fixed original PDF glyph grid and visual header/row/footnote review, not human double checking.

新增批次獨立原件證據：research/ncl-2022-independent-review.json；1236格，報告SHA與目前CSV綁定。Independently fixed original PDF glyph grid and visual header/row/footnote review, not human double checking.

新增批次獨立原件證據：research/ncl-2023-independent-review.json；1236格，報告SHA與目前CSV綁定。Independently fixed original PDF glyph grid and visual header/row/footnote review, not human double checking.

新增批次獨立原件證據：research/ncl-2024-independent-review.json；1236格，報告SHA與目前CSV綁定。Independently fixed original PDF glyph grid and visual header/row/footnote review, not human double checking.

新增批次獨立原件證據：research/ncl-v04-image-expectations.json；31格，報告SHA與目前CSV綁定。Explicit image selections, separate from the full glyph-grid comparisons. Gemini read three supplied original page images; primary agent also inspected them and the2020scoped-quantity page.

新增批次獨立原件證據：research/ncl-reading-2012-independent-review.json；154格，報告SHA與目前CSV綁定。Fixed original table expectations, merged growth-period review and original PDF checks.

## 四張國圖缺表的完整獨立視讀基準

新增四表 1180 個位置，包含 830 個印刷數字與 350 個留白，已對照在讀取抽取結果前建立的 PDFium 視讀基準逐格核對。這350格留白不同於原刊以符號明示的缺值，也不改為零。
原表差異保留：2008借閱人次28列加總11,946,492，印刷總計11,964,492；2009未印國立分館欄，臺中市與全國分館合計分別較可見分項多1。未補欄或改原值。

新國圖元件 17418 筆逐筆比對 derived 與 canonical 的原值、缺值狀態、館級、加總角色、期間、來源版本、頁列欄及bbox。另對2006、2007、2011、2013年的5張原件表，先依PDFium影像建立164個位置的固定期望值，再比對derived及canonical；159個數值、2個原印留白及3個明示符號均無差異。
此獨立影像抽查的母體、表頭、單位、註腳與期間依據詳見[ncl-v02-independent-image-samples.md](ncl-v02-independent-image-samples.md)及其[逐格JSON紀錄](ncl-v02-independent-image-samples.json)。這164個位置為明示範圍的抽查，並非所有新卷全格獨立轉錄；四張缺表的1180位置全量基準則另列於上一節。

## 解讀界線

公開圖表的回應內沒有年分欄；年分是原始公開年度請求的年分，不能誤稱與 API 一樣有回應內年度驗證。來源回傳 0 仍可能涉及未蒐集或系統補零。
不同來源家族與全國／縣市／國立館重疊口徑沒有相加；匹配官方原檔不代表官方原資料沒有錯。歷史 PDF 授權未確認的狀態保持不變。
各層驗收範圍與輸入雜湊見 source-verification.json；元件映射回查不等於所有歷史 PDF 全文校對。
