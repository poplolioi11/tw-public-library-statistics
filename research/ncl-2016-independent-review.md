# 2016 年資料／106 卷年鑑獨立來源核對

結果：1,040 個指定原刊格、13 表全量比對；原值、正規化值、null／原印0／標記、資料年、原PDF頁與印刷頁、表／列／欄均吻合，現存mismatches=0。比較綁定的是修正原欄頭後的CSV，不把原欄頭問題當作數字抽取錯誤。

最新CSV SHA256：`9324654428e74e4caf3c569da07141a054bd14ca4b52d685041efa1c7b04b05a`。JSONL SHA256：`f6ae22776b34d3ef67552ed9ee2f1335b1acc8c03bacb303cfd9b5d0d8f3f51a`。逐格可重播JSON見[ncl-2016-independent-review.json](ncl-2016-independent-review.json)。

## 獨立方式與界線

先只讀官方原PDF、自己以PDFium渲染的原圖，固定欄頭／列序／必要註腳與逐格來源期待；在期待檔保存並雜湊後，才讀producer CSV。沒有讀取producer抽取器、座標設定、檢查或freeze成果來建立期待。數字由PDFium獨立字形網格按字元中心抽取；原圖確認表頭、各縣市／層級列名及全部末列。這是完整數字文字核對與原圖語義查核，沒有宣稱每個數字都經人工目視雙校。

第一次期待檔SHA：`4a3aa5d5b180386caae0db60c91ab2eef00da7edaa6e5a0ba5b9ea6ace092510`；保存在research/ncl-2016-2018-independent.private/2016-expected-frozen.private.json。

原圖讀取範圍：公共館PDF頁2, 3, 4, 5, 6, 7, 8, 9, 10；統計章PDF頁2、3、4。原圖／全文PDF僅私有，報告只含必要統計事實及定位。

## 完整範圍

|原表|類別|PDF頁|原格數|
|---|---|---|---:|
|24|level_counts|2|25|
|25|county_counts|3|207|
|26|spending|4,4|69|
|29|holdings_county|6,6|69|
|27|staff_level|4|40|
|28|holdings_level|5|50|
|30|usage|7|92|
|31|events|8|161|
|32|attendance|9|161|
|33|immigrants|10|115|
|168|stats_types_matrix|2,2,2|22|
|169|stats_basic|3|4|
|171|stats_history|4|25|

統計章只取完整公共館子群／公立公共館列及公共館近五年表。國家圖書館另一類型、大專、中小學、專門館及出版業未混入；工程計畫、個人、獎項、榜單、照片與地方個案敘述不在此次核對的核心統計範圍。

## 原值、母體與單位

數值狀態：{"reported": 971, "reported_decimal": 69}；原印0共有123格。null和0分開比較，沒有把『無』變成0。

館藏的冊、種、件及混合小計保持原單位／未知狀態，未自行換算。活動欄序按各表原圖：閱讀推廣、說故事、社教藝文、地方特色、影片欣賞、其他、小計。

2016統計171原重刊當年館數1,138；2017統計215將同一參考年更新為536*，原註明示舊值1,138更新為536。這是不同出版版本及計數範圍，不能覆寫舊值或串成未註明口徑的單一趨勢。2016類型組1,218包含私人80及閱覽室／館外站，和公立總分館數不是同一母體。

表25原住民自治區欄數字下的4格館名補述亦已原字保存並核對：桃園（復興區立圖書館）、臺中（和平區立圖書館）、高雄（高雄市桃源區圖書館、高雄市那瑪夏圖書館、高雄市茂林區圖書館）、新竹縣（1、尖石鄉立圖書館2、五峰鄉立圖書館）。換行合併，但不補標點；那瑪夏後原未印區，不自行插入。source_cell_note_raw/status與數字及cell_annotation分存，此4格文字也列於JSON原件期待。

原圖表33末欄是「活動（人數）」，PDFium原字亦相同。producer原先寫「人次」的23格已修正：metric_raw/unit_raw保留人數，unit=null，unit_status=source_heading_counting_basis_unresolved；不逕推去重人數或累計人次、沒有候選單位。23格數值及位置全不變。

basic統計表所選4數字的原列名明印「公立公共圖書館」，現在entity_raw／source_row_label_raw按原刊保存，地理範圍全國另留context。歷史25格沒有原印地理列，明標contextual_national_aggregate_inferred。我最初數字期待曾把全國這個便利context放在expected_entity_raw，已按原件分開並留修訂紀錄；數字期待未更動。

歷史五年表的館藏列原印只有「館藏量」，未印冊、件；本年5格已保留metric_raw=館藏量、unit_raw空、unit=null、unit_status=source_unit_unconfirmed_or_not_printed，沒有從單年basic的註腳硬套跨年單位。這項語義跟查在初次數字期待／比對後再次回讀原圖確認，不冒稱另有事先凍結的盲測單位期待。

9張公共館層級表原印「鄉鎮市區立圖書館」，和統計章原印「鄉鎮市立圖書館」不同；本次已按每表原字保留。2016涉及23格，2017、2018各24格；修正的是raw層級名稱及欄路徑，數值和格位不變。

## 查核者自身修訂

數字期待未因producer比對而更動。

查核者初次視讀曾懷疑2017表23山地原住民欄少「立」；隨後逐表讀取PDFium原字確認「立」實際有印，已在通知producer修改前更正此閱讀錯誤，所有9表都保留原印「立」。此錯誤沒有形成資料修改。

## 來源版本

- raw/ncl-2016/yearbook-106-public-library.pdf：SHA256 `31b1bc30322484124d69a6487f49a92ffd0d1b40c151ff18264bbacc6e53ae65`。
- raw/ncl-2016/yearbook-106-statistics.pdf：SHA256 `823e310401a6c26f206a42d12b73ab82cf92450903714dd53dfea444546db7e7`。
- raw/ncl-2016/yearbook-106-copyright.pdf：SHA256 `662424d251d49eff39f94a010c27dddcb8072a168e656272b6883d533b727340`。
- raw/ncl-2016/yearbook-106-toc.pdf：SHA256 `d55044612426bfed6c94f8e0a7ad3d789a5ca2995a64493c36f3e1adcdb05487`。

版權頁出版月分別：106卷為2018-06、107卷為2019-06、108卷為2020-09；主資料年以公共館原文105／106／107年及原表題確認。存量未明示精確日期者不自行補日期。來源PDF的完整著作授權未在此核對中確認；不公開全文PDF與影像。
