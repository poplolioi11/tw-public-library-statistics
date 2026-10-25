#!/usr/bin/env python3
"""Extract complete reviewed2017 core tables from NCL107 edition.
Dependency: ncl_2016_2018_common.py (stdlib + pdfplumber).
"""
from ncl_2016_2018_common import *
def extract(p):
 c=common_metrics();levels=['國立圖書館','直轄市立圖書館','直轄市山地原住民區立圖書館','縣市立圖書館','鄉鎮市區立圖書館','合計'];fn='註：本表不含國臺圖及國資圖統計數據。'
 title='全國公共圖書館數量統計―依圖書館隸屬層級（106年）'
 foot=p.footnote('public-library',2,(56,596,483,658))
 p.matrix(23,title,2,(160,476,483,590),6,c['counts'],entities=levels,transpose=True,expected_rows=6,footnote=foot)
 p.table(23,title,'public-library',[2],36,'entire6metric ×6level grid; total includes reading rooms and outreach')
 title='全國公共圖書館數量統計―依縣市（106年）'
 p.matrix(24,title,3,(130,135,483,583),5,c['counts'][:5],expected_rows=23,footnote=fn)
 p.table(24,title,'public-library',[3],115,'all22county rows and printed total; main/branch/district/reading room/outreach')
 title='全國公共圖書館圖書資料購置經費及人均購書經費（106年）'
 p.matrix(25,title,4,(100,156,259,355),3,c['spending'],expected_rows=12,footnote=fn)
 p.matrix(25,title,4,(315,156,483,341),3,c['spending'],expected_rows=11,row_offset=12,footnote=fn)
 p.table(25,title,'public-library',[4],69,'all22county rows and total; split continuation panels')
 title='全國公共圖書館人力資源（106年）'
 p.matrix(26,title,4,(160,481,483,670),6,c['staff'],entities=levels,transpose=True,expected_rows=8)
 p.table(26,title,'public-library',[4],48,'entire8metric ×6level grid')
 title='全國公共圖書館館藏資源數量（106年）'
 p.matrix(27,title,5,(140,388,483,674),6,c['holdings'],entities=levels,transpose=True,expected_rows=10)
 p.table(27,title,'public-library',[5],60,'entire10metric ×6level grid; mixed-unit sums retained')
 title='全國公共圖書館館藏資源數量及人均擁有書量（106年）'
 p.matrix(28,title,6,(100,156,259,356),3,c['county_holdings'],expected_rows=12,footnote=fn)
 p.matrix(28,title,6,(315,156,483,341),3,c['county_holdings'],expected_rows=11,row_offset=12,footnote=fn)
 p.table(28,title,'public-library',[6],69,'all22county rows and total; split continuation panels')
 title='全國公共圖書館圖書資料使用情形（106年）'
 p.matrix(29,title,7,(145,145,483,552),4,c['loans'],expected_rows=23,footnote=fn)
 p.table(29,title,'public-library',[7],92,'all22county rows and total; four usage metrics')
 for table,pno,unit,end in [(30,8,'場次','辦理場次'),(31,9,'人次','參與人次')]:
  title=f'全國公共圖書館推廣活動類型及{end}（106年）'
  mm=[metric(k,l,unit,unit,basis='原表題名及同章活動敘述明示'+unit,temporal=FLOW) for k,l in c['activities']]
  p.matrix(table,title,pno,(105,146,483,596),7,mm,expected_rows=23,footnote=fn,note='原圖欄序為閱讀推廣、社教藝文、地方特色、說故事、影片欣賞、其他、小計；與2016欄序分開。')
  p.table(table,title,'public-library',[pno],161,'all22county rows and total; seven categories including subtotal')
 title='全國公共圖書館提供新住民各類服務情形（106年）'
 p.matrix(32,title,10,(120,251,483,646),5,c['immigrant'],expected_rows=23,footnote=fn)
 p.table(32,title,'public-library',[10],115,'all22county rows and total; five immigrant service metrics')
 title='全國公共圖書館年度營運經費（106年）'
 entities=['國臺圖','國資圖','基隆市','臺北市','新北市','桃園市','新竹縣','新竹市','苗栗縣','南投縣','臺中市','彰化縣','雲林縣','嘉義縣','嘉義市','臺南市','高雄市','高雄市','屏東縣','臺東縣','花蓮縣','宜蘭縣','澎湖縣','金門縣','連江縣','合計']
 p.matrix(33,title,16,(105,132,337,646),3,c['budget'],entities=entities,expected_rows=26,note='本表包含兩國立公共館，及高雄市公務機關／行政法人兩個分期列；二列原名保留，來源列號唯一，未去重或改成全年相同母體。')
 for r in p.rows:
  if r['source_table']=='33':
   if r['source_row']==1:r['source_footnotes_raw']='為「國立社教機構作業基金」單位';r['source_footnotes_status']='relevant_original_row_note'
   if r['source_row'] in {17,18}:
    sub='公務機關（1/1-/8/31）' if r['source_row']==17 else '行政法人（9/1-12/31）'
    r['source_subrow_label_raw']=sub;r['period_raw']='106年／'+sub;r['source_footnotes_raw']=sub;r['source_footnotes_status']='relevant_original_row_note'
    r['period_start']='2017-01-01' if r['source_row']==17 else '2017-09-01';r['period_end']='2017-08-31' if r['source_row']==17 else '2017-12-31';r['time_reference']=r['period_start']+'至'+r['period_end']+'（原表分期備註）';r['original_fields']['subrow_note']=sub
    if r['source_row']==17:
     r['source_period_interpretation_status']='printed_extra_slash_unresolved_candidate_dates'
     r['time_reference']='原註公務機關（1/1-/8/31）；日期欄暫按1/1至8/31解讀，原刊多斜線未釐清，解讀狀態未定'
     r['quality_flags'].append('source_period_punctuation_ambiguity_unresolved')
     r['notes']+='；原刊公務機關分期註明1/1-/8/31，多印一個斜線；原註原樣保留，日期分欄暫作候選解讀，不宣稱標點已釐清。'
 p.table(33,title,'public-library',[16],78,'complete operating-expense table: two national libraries,22counties (Kaohsiung two printed period rows), national total')
 add_stats(p)
 for r in p.rows:
  if r['source_table']=='213':
   r['entity_raw']='公立公共圖書館'
   r['entity_contextual_name']='全國'
   r['entity_kind']='national_total'
   r['source_row_label_raw']='公立公共圖書館'
   r['original_fields']['entity']='公立公共圖書館'
  if r['source_table']=='215':
   r['entity_label_status']='contextual_national_aggregate_inferred'
   r['notes']+='；全國為本表公共館整體範圍的context，不是原印實體地理列名。'
   r['interpretation_basis']+='全國標籤是依本表整體公共館範圍推定的context，非原印實體地理列名。'
   r['original_fields']['entity_context_status']='inferred_national_aggregate_context_not_printed_geography_label'
 for r in p.rows:
  if r['source_table']=='215' and r['metric_id']=='table215_holdings':
   r['metric_raw']='館藏量';r['unit_raw']=None;r['unit']=None
   r['unit_status']='source_unit_unconfirmed_or_not_printed'
   r['unit_basis']='原歷史表該列只印館藏量，未印跨年單位；跨年統一口徑未證，不沿用同卷單年basic欄頭或註腳。'
   r['original_fields']['metric']='館藏量';r['original_fields']['unit_raw']=None
   r['quality_flags'].append('source_historical_unit_not_printed')
   r['notes']+='；原歷史表列名未印單位，normalized unit留空，不將同卷單年基本表冊、件硬套全部五年。'
def main():
 a=argparse.ArgumentParser();a.add_argument('--offline',action='store_true');args=a.parse_args();p=Producer(2017,args.offline);extract(p);p.write([{'document_kind':'statistics','tables':[214,216,217,218,219],'reason':'intentional_exclusion: National Central Library and educational-library statistics outside public-library core'},{'reason':'Named construction/equipment projects, awards, individual cases, prose, photos and personal details excluded; ordinary aggregate annual operating expenses included.'}])
if __name__=='__main__':main()
