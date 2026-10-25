# -*- coding: utf-8 -*-
import json,csv,hashlib,collections,datetime
from pathlib import Path
p=Path(__file__).resolve().parents[1]
m=json.loads((p/'derived/local_historical_metadata.json').read_text());rows=list(csv.DictReader((p/'derived/local_historical_long.csv').open()))
verified_docs=0;original_records=[]
for d in m['documents']:
 if d['status']!='downloaded':continue
 b=(p/d['raw_path']).read_bytes();assert hashlib.sha256(b).hexdigest()==d['source_sha256'];raw=json.loads(b.decode('utf-8-sig'));assert len(raw)==d['row_count'];verified_docs+=1
 original_records.extend((d,i,r) for i,r in enumerate(raw,1))
assert len(rows)==m['summary']['long_rows']
for r in rows:
 orig=json.loads(r['original_fields'])
 assert r['value_raw']==str(orig['數值'] if '數值' in orig else orig[r['metric_raw']])
 assert r['period_effective']
 assert r['metric_group_raw'] or r['metric_raw']
 assert r['conflicting_values']=='false'
assert 'Set-Cookie' not in (p/'derived/local_historical_metadata.json').read_text()
assert 'set-cookie' not in (p/'derived/local_historical_metadata.json').read_text()
unique=[r for r in rows if not r['duplicate_of']]
h=[r for r in unique if r['county']=='新竹市']
periods=sorted({r['period_raw'] for r in h})
assert {f'{y:03d}{month:02d}' for y in range(105,115) for month in range(1,13)} <= set(periods)
assert {f'115{month:02d}' for month in range(1,9)} <= set(periods)
monthly={}
for r in h:monthly.setdefault(r['period_raw'],set()).add(r['facility_raw'])
coverage=[]
for year in sorted({s[:3] for s in periods}):
 ps=[s for s in periods if s.startswith(year)];locations=[len(monthly[s]) for s in ps]
 rr=[r for r in h if r['period_raw'].startswith(year)]
 coverage.append({'roc_year':int(year),'ce_year':int(year)+1911,'months':ps,'observed_month_count':len(ps),'location_categories_per_month_min':min(locations),'location_categories_per_month_max':max(locations),'unique_long_rows':len(rr)})
checks=0;arithmetic_errors=[];seen=set()
for d,source_row,orig in original_records:
 if not '新竹市' in d['source_title']:continue
 key=json.dumps(orig,ensure_ascii=False,sort_keys=True)
 if key in seen:continue
 seen.add(key)
 for total,a,b in [('借閱及續借人次','借閱人次','續借人次'),('借閱及續借冊數','借閱冊數','續借冊數')]:
  try:
   vals=[int(str(orig[k]).replace(',','')) for k in [total,a,b]]
  except (KeyError,ValueError):continue
  checks+=1
  if vals[0]!=vals[1]+vals[2]:arithmetic_errors.append({'period':orig.get('統計年月'),'location':orig.get('館藏地'),'total_field':total,'values':vals,'source_id':f'local-{d["dataset_id"]}-{d["resource_index"]:02d}','source_url':d['source_url'],'source_download_url':d['source_download_url'],'source_sha256':d['source_sha256'],'source_locator':f'JSON array[{source_row-1}]'})
audit={'checked_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'verified_raw_documents':verified_docs,'verified_long_rows':len(rows),'unique_long_rows':len(unique),'exact_duplicate_long_rows':len(rows)-len(unique),'source_conflict_groups':m['summary']['conflicting_value_groups'],'hsinchu_unique_long_rows':len(h),'hsinchu_period_count':len(periods),'hsinchu_distinct_location_categories':len({r['facility_raw'] for r in h}),'hsinchu_period_coverage':coverage,'hsinchu_arithmetic_checks':checks,'hsinchu_arithmetic_errors':arithmetic_errors,'scope_warning':'location categories include reading rooms and micro library; not a count of physical libraries. Every observed month is present for 105–114; this does not prove all expected facilities reported each month.'}
(p/'derived/local_historical_quality.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n')
lines=['# 地方公共圖書館歷年整包：範圍、來源與查核','',f'查核時間：{audit["checked_at"]}。完成 14 個明確 OGDL 目錄所列全部 JSON 資源，35 份原檔、2,333 原始列，展開為 25,184 個長表值。保留 10,433 個重複來源觀測並填 duplicate_of；排除重複後 14,751 個觀測，其中新竹市 14,400 個。所有原檔雜湊、原始列數及長表原值已逐筆讀回核對。','', '這份成果完整的是「下列特定目錄的公開資源包及新竹已觀察到的跨年月序列」，不是全臺所有年份、所有館別已完成。','', '## 已完整取得的目錄','', '| 目錄 | 範圍與口徑 | 本次處理 |','|---|---|---|']
for ds in m['catalogues']:
 docs=[d for d in m['documents'] if d['dataset_id']==ds['dataset_id']]
 count=sum(d.get('row_count',0) for d in docs if d['status']=='downloaded')
 periods_ds=sorted({r['period_raw'] for r in rows if r['source_url']==ds['source_url'] and r['period_raw']})
 span=f'{periods_ds[0]}–{periods_ds[-1]}' if periods_ds else '以資源標題期間另記，原始列未列年度'
 lines.append(f'| [{ds["dataset_id"]} {ds["source_title"]}]({ds["source_url"]}) | {span} | {len(docs)}/{len(ds["resources"])} 份 JSON；{count} 原始列 |')
lines+=['','目錄 130199 是循新竹年度目錄實際「相關資料集」連結發現的累積檔，沒有猜年度網址。它的 1,152 列包含 10412 至 11504；其他明列年度檔延伸至 11508。113、112 等分年檔與累積檔大量重疊，全部來源保留後逐觀測去重。','', '## 新竹完整年月覆蓋','', '| 民國年 | 西元年 | 已觀察月份數 | 每月館藏地類別數範圍 | 去重後觀測值 |','|---|---|---|---|---|']
for c in coverage:lines.append(f'| {c["roc_year"]} | {c["ce_year"]} | {c["observed_month_count"]} | {c["location_categories_per_month_min"]}–{c["location_categories_per_month_max"]} | {c["unique_long_rows"]} |')
lines+=['','105–114 年逐年皆包含 1–12 月，115 年目前取得 1–8 月，另有 104 年 12 月。12 種觀測指標是借閱、續借、還書、預約、取消預約與借閱及續借的人次／冊數；曾出現 12 種館藏地類別，含閱覽室、視聽室、微型圖書館等，不能說成 12 間實體圖書館，也不能把「人次」改成人數。月份齊全不證明每月所有應填館別都已填報；館藏地類別歷年會變。','',f'新竹原始資料去重後 {len(seen)} 個館藏地×月份列，執行 {checks} 次「借閱＋續借＝合計」原欄位算術核對，發現 {len(arithmetic_errors)} 次不一致；細節列於 derived/local_historical_quality.json。這項檢查與原值忠實轉換不能證明政府原始填報全部正確。','', '## 期間、重複與版本','', '- period_raw 完整保留檔內期間。臺中106/107分館檔內無年度，以確切資源標題另記 period_catalog_hint、period_effective_basis；沒有用目錄更新時間冒充觀測時間。','- 新竹114年度目錄目前資源實為115年月資料；依檔內「統計年月」處理，保留目錄標題差異，不把它硬改成114年。','- 年報、月報、分館借閱及購書資料分別保留原項目、原週期與來源，不硬接成同一口徑。臺中部分月份未在目錄出現，不補零、不推估，也不聲稱連續全月。','- duplicate_of 鍵含縣市、有效期間、原週期、館藏地、原項目、原欄位、原單位及原值；去除非空 duplicate_of 可移除已確認的重複來源觀測。目前同一觀測鍵的異值群為0；未來若 conflicting_values=true，不應只去重就把相異版本加總。','- 每列保留完整 original_fields、官方目錄、下載 URL、原檔 SHA-256、取得時間與 JSON 陣列定位。','', '## 授權與已解決的下載障礙','', '- 14 個目錄皆同時確認可見政府資料開放授權條款第1版及 JSON-LD 授權連結 https://data.gov.tw/license 。授權判斷只及明列資源，不泛用到未列的 NLPI API 年份或申請限用資料。','- 新竹站最初9份憑證鏈驗證失敗；依站方葉憑證 AIA 所列 http://sslserver.twca.com.tw/cacert/Cyber_SSL_2023.crt 取得中繼憑證，以 certifi 受信任根驗證鏈成功後補鏈。連線的憑證與主機名稱驗證一直開啟。證據在 raw/official-local/tls/verification.json；目前35份均已成功下載，最初失敗不能解讀為沒有資料。','', '## 更新失敗時保留既有成果','', '- 平常執行 scripts/fetch_local_history.py 讀取已驗證快取，不重抓成功資源；主代理規劃地方歷史來源每90天重新查核。','- --refresh 若目錄或資源失敗，使用先前雜湊仍有效的成功版本，保留觀測值並標 freshness=stale_after_failed_check、last_check_error；不以 failed 空結果刪掉舊值。沒有既有成功版本時才保留明確缺口。','- 原檔與 metadata 以雜湊命名留不可變 revision，另追加 revisions.jsonl；相同SHA的source_retrieved_at保留該內容首次取得時間，last_checked_at另記複查；不同SHA新增內容版本，不以純時間更新產生假的觀測版本。公開 manifest 只留 Content-Type、Content-Length、Last-Modified、ETag、Content-Disposition、Cache-Control，排除 Set-Cookie 等非必要 HTTP headers。','- 已完成5個離線回歸測試：更新失敗保留完整長表與版本、雜湊已損壞快取不能冒充成功、沒有前版則如實回報失敗、相同SHA保留首次取得時間、不同SHA保留前版原檔與metadata。沒有為測試重新聯網。','', '## 尚未取得／不納入的來源','', '- 國資圖舊開放資料清單 https://www.nlpi.edu.tw/OpenData/gov?PageIndex=7 有公共圖書館統計列，標示2018/01/16；其 TXT/XML/JSON/URL 連結本輪都404，沒有將上架日充成資料年度，也沒有取得「每個舊年度皆OGDL」證據。主站自訂開放宣告不自動套用另一統計系統網域。','- SEGIS 官方目錄背景 HTTP 已完整讀取，列民國95–114全國縣市公立公共圖書館數；其前端腳本本輪兩次逾時，尚未取得底層產品與個別授權，未猜下載API。這是未完成取得，不是未公開。','- 國網歷史鏡像有臺中舊月報線索，本輪直接讀取逾時；data.g0v.ronny.tw、dataportal.asia 本機TLS名稱不匹配，未繞過驗證。','- 臺南120735實際是熱門書前20名資料，不是縣市整體圖書館概況，未為增加數量而匯入。','- 停止擴大搜尋；本輪聚焦完成新竹跨年系列與上述臺中已確認整包。其他縣市及年度缺口不等於沒有資料。','']
(p/'research/local-history.md').write_text('\n'.join(lines),encoding='utf-8')
print(json.dumps({'verified_raw_documents':verified_docs,'verified_long_rows':len(rows),'unique_long_rows':len(unique),'hsinchu_period_count':len(periods),'arithmetic_checks':checks,'arithmetic_exceptions':len(arithmetic_errors)},ensure_ascii=False))
