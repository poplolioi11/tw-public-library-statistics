#!/usr/bin/env python3
"""Extract complete reviewed2018 core tables from NCL108 edition.
Dependency: ncl_2016_2018_common.py (stdlib + pdfplumber).
"""
from ncl_2016_2018_common import *
def extract(p):
 c=common_metrics();levels=['國立圖書館','直轄市立圖書館','直轄市山地原住民區立圖書館','縣市立圖書館','鄉鎮市區立圖書館','合計'];fn='註：本表不含國立圖書館統計數據。'
 title='全國公共圖書館數量統計―依圖書館隸屬層級（107年）'
 foot=p.footnote('public-library',2,(56,244,483,305))
 p.matrix(14,title,2,(150,135,483,240),6,c['counts'],entities=levels,transpose=True,expected_rows=6,footnote=foot)
 p.table(14,title,'public-library',[2],36,'entire6metric ×6level grid; facilities total includes reading rooms/outreach')
 title='縣市公共圖書館數量統計―依縣市（107年）'
 p.matrix(15,title,2,(120,365,483,640),6,c['counts'],expected_rows=17,note='原題為縣市，未把兩國立館的總分館／閱覽室／服務站混入縣市小計；含閱覽室和館外站的合計不是總分區館數。')
 p.matrix(15,title,3,(120,110,483,209),6,c['counts'],expected_rows=6,row_offset=17,note='接前頁縣市表。原印末列為小計；不把含閱覽室／館外站的1,133當縣市圖書館總分區館數。')
 p.table(15,title,'public-library',[2,3],138,'all22county rows and printed subtotal; six facility metrics')
 title='縣市公共圖書館圖書資料購置經費及人均購書經費（107年）'
 p.matrix(16,title,3,(100,478,259,669),3,c['spending'],expected_rows=12,footnote=fn)
 p.matrix(16,title,3,(315,478,483,655),3,c['spending'],expected_rows=11,row_offset=12,footnote=fn)
 p.table(16,title,'public-library',[3],69,'all22county rows and printed total; split continuation panels')
 title='全國公共圖書館人力資源統計（107年）'
 p.matrix(17,title,4,(150,323,483,535),6,c['staff'],entities=levels,transpose=True,expected_rows=8)
 p.table(17,title,'public-library',[4],48,'entire8metric ×6level grid')
 title='縣市公共圖書館編制館員及志工人數統計（107年）'
 staffcounty=[metric('population','服務轄區人口數（A）','人'),metric('compiled_staff','編制內館員數（B）','人',basis='表題人數統計及正文人力文義；欄頭未另印人'),metric('professional_compiled_staff','編制內專業人員（C）','人',basis='表題人數統計及正文文義；欄頭未另印人'),metric('volunteers','志工人數（D）','人',basis='欄名人數；未另印單位'),metric('population_per_compiled_staff','編制內人員服務人口數（A/B）','人／編制內館員',basis='由原欄名與明印公式A/B確認為比率；未宣稱原表另印此單位',temporal=RATIO),metric('population_per_professional_compiled_staff','編制內專業人員服務人口數（A/C）','人／編制內專業人員',basis='由原欄名與明印公式A/C確認為比率；未宣稱原表另印此單位',temporal=RATIO),metric('volunteers_per_10000_population','每萬人擁有志工數（D/A*10,000）','人／萬人',basis='原欄名每萬人及明印公式D/A*10,000，單位由文義推定',temporal=RATIO)]
 p.matrix(18,title,5,(110,158,483,557),7,staffcounty,expected_rows=23,footnote=fn,note='原印「無」保留為source_marker且value留空；原報0與0.00照原值保留，不由分母反推或把無改為零。')
 p.table(18,title,'public-library',[5],161,'all22county rows and total; seven staffing/population metrics including3original無markers')
 title='全國公共圖書館館藏資源數量（107年）'
 p.matrix(19,title,6,(140,290,483,498),6,c['holdings'],entities=levels,transpose=True,expected_rows=10)
 p.table(19,title,'public-library',[6],60,'entire10metric ×6level grid; mixed-unit sums retained')
 title='縣市公共圖書館館藏資源數量及人均擁書量（107年）'
 p.matrix(20,title,7,(98,157,259,367),3,c['county_holdings'],expected_rows=12,footnote=fn)
 p.matrix(20,title,7,(315,157,483,349),3,c['county_holdings'],expected_rows=11,row_offset=12,footnote=fn)
 p.table(20,title,'public-library',[7],69,'all22county rows and total; split continuation panels')
 title='縣市公共圖書館圖書資料使用情形（107年）'
 p.matrix(21,title,8,(145,145,483,541),4,c['loans'],expected_rows=23,footnote=fn)
 p.table(21,title,'public-library',[8],92,'all22county rows and total; four usage metrics')
 for table,pno,unit,end,region in [(22,9,'場次','辦理場次',(110,257,483,655)),(23,10,'人次','參與人次',(110,145,483,551))]:
  title=f'縣市公共圖書館推廣活動類型及{end}（107年）'
  mm=[metric(k,l,unit,unit,basis='原表題名及同章活動敘述明示'+unit,temporal=FLOW) for k,l in c['activities']]
  p.matrix(table,title,pno,region,7,mm,expected_rows=23,footnote=fn,note='原圖欄序為閱讀推廣、社教藝文、地方特色、說故事、影片欣賞、其他、小計。')
  p.table(table,title,'public-library',[pno],161,'all22county rows and total; seven activity categories including subtotal')
 title='縣市公共圖書館提供新住民資源及活動辦理情形（107年）'
 p.matrix(24,title,11,(120,287,483,668),5,c['immigrant'],expected_rows=23,footnote=fn)
 p.table(24,title,'public-library',[11],115,'all22county rows and total; five immigrant service metrics')
 title='全國公共圖書館年度營運經費（107年）'
 p.matrix(26,title,17,(120,386,483,654),3,c['budget'],expected_rows=16,note='本表包含國資圖、國臺圖與縣市年度營運經費；不是特定工程計畫成果。')
 p.matrix(26,title,18,(120,119,483,275),3,c['budget'],expected_rows=9,row_offset=16,note='接前頁，兩國立公共館及22縣市全年營運經費的原印總計保留。')
 p.table(26,title,'public-library',[17,18],75,'entire operating-expense table: two national libraries,22counties,total')
 add_stats(p)
 for r in p.rows:
  if r['source_table']=='192':
   r['entity_raw']='公立公共圖書館'
   r['entity_contextual_name']='全國'
   r['entity_kind']='national_total'
   r['source_row_label_raw']='公立公共圖書館'
   r['original_fields']['entity']='公立公共圖書館'
  if r['source_table']=='194':
   r['entity_label_status']='contextual_national_aggregate_inferred'
   r['notes']+='；全國為本表公共館整體範圍的context，不是原印實體地理列名。'
   r['interpretation_basis']+='全國標籤是依本表整體公共館範圍推定的context，非原印實體地理列名。'
   r['original_fields']['entity_context_status']='inferred_national_aggregate_context_not_printed_geography_label'
 for r in p.rows:
  if r['source_table']=='194' and r['metric_id']=='table194_holdings':
   r['metric_raw']='館藏量';r['unit_raw']=None;r['unit']=None
   r['unit_status']='source_unit_unconfirmed_or_not_printed'
   r['unit_basis']='原歷史表該列只印館藏量，未印跨年單位；跨年統一口徑未證，不沿用同卷單年basic欄頭或註腳。'
   r['original_fields']['metric']='館藏量';r['original_fields']['unit_raw']=None
   r['quality_flags'].append('source_historical_unit_not_printed')
   r['notes']+='；原歷史表列名未印單位，normalized unit留空，不將同卷單年基本表冊、件硬套全部五年。'
def main():
 a=argparse.ArgumentParser();a.add_argument('--offline',action='store_true');args=a.parse_args();p=Producer(2018,args.offline);extract(p);p.write([{'document_kind':'public-library','table':25,'reason':'intentional_exclusion: LibraryTalk award/individual-case list; not aggregate operational statistics'},{'document_kind':'statistics','tables':[193,195,196,197,198],'reason':'intentional_exclusion: separate National Central Library and educational-library statistics outside public-library core'},{'reason':'Named construction/equipment projects, awards, individual cases, prose, photos and personal details excluded; ordinary aggregate annual operating expenses included.'}])
if __name__=='__main__':main()
