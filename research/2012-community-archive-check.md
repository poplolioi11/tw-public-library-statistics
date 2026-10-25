# g0v/twstat的2012年公共館資料有限查核

查核時間：2026-10-25T10:44:37.143918+00:00。只查公開GitHub API／HTTP，沒有clone、批量爬取官方網站、擷取樣本入庫、改canonical或發布。

本輪在完整tree檔名、縣市CSV索引及教育文化PX指標列表中，**只見「公立公共圖書館個數」**。該CSV確含2012年的22縣市館數，但未見館藏、購書、借閱、圖書館人力的完整全縣市核心表。這是有限查核結果，不能稱整庫所有歷史分支或每個townPX都沒有。

g0v已做過主計縣市PX與CSV整理，應引用及評估再利用；現有館數與本專案已取得的主計館數系列高度重疊，尚未逐格認證同一版本，本輪不重造或新增入庫。

- 凍結tree：[git tree 85d76b84e49e49d04ef530fdf8de7b44a1e8cdb9](https://github.com/g0v/twstat/tree/85d76b84e49e49d04ef530fdf8de7b44a1e8cdb9)，4,759項，API回覆truncated=false。
- [README](https://github.com/g0v/twstat/blob/85d76b84e49e49d04ef530fdf8de7b44a1e8cdb9/README.md)列出原官方縣市PXWeb來源；[main.ls](https://github.com/g0v/twstat/blob/85d76b84e49e49d04ef530fdf8de7b44a1e8cdb9/main.ls)記錄主計抓取流程及1998–2014的設定。
- [縣市CSV索引](https://github.com/g0v/twstat/blob/85d76b84e49e49d04ef530fdf8de7b44a1e8cdb9/csv/county/index/index.json)只有上述圖書館館數項；[館數CSV](https://github.com/g0v/twstat/blob/85d76b84e49e49d04ef530fdf8de7b44a1e8cdb9/csv/county/index/公立公共圖書館個數.csv)實際年序列1998–2014（README的1998–2011描述已過時）。
- [舊分類索引](https://github.com/g0v/twstat/blob/85d76b84e49e49d04ef530fdf8de7b44a1e8cdb9/old/county/index.json)指出14.px為教育文化；讀取其後續raw14-1／14-2的指標列表，只見館數。原PX題為「【改制後】縣市重要統計指標」，不能把它當當年原行政區界線。

GitHub API回覆repo未設archived，但最後push為2016-10-15；這是**社群歷史快照，並非現行官方供應**。原官方來源鏈為README的`ebas1.ebas.gov.tw/pxweb/Dialog/statfile9.asp`與程式的`statdb.dgbas.gov.tw/pxweb/dialog/CityItemlist_n.asp`；本輪沒有重抓這些舊端點。

[MIT-LICENSE](https://github.com/g0v/twstat/blob/85d76b84e49e49d04ef530fdf8de7b44a1e8cdb9/MIT-LICENSE)明確對Software授權；README另將data歸其原權利人，沒有明確把所有政府原資料都授權MIT。尚未建立原始版本的下載／再公開授權鏈，不能把程式MIT直接套到整個歷史資料庫。本輪只記查重與來源，不再公開資料。

詳查閱[查核JSON](2012-community-archive-check.json)。沒有逐一下載4,759個blob、遍查commit／branch歷史或整合全部地方townPX，因此未見不等於不存在。
