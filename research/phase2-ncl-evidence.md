# 第二階段：國圖／主計原表與定義證據

覆蓋 20,045 筆既有 canonical 觀測、54 個來源版本、212 個原表組；另含 2005 年計畫表 123 筆、2 表。
共 40 個原件 SHA 全數讀回一致；214 張 source card，實讀頁數 215。沒有重擷取或修改 canonical 數值／ID。

可允許範圍只有同一原刊回溯面板、相同原指標／實體／單位／母體／期別等維度；不能把 published_panel_limited 當歷年調查方法完全相同。每張卡附 observation_ids 與具體 field_policies。

## 主要斷點

- DGBAS 2005／2008 本版英文原註 Since 2000，與中文「1999以前」一起支持借閱／閱覽在 <=1999 與 >=2000 分段；不可跨段。
- DGBAS 2011 本版中英方向衝突：中文稱1999以前為閱覽，英文稱before1999只含借出者；沒有自行訂正，借閱欄與1999邊界保留 unresolved。這不阻止同版清楚的館數／館藏欄各自有界比較。
- DGBAS 三版都明示1998／1999年臺灣省公共館數不含分館；館數與每10萬人館數按該兩年另段。
- NCL 2016–2024 等五年回溯表只准原刊內面板；國家圖書館館內調閱註屬另一張表，不套到公共館表。
- 舊行政區不改名加總；國立館排除／另列、冊件種混合、2015活動題名／單位衝突、2016活動人數、2017子期間、2024地名疑義均保留。
- 2012閱讀報告2011–12原刊比較表只支持本報告的全國借閱量／人次；不回推出缺失縣市原量。
- 2005計畫表只有活動窗／計畫期，data_year不補2005，不當全年館務活動量。

## 完整來源表清冊

|來源|原表|資料年|原件已讀|比較狀態|證據ID|
|---|---|---|---|---|---|
|dgbas-county-library-Z091101a029|None|1998,1999,2000,2001,2002,2003,2004,2005,2006,2007,2008,2009,2010,2011,2012,2013,2014,2015,2016,2017,2018,2019,2020,2021,2022,2023,2024,2025|True|published_panel_limited|p2-ncl-9edff5297c7f6c2eeb5935c9|
|dgbas-social-indicators-2005|文化與休閒／公立公共圖書館|1991,1992,1993,1994,1995,1996,1997,1998,1999,2000,2001,2002,2003,2004,2005|True|published_panel_limited|p2-ncl-7831ca1bffee71fd9c3918d3|
|dgbas-social-indicators-2008|文化與休閒／公立公共圖書館|1993,1994,1995,1996,1997,1998,1999,2000,2001,2002,2003,2004,2005,2006,2007,2008|True|published_panel_limited|p2-ncl-5469f7758a01e9e925ac7338|
|dgbas-social-indicators-2011|文化與休閒／公立公共圖書館|1996,1997,1998,1999,2000,2001,2002,2003,2004,2005,2006,2007,2008,2009,2010,2011|True|published_panel_limited|p2-ncl-b976fbf884660dc9171ea680|
|ncl-earlier-2006-t1|1|2006|True|source_series_only|p2-ncl-a32f7eff0bfc0651fe06ba24|
|ncl-earlier-2006-t2|2|2006|True|source_series_only|p2-ncl-1d9bf751ea0ce31b0ea77c3d|
|ncl-earlier-2006-t3|3|2006|True|source_series_only|p2-ncl-9074ca4ff07aed13faf8d2b8|
|ncl-earlier-2006-t4|4|2006|True|source_series_only|p2-ncl-5c7e1f85f52b29e289a3323d|
|ncl-earlier-2006-t5|5|2006|True|source_series_only|p2-ncl-87d52da219bb78b2e2242e2e|
|ncl-earlier-2007-t1|1|2007|True|source_series_only|p2-ncl-08320fdce0b32e2ba029bfe3|
|ncl-earlier-2007-t2|2|2007|True|source_series_only|p2-ncl-52822b6986c478457c000a89|
|ncl-earlier-2007-t3|3|2007|True|source_series_only|p2-ncl-ed231c330ab104616e29f42d|
|ncl-gap-2008-t3-counts|3|2008|True|source_series_only|p2-ncl-5595aafd754941c10bf95e1b|
|ncl-gap-2008-t5-staff-services|5|2008|True|source_series_only|p2-ncl-2567794dd074793772da839b|
|ncl-gap-2009-t1-counts|1|2009|True|source_series_only|p2-ncl-1c459afe10fe27c518a61ffe|
|ncl-gap-2010-t1-counts|1|2010|True|source_series_only|p2-ncl-6e80e755c2ba003ff88725d3|
|ncl-reading-2012-t1|unlabelled-1|2011,2012|True|published_panel_limited|p2-ncl-c1889f5af1e90ce30e323272|
|ncl-reading-2012-t2|unlabelled-2|2011,2012|True|published_panel_limited|p2-ncl-6e59c8c7745f55b86231af3e|
|ncl-reading-2012-t3|unlabelled-3|2012|True|source_series_only|p2-ncl-d43069f2de7720b3a36021f5|
|ncl-reading-2012-t4|unlabelled-4|2012|True|source_series_only|p2-ncl-5cfe5623973bde3629488f4c|
|ncl-reading-2012-t5|unlabelled-5|2012|True|source_series_only|p2-ncl-e94e0e68c7c90ca18261a163|
|ncl-yearbook-100-public|3|2010|True|source_series_only|p2-ncl-1d7fa33594b38247375b30b5|
|ncl-yearbook-100-public|4|2010|True|source_series_only|p2-ncl-688773bbc3892fab5fa645f4|
|ncl-yearbook-101-public-library|19|2011|True|source_series_only|p2-ncl-3c9c487ebfb47d558e4fad9b|
|ncl-yearbook-101-public-library|20|2011|True|source_series_only|p2-ncl-54dd0d86e3d646391053eeae|
|ncl-yearbook-101-public-library|21|2011|True|source_series_only|p2-ncl-de4acd8962fce7673f2038f4|
|ncl-yearbook-101-public-library|22|2011|True|source_series_only|p2-ncl-7f7c64c0891684aca3c36989|
|ncl-yearbook-101-statistics|169|2011|True|source_series_only|p2-ncl-5d5885bc08f735992bc83d01|
|ncl-yearbook-101-statistics|170|2011|True|source_series_only|p2-ncl-e8691c9741e60f469d902db9|
|ncl-yearbook-102-operational-prose-2012|prose|2012|True|source_series_only|p2-ncl-cce362ddb2407e9300aa1432|
|ncl-yearbook-102-statistics|151|2012|True|source_series_only|p2-ncl-a680db0ca5174a540485f798|
|ncl-yearbook-102-statistics|152|2012|True|source_series_only|p2-ncl-8fb9ab39a43fe8dd2005bc5c|
|ncl-yearbook-103-public-library|31|2013|True|source_series_only|p2-ncl-33b5a54e74d30062ffae4204|
|ncl-yearbook-103-public-library|32|2013|True|source_series_only|p2-ncl-d92fd93a3552bf139789ea6a|
|ncl-yearbook-103-public-library|33|2013|True|source_series_only|p2-ncl-38380a5952158ace643693df|
|ncl-yearbook-103-public-library|34|2013|True|source_series_only|p2-ncl-02b6da931599d3712cb35016|
|ncl-yearbook-103-public-library|35|2013|True|source_series_only|p2-ncl-cbd8abb13e977fa701524376|
|ncl-yearbook-103-public-library|36|2013|True|source_series_only|p2-ncl-41cd7fe686c13f792b864a9d|
|ncl-yearbook-103-public-library|37|2013|True|source_series_only|p2-ncl-21639b5432b31622928aedf2|
|ncl-yearbook-103-public-library|38|2013|True|source_series_only|p2-ncl-bc79dd94a60c7a86f75be9b3|
|ncl-yearbook-103-public-library|39|2013|True|source_series_only|p2-ncl-1d38727c81b56a6770489a49|
|ncl-yearbook-103-public-library|40|2013|True|source_series_only|p2-ncl-46fe2cc928dc2412e94c2fdc|
|ncl-yearbook-103-statistics|154|2013|True|source_series_only|p2-ncl-75dc821314490b1ad87b570f|
|ncl-yearbook-103-statistics|155|2013|True|source_series_only|p2-ncl-c9ded4da27bfb18db45406f2|
|ncl-yearbook-103-statistics|157|2009,2010,2011,2012,2013|True|published_panel_limited|p2-ncl-e613fcf056e88ed3d76a68da|
|ncl-yearbook-104-public-library|14|2014|True|source_series_only|p2-ncl-7ae0d200d5ce37c12f8f22ac|
|ncl-yearbook-104-public-library|15|2014|True|source_series_only|p2-ncl-b1991009c4b2ab0e051c5579|
|ncl-yearbook-104-public-library|16|2014|True|source_series_only|p2-ncl-fb826b6593abadcb0b0ae6f5|
|ncl-yearbook-104-public-library|17|2014|True|source_series_only|p2-ncl-2cb3e2c53513e37b3a9e87a1|
|ncl-yearbook-104-public-library|18|2014|True|source_series_only|p2-ncl-06073d737b530495a20b9e64|
|ncl-yearbook-104-public-library|19|2014|True|source_series_only|p2-ncl-3647c77681da8d8ec6b2a4ff|
|ncl-yearbook-104-public-library|20|2014|True|source_series_only|p2-ncl-643310669696b1414a8f30c5|
|ncl-yearbook-104-public-library|21|2014|True|source_series_only|p2-ncl-555ac94b95868273dcb06a57|
|ncl-yearbook-104-public-library|22|2014|True|source_series_only|p2-ncl-c2bdccc15741f52bff4d5456|
|ncl-yearbook-104-public-library|23|2014|True|source_series_only|p2-ncl-2f92b5daeee6057dcf55595b|
|ncl-yearbook-104-statistics|199|2014|True|source_series_only|p2-ncl-21975fd02bd649b094b4d953|
|ncl-yearbook-104-statistics|200|2014|True|source_series_only|p2-ncl-15238f057a593d0793965dea|
|ncl-yearbook-104-statistics|202|2010,2011,2012,2013,2014|True|published_panel_limited|p2-ncl-68a792621e62955c206cce0f|
|ncl-yearbook-105-public-library|10|2015|True|source_series_only|p2-ncl-dc2ecf03b8c4ac7de1216738|
|ncl-yearbook-105-public-library|11|2015|True|source_series_only|p2-ncl-a2e8c16dfbfdcea611d399a8|
|ncl-yearbook-105-public-library|12|2015|True|source_series_only|p2-ncl-110b7122ca56bd2c4122f13f|
|ncl-yearbook-105-public-library|13|2015|True|source_series_only|p2-ncl-128a28621b85cc1982458e47|
|ncl-yearbook-105-public-library|14|2015|True|source_series_only|p2-ncl-958d7b464b5cf2b5b8c67d16|
|ncl-yearbook-105-public-library|15|2015|True|source_series_only|p2-ncl-61d2cbf806fd37ecb13f585c|
|ncl-yearbook-105-public-library|16|2015|True|source_series_only|p2-ncl-b17b993a3cab7912c325b1d7|
|ncl-yearbook-105-public-library|17|2015|True|source_series_only|p2-ncl-d82092e584e87341df897b5d|
|ncl-yearbook-105-public-library|18|2015|True|source_series_only|p2-ncl-f815c229bf69170aee5bac56|
|ncl-yearbook-105-public-library|9|2015|True|source_series_only|p2-ncl-cdc59cf092a95eff314f09d8|
|ncl-yearbook-105-statistics|143|2015|True|source_series_only|p2-ncl-ce553e4288ac2d80f7bcc923|
|ncl-yearbook-105-statistics|144|2015|True|source_series_only|p2-ncl-c604518217800bb482371f74|
|ncl-yearbook-105-statistics|146|2011,2012,2013,2014,2015|True|published_panel_limited|p2-ncl-4eb572d03dd7498d3eeb2320|
|ncl-yearbook-106-public-library|24|2016|True|source_series_only|p2-ncl-fff6e6918cd4097bffe41f4f|
|ncl-yearbook-106-public-library|25|2016|True|source_series_only|p2-ncl-c64e04f436a529b4d6058220|
|ncl-yearbook-106-public-library|26|2016|True|source_series_only|p2-ncl-d35705f6a8a9e882f920a60a|
|ncl-yearbook-106-public-library|27|2016|True|source_series_only|p2-ncl-19f8389d71455f05c86776f6|
|ncl-yearbook-106-public-library|28|2016|True|source_series_only|p2-ncl-44aaedf07e19dbe82132a72b|
|ncl-yearbook-106-public-library|29|2016|True|source_series_only|p2-ncl-6bfd11c08c1141e1c05a0417|
|ncl-yearbook-106-public-library|30|2016|True|source_series_only|p2-ncl-685a4a77f494a55fc8b915b9|
|ncl-yearbook-106-public-library|31|2016|True|source_series_only|p2-ncl-6593d23bcad490a77130528b|
|ncl-yearbook-106-public-library|32|2016|True|source_series_only|p2-ncl-307230b3ddef9dc005e00ac5|
|ncl-yearbook-106-public-library|33|2016|True|source_series_only|p2-ncl-b1b45c68ed9bb4e89c14bdd2|
|ncl-yearbook-106-statistics|168|2016|True|source_series_only|p2-ncl-e37889e7ad7963685829e714|
|ncl-yearbook-106-statistics|169|2016|True|source_series_only|p2-ncl-a0ce78f609e43a12816b5ef8|
|ncl-yearbook-106-statistics|171|2012,2013,2014,2015,2016|True|published_panel_limited|p2-ncl-06d4e85ecd41004b3767183f|
|ncl-yearbook-107-public-library|23|2017|True|source_series_only|p2-ncl-066da49e2b3d40413dd0aa62|
|ncl-yearbook-107-public-library|24|2017|True|source_series_only|p2-ncl-e1d9072a429679f8a0d9d875|
|ncl-yearbook-107-public-library|25|2017|True|source_series_only|p2-ncl-41bdb9e0545e19b334e091a1|
|ncl-yearbook-107-public-library|26|2017|True|source_series_only|p2-ncl-4ec0f3c34450b6f1159efc46|
|ncl-yearbook-107-public-library|27|2017|True|source_series_only|p2-ncl-1c558b686ffe10501379c1d6|
|ncl-yearbook-107-public-library|28|2017|True|source_series_only|p2-ncl-155cac9e409b5c8448e311b4|
|ncl-yearbook-107-public-library|29|2017|True|source_series_only|p2-ncl-17ab7e2c345a52350c8c4741|
|ncl-yearbook-107-public-library|30|2017|True|source_series_only|p2-ncl-498175c7027079e4fb6a1a21|
|ncl-yearbook-107-public-library|31|2017|True|source_series_only|p2-ncl-9079c7c4305e12450569e827|
|ncl-yearbook-107-public-library|32|2017|True|source_series_only|p2-ncl-8199e549e33ad1bdd5615e03|
|ncl-yearbook-107-public-library|33|2017|True|source_series_only|p2-ncl-47c91d8a202418d595c4766f|
|ncl-yearbook-107-statistics|212|2017|True|source_series_only|p2-ncl-05fd2f9297734693d872832d|
|ncl-yearbook-107-statistics|213|2017|True|source_series_only|p2-ncl-afd6eeb402713905275e9671|
|ncl-yearbook-107-statistics|215|2013,2014,2015,2016,2017|True|published_panel_limited|p2-ncl-45a8feef9ed8431984ff0d98|
|ncl-yearbook-108-public-library|14|2018|True|source_series_only|p2-ncl-7e04fb5c1315f77abd9c5cf6|
|ncl-yearbook-108-public-library|15|2018|True|source_series_only|p2-ncl-c6ebfada2b5ea30c4863150c|
|ncl-yearbook-108-public-library|16|2018|True|source_series_only|p2-ncl-fe99a4952bafec7b82e33645|
|ncl-yearbook-108-public-library|17|2018|True|source_series_only|p2-ncl-0b12192973fc09a036c10314|
|ncl-yearbook-108-public-library|18|2018|True|source_series_only|p2-ncl-51ef720964d0179a0a2e72d5|
|ncl-yearbook-108-public-library|19|2018|True|source_series_only|p2-ncl-8bc199a64ce9db562ba4c4a7|
|ncl-yearbook-108-public-library|20|2018|True|source_series_only|p2-ncl-d6bada5ce4700c545c747a32|
|ncl-yearbook-108-public-library|21|2018|True|source_series_only|p2-ncl-03272258a9fdc058e0a0bbab|
|ncl-yearbook-108-public-library|22|2018|True|source_series_only|p2-ncl-135ea0c9e606c9a02f0de0df|
|ncl-yearbook-108-public-library|23|2018|True|source_series_only|p2-ncl-354b4c0fd01146c6264364c3|
|ncl-yearbook-108-public-library|24|2018|True|source_series_only|p2-ncl-4ec5169278309daa2885e07b|
|ncl-yearbook-108-public-library|26|2018|True|source_series_only|p2-ncl-6c129fca640ef6223dd25b87|
|ncl-yearbook-108-statistics|191|2018|True|source_series_only|p2-ncl-b51724c5579a29098fba5ae8|
|ncl-yearbook-108-statistics|192|2018|True|source_series_only|p2-ncl-22b16fa16b8f500e3c3959c3|
|ncl-yearbook-108-statistics|194|2014,2015,2016,2017,2018|True|published_panel_limited|p2-ncl-0122aeb0cd63cb671b9ec075|
|ncl-yearbook-109-public-library|15|2019|True|source_series_only|p2-ncl-bd6ba2239cc079f508a0c551|
|ncl-yearbook-109-public-library|16|2019|True|source_series_only|p2-ncl-54d9fb757c960cac3c9aa6bd|
|ncl-yearbook-109-public-library|17|2019|True|source_series_only|p2-ncl-1b7ae12bdcfa1353fd9d7409|
|ncl-yearbook-109-public-library|18|2019|True|source_series_only|p2-ncl-2c6a2b91991780f89a0bc134|
|ncl-yearbook-109-public-library|19|2019|True|source_series_only|p2-ncl-2a8e7887f0470ed4281d8731|
|ncl-yearbook-109-public-library|20|2019|True|source_series_only|p2-ncl-b84df7be9bce577621d17037|
|ncl-yearbook-109-public-library|21|2019|True|source_series_only|p2-ncl-279c7a9a37ad68405dd9e711|
|ncl-yearbook-109-public-library|22|2019|True|source_series_only|p2-ncl-018e92c811020e6655aeee30|
|ncl-yearbook-109-public-library|23|2019|True|source_series_only|p2-ncl-e60e08d973bfe1e64b42290f|
|ncl-yearbook-109-public-library|24|2019|True|source_series_only|p2-ncl-2a57a02b857d49739483c5f5|
|ncl-yearbook-109-public-library|26|2019|True|source_series_only|p2-ncl-252e312da35493cec9223fb4|
|ncl-yearbook-109-statistics|205|2019|True|source_series_only|p2-ncl-a1a27ce61adc163311cf8ffc|
|ncl-yearbook-109-statistics|206|2019|True|source_series_only|p2-ncl-62b259868216e9af165cafc8|
|ncl-yearbook-109-statistics|208|2015,2016,2017,2018,2019|True|published_panel_limited|p2-ncl-2c4c7cd2cc255010be23bcc5|
|ncl-yearbook-110-public-library|10|2020|True|source_series_only|p2-ncl-6021659ca18614b8471bf8e3|
|ncl-yearbook-110-public-library|11|2020|True|source_series_only|p2-ncl-0d0cef44091eb4bc10ff35b0|
|ncl-yearbook-110-public-library|12|2020|True|source_series_only|p2-ncl-0fad8cf6c0456cfc01017447|
|ncl-yearbook-110-public-library|13|2020|True|source_series_only|p2-ncl-a71472b9e217c7ac69bf8b81|
|ncl-yearbook-110-public-library|14|2020|True|source_series_only|p2-ncl-f790bcb5805bd6ec2def9a59|
|ncl-yearbook-110-public-library|15|2020|True|source_series_only|p2-ncl-bfdedd8f8b9a2ffff7bda6e5|
|ncl-yearbook-110-public-library|16|2020|True|source_series_only|p2-ncl-36007024d9c156e71ba12999|
|ncl-yearbook-110-public-library|17|2020|True|source_series_only|p2-ncl-a6aafa8d6f6d678f28c54b93|
|ncl-yearbook-110-public-library|18|2020|True|source_series_only|p2-ncl-1ba56d7d6a8ba9df18d5afba|
|ncl-yearbook-110-public-library|19|2020|True|source_series_only|p2-ncl-f56703d32188cbbae5a75950|
|ncl-yearbook-110-public-library|22|2020|True|source_series_only|p2-ncl-f36f4750ae8cbfce6decad30|
|ncl-yearbook-110-public-library|24|2020|True|source_series_only|p2-ncl-b73a82536f3a9b8120dd170a|
|ncl-yearbook-110-statistics|186|2020|True|source_series_only|p2-ncl-6068ffac220069e803d7c2bf|
|ncl-yearbook-110-statistics|187|2020|True|source_series_only|p2-ncl-40079fdaad351f89b6290118|
|ncl-yearbook-110-statistics|189|2016,2017,2018,2019,2020|True|published_panel_limited|p2-ncl-1bbad8f6aefdebc285bac24c|
|ncl-yearbook-111-public-library|10|2021|True|source_series_only|p2-ncl-4cd6c037bd5e0f22a688a1ef|
|ncl-yearbook-111-public-library|11|2021|True|source_series_only|p2-ncl-7b7dfbb81a202f8eeb68710e|
|ncl-yearbook-111-public-library|12|2021|True|source_series_only|p2-ncl-4df18b3f2144f9c30da7b0e6|
|ncl-yearbook-111-public-library|13|2021|True|source_series_only|p2-ncl-a9f63308ab1a0939bae4a4d1|
|ncl-yearbook-111-public-library|14|2021|True|source_series_only|p2-ncl-f9a31e78f4bca79bd01941fb|
|ncl-yearbook-111-public-library|15|2021|True|source_series_only|p2-ncl-d5bf67a0813b4573f243449f|
|ncl-yearbook-111-public-library|16|2021|True|source_series_only|p2-ncl-341465ad8064010a50a9231a|
|ncl-yearbook-111-public-library|19|2021|True|source_series_only|p2-ncl-323df730b9d59f75d10524ba|
|ncl-yearbook-111-public-library|21|2021|True|source_series_only|p2-ncl-cacf8f3c3c0fcbda2eaaf3a4|
|ncl-yearbook-111-public-library|7|2021|True|source_series_only|p2-ncl-4128c9a189cdac0464a0080a|
|ncl-yearbook-111-public-library|8|2021|True|source_series_only|p2-ncl-57dd23e7136aae34ef4f976c|
|ncl-yearbook-111-public-library|9|2021|True|source_series_only|p2-ncl-421c38df071c5e3b557c7b65|
|ncl-yearbook-111-statistics|203|2021|True|source_series_only|p2-ncl-337776d04f0b93a9156610c3|
|ncl-yearbook-111-statistics|204|2021|True|source_series_only|p2-ncl-8d72a829558fcfdafea5ea20|
|ncl-yearbook-111-statistics|206|2017,2018,2019,2020,2021|True|published_panel_limited|p2-ncl-546f8ea62c8a8b39ab8c5025|
|ncl-yearbook-112-public-library|10|2022|True|source_series_only|p2-ncl-3add0073f92ccc0f31476fd4|
|ncl-yearbook-112-public-library|11|2022|True|source_series_only|p2-ncl-0f15e471c5820d03c61ebeb7|
|ncl-yearbook-112-public-library|12|2022|True|source_series_only|p2-ncl-51c0896f8c2753054a74eb89|
|ncl-yearbook-112-public-library|13|2022|True|source_series_only|p2-ncl-a2da7e252cbe123047c05388|
|ncl-yearbook-112-public-library|14|2022|True|source_series_only|p2-ncl-c770c77b0b42b8ab02c922ae|
|ncl-yearbook-112-public-library|15|2022|True|source_series_only|p2-ncl-c93bda4a5aa5230ec34ea519|
|ncl-yearbook-112-public-library|16|2022|True|source_series_only|p2-ncl-b38199432c4ffecf71d3c780|
|ncl-yearbook-112-public-library|17|2022|True|source_series_only|p2-ncl-7eebc934afa257ca87a540fc|
|ncl-yearbook-112-public-library|18|2022|True|source_series_only|p2-ncl-435e039881fe9587c0991cf2|
|ncl-yearbook-112-public-library|19|2022|True|source_series_only|p2-ncl-900665c3a45f7ca15dcf256a|
|ncl-yearbook-112-public-library|21|2022|True|source_series_only|p2-ncl-7478b78b51ff8f850b103ec3|
|ncl-yearbook-112-public-library|23|2022|True|source_series_only|p2-ncl-16fc13470486bf845ba2efce|
|ncl-yearbook-112-statistics|164|2022|True|source_series_only|p2-ncl-03eb6b24274fc11135e760c1|
|ncl-yearbook-112-statistics|165|2022|True|source_series_only|p2-ncl-8334f738c0ff175c13401380|
|ncl-yearbook-112-statistics|167|2018,2019,2020,2021,2022|True|published_panel_limited|p2-ncl-dc85e48d30414ecc6e7a7c4f|
|ncl-yearbook-113-public-library|10|2023|True|source_series_only|p2-ncl-8ca6e99f216ae6ee52b0303e|
|ncl-yearbook-113-public-library|11|2023|True|source_series_only|p2-ncl-35dfd575ea5f046c8235bcf9|
|ncl-yearbook-113-public-library|12|2023|True|source_series_only|p2-ncl-5aa62afed529942adb01dda9|
|ncl-yearbook-113-public-library|13|2023|True|source_series_only|p2-ncl-70617eef32b614f387e15331|
|ncl-yearbook-113-public-library|14|2023|True|source_series_only|p2-ncl-65314718b0010e7f2aa81a4c|
|ncl-yearbook-113-public-library|15|2023|True|source_series_only|p2-ncl-f6bdc2eaac209cfbe5ce9b08|
|ncl-yearbook-113-public-library|16|2023|True|source_series_only|p2-ncl-1686770706794559da71d33a|
|ncl-yearbook-113-public-library|17|2023|True|source_series_only|p2-ncl-204156fd46a7c41d759c2a82|
|ncl-yearbook-113-public-library|20|2023|True|source_series_only|p2-ncl-da5df6e78722074aa104f35e|
|ncl-yearbook-113-public-library|22|2023|True|source_series_only|p2-ncl-b92151db7e4962e63676dbd0|
|ncl-yearbook-113-public-library|8|2023|True|source_series_only|p2-ncl-36f7ca18894b0bc4f2dc3026|
|ncl-yearbook-113-public-library|9|2023|True|source_series_only|p2-ncl-958014e6bbb8aa1668025818|
|ncl-yearbook-113-statistics|194|2023|True|source_series_only|p2-ncl-8cfeb86e43895c114eac43e3|
|ncl-yearbook-113-statistics|195|2023|True|source_series_only|p2-ncl-bc749f05ec02281ed213d020|
|ncl-yearbook-113-statistics|197|2019,2020,2021,2022,2023|True|published_panel_limited|p2-ncl-f563fa024ed2e07058cf1e61|
|ncl-yearbook-114-public-library|10|2024|True|source_series_only|p2-ncl-93ae5880b0e136cefb97236d|
|ncl-yearbook-114-public-library|11|2024|True|source_series_only|p2-ncl-ce34715444f0d7eb6dcad152|
|ncl-yearbook-114-public-library|12|2024|True|source_series_only|p2-ncl-6ddcb6ad288ab85e0bd03bb7|
|ncl-yearbook-114-public-library|13|2024|True|source_series_only|p2-ncl-15fb18ecca098b8d9fb64d4c|
|ncl-yearbook-114-public-library|14|2024|True|source_series_only|p2-ncl-6fa786d196c6b5d1a02c05b5|
|ncl-yearbook-114-public-library|15|2024|True|source_series_only|p2-ncl-03a674052fb1d6818bffd304|
|ncl-yearbook-114-public-library|16|2024|True|source_series_only|p2-ncl-9ed3b906220b579320543b09|
|ncl-yearbook-114-public-library|19|2024|True|source_series_only|p2-ncl-b592a30df8fc7d5eccb21edc|
|ncl-yearbook-114-public-library|21|2024|True|source_series_only|p2-ncl-ed629488127c5779cd1b3bd7|
|ncl-yearbook-114-public-library|7|2024|True|source_series_only|p2-ncl-25ab05da000f818fad032475|
|ncl-yearbook-114-public-library|8|2024|True|source_series_only|p2-ncl-33357b814f2dbd99e80bf716|
|ncl-yearbook-114-public-library|9|2024|True|source_series_only|p2-ncl-7712a17b911e760a460e31b6|
|ncl-yearbook-114-statistics|192|2024|True|source_series_only|p2-ncl-9b6e6d26a2339625eeeb4405|
|ncl-yearbook-114-statistics|193|2024|True|source_series_only|p2-ncl-89b4fe139ceb6a89fe0b4856|
|ncl-yearbook-114-statistics|195|2020,2021,2022,2023,2024|True|published_panel_limited|p2-ncl-0ab8d6ea4d4299c60e356a7e|
|ncl-yearbook-95-public-library|1|2005|True|source_series_only|p2-ncl-71ae54d32958b5b820c4d7ed|
|ncl-yearbook-95-public-library|2|2005|True|source_series_only|p2-ncl-d015af50e4d60503c5be6350|
|ncl-yearbook-95-public-library|3|2005|True|source_series_only|p2-ncl-c13ced1d148250f9f73859d8|
|ncl-yearbook-95-public-library|4|2005|True|source_series_only|p2-ncl-6de3edf84aa409ac86bb1d62|
|ncl-yearbook-95-public-library|5|2005|True|source_series_only|p2-ncl-b3ce8058573f6e131ccd2438|
|ncl-yearbook-95-public-library-programmes|6||True|source_series_only|p2-ncl-6b2eb17a0fa5c8a998131f47|
|ncl-yearbook-95-public-library-programmes|7||True|source_series_only|p2-ncl-2d74df3b75d55e1f94b8af21|
|ncl-yearbook-95-statistics|107|2005|True|source_series_only|p2-ncl-4786668e226e2322b1751662|
|ncl-yearbook-95-statistics|108|2005|True|source_series_only|p2-ncl-f53cc5896b3afd0e3f8c359f|
|ncl-yearbook-98-public|4|2008|True|source_series_only|p2-ncl-a638ff3cd90210311ed26c58|
|ncl-yearbook-99-public|2|2009|True|source_series_only|p2-ncl-1905f5f2c9e734486a215bbe|
|ncl-yearbook-99-public|3|2009|True|source_series_only|p2-ncl-d2a42c7323e2f465186f391d|

## 驗收

```json
{
  "canonical_records": 20045,
  "canonical_source_ids": 54,
  "canonical_table_groups": 212,
  "programme_records": 123,
  "programme_table_groups": 2,
  "source_cards": 214,
  "physical_originals": 40,
  "original_PDFs": 39,
  "original_HTMLs": 1,
  "original_pages_text_read": 215,
  "reviewed_original_cards": 214,
  "pending_original_cards": [],
  "comparison_status_counts": {
    "published_panel_limited": 18,
    "source_series_only": 196
  },
  "all_selected_observation_ids_covered_once": true,
  "canonical_values_or_IDs_modified": false
}
```

重跑：`python scripts/phase2_ncl_source_audit.py`。原PDF與原HTML只讀；私人的整頁render不在公開JSON。四張關鍵頁已背景render後視覺覆核，其他卡的method精確標為原PDF文字／原HTML查讀，沒有冒稱每頁皆做圖像判讀。
