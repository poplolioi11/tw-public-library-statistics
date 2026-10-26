#!/usr/bin/env python3
"""Prepare the initial explicit source-policy review file. Never called by updates."""
import gzip,json
from pathlib import Path
import record_io
import phase2_engine as p2
ROOT=Path(__file__).resolve().parents[1]
def main():
 path=ROOT/'docs/phase3-profiles.json'
 if path.exists():raise FileExistsError('Review existing policy; never silently reseed accepted source versions')
 with gzip.open(ROOT/'derived/phase2/annotations.jsonl.gz','rt') as f:annotations=[json.loads(x) for x in f]
 families={(r['source_id'],r['source_sha256']):r['source_family'] for r in record_io.rows(ROOT)}
 contexts={}
 for a in annotations:
  k=(a['layer'],a['source_id'],a['source_sha256'])
  contexts[k]={'layer':k[0],'source_id':k[1],'source_sha256':k[2],'source_family':families.get((k[1],k[2]),'地方原工作簿來源格' if k[0]=='local_statistical_cells' else '特定計畫來源數量'),'evidence_ids':[]}
 for a in annotations:contexts[(a['layer'],a['source_id'],a['source_sha256'])]['evidence_ids'].append(a['evidence_id'])
 for c in contexts.values():c['evidence_ids']=sorted(set(c['evidence_ids']))
 profiles=[]
 def add(id,title,description,selector,mode='fixed_original_rows',purpose='source-facts',period='annual',**kw):
  profiles.append({'id':id,'title':title,'description':description,'selection_mode':mode,'default_purpose':purpose,'period_requirement':period,'candidate_filter':selector,'priority_rule':'complete original requested period coverage; qualified definition before edition for trends; never rank by value availability' if mode=='latest_original_panel' else 'fixed original source scope; no cross-family fallback or sums','curator_policy_not_official_correction':True,**kw})
 dgbas={'layer':'canonical','source_ids':['dgbas-county-library-Z091101a029']}
 add('county-library-count-dgbas','各縣市館數：主計官方改制後範圍','含國家圖書館、國資圖及國臺圖；保留1998–2005來源缺值，不把原縣市重編一次。',{**dgbas,'geo_in':['county_official_reorganized']})
 add('national-library-count-dgbas','全國館數：主計原總計','直接使用原總計，不將總計與縣市重複相加。含國家圖書館。',{**dgbas,'geo_in':['national_total'],'entity_in':['總計']})
 add('county-2023-nlpi-default','2023縣市公立館原量：國資圖預設口徑','22個原預設縣市列；不混入全國或三個不含國立館替代列。',{'layer':'canonical','source_ids':['ogdl-api-2023'],'geo_in':['county_default_includes_national_where_applicable']})
 add('national-2023-nlpi','2023全國公立館原量：國資圖','直接用原全國列；國立館範圍逐筆保留，不補成另一機關的母體。',{'layer':'canonical','source_ids':['ogdl-api-2023'],'geo_in':['national_total']})
 add('national-nlpi-chart-source-facts','國資圖歷年全國公開圖表原報值','原圖表系列逐年原報；可查單年，不因同標籤便認證歷年方法。',{'layer':'canonical','source_id_regex':r'public-chart-[0-9]{4}-.+'})
 national={'layer':'canonical','source_id_regex':r'ncl-yearbook-[0-9]+-statistics','entity_in':['全國'],'geo_in':['national_total']}
 targets=[
  ('count','館數',['圖書館數量','館數']),
  ('seats','閱覽席位',['閱覽席位','閱覽席位（席）']),
  ('book-loans','圖書借閱冊數',['圖書借閱冊數','借閱冊數','借閱冊數（冊）']),
  ('borrower-visits','圖書借閱人次',['圖書借閱人次','借閱人次','借閱人次（人次）']),
  ('ebook-loans','電子書借閱冊數',['電子書借閱冊數']),
  ('ebook-visits','電子書借閱人次',['電子書借閱人次'])]
 for suffix,label,names in targets:
  add('national-ncl-'+suffix+'-panel','國圖原刊回溯面板：'+label,'預設最新已核原刊面板；指定期間須由同一原刊完整涵蓋，不跨版補接。原刊限定對照不等於歷史方法不變。',{**national,'indicators':names},mode='latest_original_panel',purpose='trend')
 add('county-ncl-yearbook-source-facts','國圖縣市年度原量：原行政區','依原年鑑、原地名與原母體保留；比率不是原量，標籤有疑義的縣市不預設使用。',{'layer':'canonical','source_family':'國家圖書館年鑑統計事實','geo_prefix':'county'},required_geo=['county'],exclude_measures=['ratio_or_per_capita'],default_coverage_years=[2005,2024])
 add('hsinchu-monthly-circulation','新竹各館藏地逐月借還與預約原報','借閱、續借、借閱及續借等12種原欄分開；不把人次當去重人數，不把月值當全年。',{'layer':'canonical','source_ids':['local-72fc0692aa286cb0','local-3a42e4707efe4d33','local-cb74c0b328be06d4']},period='monthly')
 add('taichung-procurement-volumes','臺中原表年度採購冊數','只用已核採購冊數原欄；不將未知單位的購書經費當冊數或決算。',{'layer':'canonical','source_ids':['local-309c115c007b3086'],'indicators':['採購冊數']},purpose='trend',expected_units=['冊'])
 add('hualien-monthly-by-room','花蓮逐月按館藏地原表','原館藏地、原欄頭與總計/分項分開；所有格可看，不自行合計。',{'layer':'local_statistical_cells','source_ids':['south-hualien-library-lending-409-room']},period='monthly')
 add('hualien-monthly-by-reader','花蓮逐月按讀者分類原表','讀者類別、性別、總計與原grid分開；顯示/typed0矛盾保持缺值。',{'layer':'local_statistical_cells','source_ids':['south-hualien-library-lending-409-reader']},period='monthly')
 add('lienchiang-explicit-annual-sheet','連江有明示年度的原統計表','114原表明示年度；113僅目錄標年不能代入2024，仍列為被拒候選。',{'layer':'local_statistical_cells','source_ids':['south-lienchiang-culture-library-overview-114','south-lienchiang-opendata-173786']})
 add('programme-source-quantities','2005來源所列特定計畫數量','只及原計畫/活動與原期間，不能當年度營運量、全年讀者或去重人數。',{'layer':'programme_quantities'},period='programme',supported_purposes=['source-facts'])
 add('historical-national-dgbas-source-facts','主計歷史全國原報：單一版次','原報值與原註分開保留；趨勢須指定原指標，較新版定義矛盾不能壓過較舊合格面板。',{'layer':'canonical','source_id_regex':r'dgbas-social-indicators-[0-9]{4}'},mode='latest_original_panel',priority_source_ids=['dgbas-social-indicators-2011','dgbas-social-indicators-2008','dgbas-social-indicators-2005'],require_metric_for_trend=True)
 contract=json.loads((ROOT/'docs/phase3-contract.json').read_text())
 if {p['id'] for p in profiles}!=set(contract['profiles']):raise ValueError('Profile registry and contract differ')
 index=p2.card_index(p2.evidence_cards(ROOT));panel_keys=[]
 for layer,raw in p2.load_inputs(ROOT):
  card=index[(layer,raw['observation_id'])]
  if p2.is_reviewed(card) and p2.policy_for(raw,card)['status']=='published_panel_limited':panel_keys.append(layer+':'+raw['observation_id'])
 evidence_bindings={c['evidence_id']:__import__('hashlib').sha256(json.dumps(c,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest() for c in (json.loads(x) for x in (ROOT/'derived/phase2/evidence_cards.jsonl').read_text().splitlines())}
 for profile in profiles:
  if profile['id']=='county-ncl-yearbook-source-facts':profile['known_scope_gaps']=[{'data_year':2012,'status':'complete_22_county_core_original_quantity_table_not_obtained','partial_source_facts_not_removed':'Explicit component counts remain usable as those components; they do not fill the missing full core county table.','no_ratio_back_calculation':True}]
 policy={'schema_version':'1.0.0','policy_version':'1.0.0','reviewed_dataset_version':'0.7.0','review_method':'Explicit curator question scopes bound to existing phase2 source/evidence versions; no new raw numerical facts or historical equivalence inferred.','reviewed_sources':[contexts[k] for k in sorted(contexts)],'evidence_bindings':evidence_bindings,'reviewed_panel_record_keys':sorted(panel_keys),'panel_support_policy':'Original field/year policy support before value availability; missing values do not create or remove original panel support.','profiles':profiles,'no_value_based_ranking':True,'unreviewed_source_versions_require_review':True}
 path.write_text(json.dumps(policy,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'profiles':len(profiles),'reviewed_source_versions':len(contexts)}))
if __name__=='__main__':main()
