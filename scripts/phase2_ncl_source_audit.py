#!/usr/bin/env python3
"""Read retained NCL/DGBAS originals; build bounded definition evidence, no values.

Never edits canonical records, source metadata or originals. Positive scopes are
within one published source/table/printed metric; they are not harmonisation.
"""
from __future__ import annotations
import argparse,collections,datetime,hashlib,json,re,unicodedata
from html.parser import HTMLParser
from pathlib import Path
from pypdf import PdfReader

ROOT=Path(__file__).resolve().parents[1]
DIMENSIONS=['measure','unit','collection_type','stock_flow_ratio_financial','period_resolution','population','national_library_scope','geography_vintage','institutional_level','aggregation_role','source_edition','age_sex_reader_classification']
VISUAL_CHECKS={
 'dgbas-social-indicators-2005':{'pages':[107],'finding':'English note explicitly says Since 2000; full page rendered and visually read.'},
 'dgbas-social-indicators-2008':{'pages':[133],'finding':'English note explicitly says Since 2000; full page rendered and visually read.'},
 'dgbas-social-indicators-2011':{'pages':[2],'finding':'English note says before 1999, opposite in direction to Chinese note; full page visually confirmed.'},
 'ncl-yearbook-106-statistics':{'pages':[4],'finding':'Tables 170 and 171 visually separated; note limiting NCL borrowing to onsite request belongs to table170, not table171.'},
}
def digest(b):return hashlib.sha256(b).hexdigest()
def compact(s):return re.sub(r'\s+','',unicodedata.normalize('NFKC',str(s or '')))
def values(rows,key):return sorted({str(r.get(key)) for r in rows if r.get(key) not in (None,'')})
def textvals(v):return v if isinstance(v,str) else json.dumps(v,ensure_ascii=False,sort_keys=True)
def clean_snip(s,n=240):return ' '.join(str(s).split())[:n]

class HTMLText(HTMLParser):
 def __init__(self):super().__init__(convert_charrefs=True);self.parts=[];self.skip=0
 def handle_starttag(self,t,a):
  if t in ('script','style'):self.skip+=1
  if t in ('td','th','tr','div','p','br'):self.parts.append('\n')
 def handle_endtag(self,t):
  if t in ('script','style'):self.skip=max(0,self.skip-1)
 def handle_data(self,d):
  if not self.skip:self.parts.append(d)

def printed_block(text,table):
 if not str(table).isdigit():return text,'page_context_no_numeric_table_label'
 pat=re.compile(r'(?m)^\s*表\s*'+re.escape(str(table))+r'(?!\d)')
 found=list(pat.finditer(text))
 if not found:return text,'page_context_continuation_or_unlocated_table_label'
 start=found[-1].start();next_table=re.search(r'(?m)^\s*表\s*\d+',text[found[-1].end():])
 end=found[-1].end()+next_table.start() if next_table else len(text)
 return text[start:end],'printed_table_label_to_next_table_label'

def flagged(r,words):
 return any(x in ' '.join(str(r.get(k) or '') for k in ('quality_flags','entity_label_status','unit_status','geographic_scope','period_basis','source_period_interpretation_status')) for x in words)

def field_selector(rows):
 return {'series_ids':values(rows,'series_id'),'indicators':values(rows,'indicator'),'source_fields':values(rows,'source_field')}

def policy(rows,reason,locator,segments=(),unresolved_years=(),status='unresolved',**extra):
 return {'selector':field_selector(rows),'observation_ids':sorted(r['observation_id'] for r in rows),
  'year_segments':[sorted(set(x)) for x in segments if x],'unresolved_years':sorted(set(unresolved_years)),
  'status':status,'reason':reason,'source_locator':locator,**extra}

def main():
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=ROOT);a=p.parse_args();root=a.root.resolve()
 contract_path=root/'docs/phase2-contract.json';contract=json.loads(contract_path.read_text())
 canonical_path=root/'data/combined/observations.jsonl';canonical_bytes=canonical_path.read_bytes()
 allrows=[json.loads(x) for x in canonical_bytes.decode().splitlines()]
 rows=[r for r in allrows if r['source_id'].startswith(('ncl','dgbas'))]
 for r in rows:r['_layer']='canonical_quantitative'
 programme_path=root/'derived/ncl_2005_programmes_long.jsonl';programmes=[json.loads(x) for x in programme_path.read_text().splitlines()]
 for r in programmes:
  r['_layer']='programme_quantities';r['source_snapshot_path']=r['source_local_path'];r['source_field']=r.get('source_column_path') or r.get('metric_raw');r['indicator']=r.get('metric_raw');r['geography']=r.get('county_raw')
 grouped=collections.defaultdict(list)
 for r in rows+programmes:grouped[(r['source_id'],str(r.get('source_table')),r['_layer'])].append(r)
 paths={r['source_snapshot_path']:r['source_sha256'] for r in rows+programmes};originals={};readers={};page_cache={}
 for path,expected in paths.items():
  f=root/path;b=f.read_bytes();actual=digest(b);assert actual==expected,('source_sha_mismatch',path)
  if b.startswith(b'%PDF'):readers[path]=PdfReader(f)
  else:
   q=HTMLText();q.feed(b.decode('utf-8',errors='replace'));page_cache[(path,None)]=''.join(q.parts)
  originals[path]={'source_sha256':actual,'bytes':len(b),'kind':'PDF' if path in readers else 'HTML','read_sha_verified':True}
 def page(path,n):
  k=(path,n)
  if k not in page_cache:page_cache[k]=readers[path].pages[n-1].extract_text() or ''
  return page_cache[k]
 cards=[]
 for (sid,table,layer),items in sorted(grouped.items()):
  path=items[0]['source_snapshot_path'];pages=sorted({int(r['source_pdf_page']) for r in items if r.get('source_pdf_page') is not None})
  # Page context is separate from the specific printed table block. Adjacent
  # notes are never automatically transferred to a different table.
  blocks=[];loc=[]
  for n in pages:
   s=page(path,n);bl,method=printed_block(s,table)
   if len(bl.strip())<=20 and len(s.strip())>20:
    bl=s;method='whole_original_page_context; heading_follows_data_in_text_order; no_table_exclusive_block_claim'
   blocks.append(bl)
   loc.append({'pdf_page':n,'printed_pages':sorted({str(r.get('source_printed_page')) for r in items if r.get('source_pdf_page')==n and r.get('source_printed_page') is not None}),'table_block_method':method,'page_text_sha256':digest(s.encode()),'table_label_detected':method=='printed_table_label_to_next_table_label'})
  if not pages:blocks=[page(path,None)];loc=[{'html_locator':'#dataTable; td.fvalue[effect=Z091101a029][date][area] and original note after table'}]
  joined='\n'.join(blocks);all_page_text='\n'.join(page(path,n) for n in pages) if pages else joined
  normalized=compact(all_page_text);blocknorm=compact(joined)
  years=sorted({r['data_year'] for r in items if isinstance(r.get('data_year'),int)})
  fields=values(items,'source_field');indicators=values(items,'indicator');units=values(items,'unit');notes=[]
  # Only an original footnote string actually found in the retained source
  # pages is admitted as original-note evidence. Commentary remains separate.
  for raw_note in values(items,'source_footnotes_raw'):
   for sentence in re.split(r'(?<=[。；])',raw_note):
    if len(compact(sentence))>=8 and compact(sentence) in normalized:
     n={'text':clean_snip(sentence),'match_method':'NFKC_and_whitespace_only_literal_match_to_original_page','source_locator':loc}
     if n['text'] not in {x['text'] for x in notes}:notes.append(n)
  # Printed-year validation for national retrospective tables. Values are not
  # re-extracted; only the printed table's period labels are checked.
  roc=[y-1911 for y in years];sequence=''.join(map(str,roc))
  explicit_year_header=(len(years)>1 and (sequence in blocknorm or (str(roc[0])+'年至'+str(roc[-1])+'年') in blocknorm or sid.startswith('dgbas-') and all(str(y) in normalized for y in years)))
  reading_panel=sid in ('ncl-reading-2012-t1','ncl-reading-2012-t2') and years==[2011,2012] and all(str(x) in normalized for x in (100,101))
  ncl_panel=sid.endswith('-statistics') and explicit_year_header and len(years)>1
  dgbas_panel=sid.startswith('dgbas-') and len(years)>1
  panel=ncl_panel or reading_panel or dgbas_panel
  eid='p2-ncl-'+digest((sid+'|'+table+'|'+layer).encode())[:24]
  facts={'measure':{'retained_indicator_labels':indicators,'raw_source_fields':fields,'original_field_literal_matches':[f for f in fields if compact(f) and compact(f) in normalized]},'unit':{'raw_units':values(items,'unit_raw'),'retained_units':units,'unit_statuses':values(items,'unit_status'),'rule':'retain original; no scaling or conversion to pure book counts'},
   'collection_type':{'source_collection_labels':[i for i in indicators if any(w in i for w in ('館藏','圖書','期刊','非書','電子'))],'complete_definition_effective_years_confirmed':False},
   'stock_flow_ratio_financial':{'retained_temporal_kinds':values(items,'temporal_kind'),'definition_rule':'stock, flows, ratios and financial amounts remain separate'},
   'period_resolution':{'data_years_present':years,'raw_periods':values(items,'period_raw'),'period_basis':values(items,'period_basis'),'printed_multi_year_header_confirmed':bool(explicit_year_header or reading_panel)},
   'population':{'retained_population_scope':values(items,'population_scope'),'evidence_scope':'source statements are listed without treating vague metadata as harmonised definition'},
   'national_library_scope':{'retained_source_qualifiers':values(items,'national_libraries_scope'),'cross_source_equivalence_confirmed':False},
   'geography_vintage':{'raw_geography_labels':values(items,'geography'),'retained_vintage':values(items,'geography_vintage'),'recoding_permitted':False},
   'institutional_level':{'retained_labels':values(items,'institutional_level')},'aggregation_role':{'retained_roles':values(items,'aggregation_role'),'totals_and_components_additive':False},
   'source_edition':{'edition_labels':values(items,'source_edition'),'roc_editions':values(items,'source_edition_roc'),'publication_years':values(items,'publication_year'),'publication_dates':values(items,'publication_date'),'data_year_is_not_publication_year':True},
   'age_sex_reader_classification':{'age_labels':values(items,'age_group_raw'),'sex_labels':values(items,'sex_raw'),'original_row_labels_not_assumed_reader_class':values(items,'source_row_label_raw'),'cross_year_classification_equivalence_confirmed':False}}
  unresolved=['本卡沒有認證歷年填報方法、回應完整率或定義生效日完全相同。','不能跨來源版本覆寫、接續或以同名欄位視作同口徑。']
  if any(r.get('unit') is None for r in items):unresolved.append('部分單位未定；同一原刊面板許可不能繞過unknown-unit檢查。')
  if not notes:unresolved.append('未在本卡引用到可逐字匹配的表專屬註腳；不從相鄰表或當代字典補定義。')
  fp=[];breaks=[]
  geo_bad=[r for r in items if flagged(r,('geography_label_alignment','county_source_label_uncertain','duplicate_printed_geography_label_unresolved'))]
  if geo_bad:
   fp.append(policy(geo_bad,'既有來源審查的地名／欄位對齊疑義，在回讀原頁後保留；不新訂正地名。',loc,unresolved_years=[r['data_year'] for r in geo_bad if r.get('data_year')],dimension='geography_vintage',evidence_kind='existing_source_review_flag_preserved_after_original_page_readback'))
   breaks.append({'kind':'unresolved_original_geography_label','observation_ids':sorted(r['observation_id'] for r in geo_bad),'reason':'原地名疑義不以現行縣市名稱改正。','source_locator':loc})
  if any(x in values(items,'geography') for x in ('臺北縣','臺中縣','臺南縣','高雄縣','桃園縣')):
   breaks.append({'kind':'historical_geography','labels':[x for x in values(items,'geography') if x.endswith('縣')],'reason':'原行政區原名；不等同現行導航，不合併舊縣市。','source_locator':loc})
  conflict=[r for r in items if flagged(r,('unit_conflict','title_unit_conflict','counting_basis_unresolved','display_typed_value_conflict'))]
  if conflict:
   fp.append(policy(conflict,'原單位／題名／計量基礎有衝突或未定，不能以欄名相同解鎖比較。',loc,unresolved_years=[r['data_year'] for r in conflict if r.get('data_year')],dimension='unit'))
  if sid=='ncl-yearbook-105-public-library' and table=='17':
   context=page(path,4);quote='各縣市辦理推廣活動共9萬643場、參與人次1,715萬1,036人，詳如表16及表17。';assert compact(quote) in compact(context)
   notes.append({'text':quote,'source_locator':{'pdf_page':4,'printed_page':'62','section':'（六）推廣活動辦理情形'},'match_method':'literal_original_chapter_context_not_a_silent_unit_correction'})
   fp.append(policy(items,'表17題名印辦理場次，章內正文卻列參與人次並指表16/17；只保留人次候選，正式單位仍未知，不能替原題訂正。',{'pdf_pages':[4,7],'table':'17','chapter_section':'（六）推廣活動辦理情形'},unresolved_years=[2015],dimension='measure_and_unit'))
  if sid=='ncl-yearbook-106-public-library' and table=='33':
   people=[r for r in items if '活動（人數）' in str(r['indicator'])]
   assert compact('活動（人數）') in normalized
   notes.append({'text':'活動（場次）／活動（人數）','source_locator':{'pdf_page':10,'table':'33','location':'最後兩欄欄頭'},'match_method':'original_printed_header_readback; slash_separates_the_two_labels'})
   fp.append(policy(people,'原欄為活動（人數）；是否去重或其實人次未明，不當其他年份活動人次。',loc,unresolved_years=[2016],dimension='counting_basis'))
  subperiod=[r for r in items if 'subperiod' in str(r.get('period_basis')) or r.get('source_period_interpretation_status')]
  if subperiod:
   if sid=='ncl-yearbook-107-public-library' and table=='33':
    for quote in ('公務機關（1/1-/8/31）','行政法人（9/1-12/31）'):
     assert compact(quote) in normalized
     notes.append({'text':quote,'source_locator':{'pdf_page':16,'table':'33','location':'高雄市備註列'},'match_method':'literal_original_row_note_readback'})
   fp.append(policy(subperiod,'原列為公務機關／行政法人子期間，或日期標點未解；不當全年。',loc,unresolved_years=[r['data_year'] for r in subperiod if r.get('data_year')],dimension='period_resolution',raw_periods=values(subperiod,'period_raw')))
  # DGBAS version-specific breakpoints. Do not silently fix the 2011 English.
  if sid.startswith('dgbas-social-indicators-'):
   ed=int(sid.rsplit('-',1)[-1]);count_rows=[r for r in items if r['indicator'] in ('家數','每10萬人圖書館數')];borrow=[r for r in items if r['indicator']=='圖書借閱人數'];ratio=[r for r in items if r['indicator']=='圖書館利用率']
   count_segments=[[y for y in years if y<=1997],[y for y in years if y in (1998,1999)],[y for y in years if y>=2000]]
   fp.append(policy(count_rows,'本版原註明1998及1999年臺灣省公共館不含分館；只在各段內保留原刊比較。',loc,segments=count_segments,status='published_panel_limited',dimension='population_and_institution',excluded_cross_segment_pairs=True))
   breaks.append({'kind':'branch_inclusion_break','selector':field_selector(count_rows),'year_segments':count_segments,'unresolved_years':[],'reason':'原註1998、1999年臺灣省公共圖書館不含分館。','source_locator':loc})
   cn='1999以前，圖書館借閱人數之定義為閱覽人數。'
   if ed in (2005,2008):
    en='Since 2000, number of readers only included those who borrowed books out of libraries.'
    enpage=107 if ed==2005 else 133;assert compact(en) in compact(page(path,enpage))
    seg=[[y for y in years if y<=1999],[y for y in years if y>=2000]]
    fp.append(policy(borrow,'保留中文1999以前；本版英文Since2000明示起點，支持<=1999／>=2000分段，不能跨段。',{'pdf_pages':[enpage-1,enpage],'notes':['中文註','English note']},segments=seg,status='published_panel_limited',dimension='measure',boundary_year_resolution='resolved_by_same_edition_English_since_2000',original_notes=[cn,en]))
    if ratio:fp.append(policy(ratio,'利用率原公式及分母未在本次原表列明；不能僅由借閱欄自動補有效定義。',loc,unresolved_years=years,dimension='ratio_definition'))
    notes.append({'text':en,'source_locator':{'pdf_page':enpage,'note':'English borrowing definition'},'match_method':'exact_source_text_and_rendered_visual_review'})
   else:
    en='Number of readers only included those who borrowed books out of libraries before 1999.';assert compact(en) in compact(page(path,2))
    fp.append(policy(borrow,'本版中文稱1999以前為閱覽人數，英文卻稱before1999只含外借者；方向衝突，不自行訂正。',{'pdf_pages':[1,2],'notes':['中文⑤','English⑤']},unresolved_years=years,status='unresolved',dimension='measure',boundary_year_unresolved=[1999],original_notes=[cn,en]))
    if ratio:fp.append(policy(ratio,'原利用率公式／分母未明且借閱定義中英衝突；不由標籤推其有效定義。',loc,unresolved_years=years,dimension='ratio_definition'))
    unresolved.append('2011本版借閱人數中英定義方向矛盾，1999邊界不由其他版本代改。')
    notes.append({'text':en,'source_locator':{'pdf_page':2,'note':'English⑤'},'match_method':'exact_source_text_and_rendered_visual_review'})
   # Chinese note and branch exclusion are verified separately, with original
   # pre-modern compatibility glyphs retained in the source, not corrected.
   notes.append({'text':cn,'source_locator':{'pdf_page':min(pages),'note':'borrowing definition Chinese'},'match_method':'NFKC_original_note_readback; paired_with_English_not_substituted'})
   notes.append({'text':'1998年、1999年台灣省公共圖書館不含分館。','source_locator':{'pdf_page':pages[2],'note':'library count note'},'match_method':'NFKC_source_page_readback'})
  if sid=='dgbas-county-library-Z091101a029':
   quote='公立公共圖書館館數（包含國家圖書館、國立公共資訊圖書館及國立臺灣圖書館）。';assert compact(quote) in normalized
   notes.append({'text':quote,'source_locator':loc,'match_method':'literal_HTML_table_note_readback'})
   facts['national_library_scope']['printed_note_includes']=['國家圖書館','國立公共資訊圖書館','國立臺灣圖書館']
   fp.append(policy(items,'僅官方同一查詢表、同原地區列；原列1998–2005缺值不能補量，正值面板範圍只取實有值年份。',loc,segments=[[y for y in years if any(r['data_year']==y and r['value'] is not None for r in items)]],status='published_panel_limited',dimension='same_official_query_snapshot',excluded_years_no_numeric=sorted({r['data_year'] for r in items if r['value'] is None})))
  if layer=='programme_quantities':
   panel=False;unresolved.append('計畫參照年2005不是data_year；活動窗、學期或跨年專案不改成全年。')
   fp.append(policy(items,'2005計畫表為具名方案／參加數量；不與館務全年活動場次／人次相接。',loc,status='incompatible',dimension='programme_vs_annual',raw_periods=values(items,'period_raw')))
  status='published_panel_limited' if panel else 'source_series_only'
  scope={'status':status,'panel_id':eid+'-panel' if panel else None,'positive_scope':'Only the original published table/edition, same printed row metric and exact compatible raw dimensions. No cross-source splicing or reporting-method equivalence.' if panel else 'Source-labelled rows only; no cross-year comparability permission established.',
   'group_by':['source_id','source_table','series_id','geography_or_entity_raw','indicator','unit','collection_type','population_scope','national_libraries_scope','institutional_level','aggregation_role','period_type','source_edition','age_sex_reader_classification'],
   'data_years':years,'observation_ids':sorted(r['observation_id'] for r in items),
   'field_policies_apply_before_panel_permission':True,'nulls_and_markers_never_numeric_pairs':True,'cross_version_comparison_permitted':False,'geography_recoding_permitted':False,
   'within_same_national_published_panel':bool(panel and all(r.get('geography')=='全國' for r in items)),
   'keep_raw_geography_vintage':True,'mixed_units_not_converted_to_pure_books':True,'unknown_units_still_unresolved':True}
  title=next((r.get('source_table_title') for r in items if r.get('source_table_title')),None)
  card={'evidence_id':eid,'source_id':sid,'source_sha256':items[0]['source_sha256'],'source_url':items[0].get('source_download_url') or items[0]['source_url'],
   'source_urls':values(items,'source_url'),'source_locator':{'pages_or_HTML':loc,'table':table,'raw_locator_examples':values(items,'source_locator')[:6]},'layer':layer,'source_table':None if table=='None' else table,'source_table_title':title,
   'source_fields':fields,'indicators':indicators,'series_ids':values(items,'series_id'),'data_years_present':years,'source_report_reference_years':values(items,'source_report_reference_year'),
   'reviewed_original':all(len(page(path,n).strip())>20 for n in pages) if pages else len(joined.strip())>20,'semantic_facts':facts,'original_notes_short':notes[:8],
   'supported_comparison_scope':scope,'field_breaks':breaks,'field_policies':fp,'unresolved':unresolved,
   'review_method':{'method':'retained_original_SHA_readback_and_pypdf_page_text_table_heading_footnote_audit' if pages else 'retained_original_SHA_readback_and_HTML_table_note_and_date_area_cell_audit','original_pages_read':pages,'table_context_review_not_full_numeric_reextraction':True,'metadata_only_not_counted_as_original_definition':True,'rendered_visual_review':VISUAL_CHECKS.get(sid)},
   'observation_ids':sorted(r['observation_id'] for r in items),'observation_count':len(items),'numeric_values_modified':False,
   'original_title_literal_match':bool(title and compact(title) in normalized),'source_field_literal_matches':[f for f in fields if compact(f) and compact(f) in normalized],
   'all_raw_observation_notes_and_qualifiers_remain_in_canonical':True}
  cards.append(card)
 # Exact accounting is by layer; programme facts never enter canonical totals.
 covered=[o for c in cards if c['layer']=='canonical_quantitative' for o in c['observation_ids']]
 pcov=[o for c in cards if c['layer']=='programme_quantities' for o in c['observation_ids']]
 assert len(covered)==len(set(covered))==len(rows) and set(covered)=={r['observation_id'] for r in rows}
 assert len(pcov)==len(set(pcov))==len(programmes)
 assert canonical_path.read_bytes()==canonical_bytes
 for path,old in originals.items():assert digest((root/path).read_bytes())==old['source_sha256']
 scope_counts=collections.Counter(c['supported_comparison_scope']['status'] for c in cards)
 result={'schema_version':'phase2-ncl-source-evidence-1.0','checked_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
  'contract_sha256':digest(contract_path.read_bytes()),'audit_script_sha256':digest(Path(__file__).read_bytes()),
  'scope':{'source_filter':'canonical source_id starts ncl or dgbas; plus 2005 NCL programme quantitative layer','scope_excluded_source_families':sorted({r['source_family'] for r in allrows if not r['source_id'].startswith(('ncl','dgbas'))}),'no_new_network_requests':True,'no_current_dictionary_backport':True},
  'coverage':{'canonical_records':len(rows),'canonical_source_ids':len({r['source_id'] for r in rows}),'canonical_table_groups':sum(c['layer']=='canonical_quantitative' for c in cards),'programme_records':len(programmes),'programme_table_groups':sum(c['layer']=='programme_quantities' for c in cards),'source_cards':len(cards),'physical_originals':len(originals),'original_PDFs':len(readers),'original_HTMLs':len(originals)-len(readers),'original_pages_text_read':len([k for k in page_cache if k[1] is not None]),'reviewed_original_cards':sum(c['reviewed_original'] for c in cards),'pending_original_cards':[c['evidence_id'] for c in cards if not c['reviewed_original']],'comparison_status_counts':dict(scope_counts),'all_selected_observation_ids_covered_once':True,'canonical_values_or_IDs_modified':False},
  'source_cards':cards,'protected_input_sha256':{'data/combined/observations.jsonl':digest(canonical_bytes),'derived/ncl_2005_programmes_long.jsonl':digest(programme_path.read_bytes())},
  'text_extraction_limitations':['pypdf reports advanced encoding B5pc-H limitations for some retained PDFs. Original-page readback is not a claim of complete OCR or layout interpretation. Literal matches, specific visual checks and remaining unresolved dimensions are separately recorded.'],
  'boundaries':['published_panel_limited permits the printed comparison only; not identical historic surveys.','2012 county core original quantities remain absent except existing source-specific count/prose facts; no ratio back-calculation.','Old administrative geography, source editions, national-library inclusion and mixed material units remain distinct.','No source cards imply that every numeric transcription or legal redistribution question has been re-verified.']}
 out=root/'research/phase2-ncl-evidence.json';out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
 lines=['# 第二階段：國圖／主計原表與定義證據','',
  f"覆蓋 {len(rows):,} 筆既有 canonical 觀測、{len({r['source_id'] for r in rows})} 個來源版本、{sum(c['layer']=='canonical_quantitative' for c in cards)} 個原表組；另含 2005 年計畫表 {len(programmes)} 筆、{sum(c['layer']=='programme_quantities' for c in cards)} 表。",
  f"共 {len(originals)} 個原件 SHA 全數讀回一致；{len(cards)} 張 source card，實讀頁數 {len([k for k in page_cache if k[1] is not None])}。沒有重擷取或修改 canonical 數值／ID。",'',
  '可允許範圍只有同一原刊回溯面板、相同原指標／實體／單位／母體／期別等維度；不能把 published_panel_limited 當歷年調查方法完全相同。每張卡附 observation_ids 與具體 field_policies。','',
  '## 主要斷點','',
  '- DGBAS 2005／2008 本版英文原註 Since 2000，與中文「1999以前」一起支持借閱／閱覽在 <=1999 與 >=2000 分段；不可跨段。',
  '- DGBAS 2011 本版中英方向衝突：中文稱1999以前為閱覽，英文稱before1999只含借出者；沒有自行訂正，借閱欄與1999邊界保留 unresolved。這不阻止同版清楚的館數／館藏欄各自有界比較。',
  '- DGBAS 三版都明示1998／1999年臺灣省公共館數不含分館；館數與每10萬人館數按該兩年另段。',
  '- NCL 2016–2024 等五年回溯表只准原刊內面板；國家圖書館館內調閱註屬另一張表，不套到公共館表。',
  '- 舊行政區不改名加總；國立館排除／另列、冊件種混合、2015活動題名／單位衝突、2016活動人數、2017子期間、2024地名疑義均保留。',
  '- 2012閱讀報告2011–12原刊比較表只支持本報告的全國借閱量／人次；不回推出缺失縣市原量。',
  '- 2005計畫表只有活動窗／計畫期，data_year不補2005，不當全年館務活動量。','',
  '## 完整來源表清冊','', '|來源|原表|資料年|原件已讀|比較狀態|證據ID|','|---|---|---|---|---|---|']
 for c in cards:lines.append('|'+c['source_id']+'|'+str(c['source_table'])+'|'+','.join(map(str,c['data_years_present']))+'|'+str(c['reviewed_original'])+'|'+c['supported_comparison_scope']['status']+'|'+c['evidence_id']+'|')
 lines+=['','## 驗收','', '```json',json.dumps(result['coverage'],ensure_ascii=False,indent=2),'```','',
  '重跑：`python scripts/phase2_ncl_source_audit.py`。原PDF與原HTML只讀；私人的整頁render不在公開JSON。四張關鍵頁已背景render後視覺覆核，其他卡的method精確標為原PDF文字／原HTML查讀，沒有冒稱每頁皆做圖像判讀。']
 (root/'research/phase2-ncl-evidence.md').write_text('\n'.join(lines)+'\n')
 print(json.dumps(result['coverage'],ensure_ascii=False,indent=2))

if __name__=='__main__':main()
