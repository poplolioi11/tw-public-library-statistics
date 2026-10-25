#!/usr/bin/env python3
"""Extract all reviewed 2016 operational core tables (NCL106 edition).
Dependencies and content-preserving offline/no-op behavior are in
ncl_2016_2018_common.py. Original PDF/HTML/images remain private.
"""
from ncl_2016_2018_common import *
def extract(p):
 c=common_metrics();levels=['國立圖書館','直轄市立圖書館','縣市立圖書館','鄉鎮市區立圖書館','合計']
 title='全國公共圖書館數量統計－依圖書館隸屬層級（105年）'
 fn=p.footnote('public-library',2,(56,637,483,675))
 mm=[c['counts'][i] for i in [0,1,3,4,5]]
 p.matrix(24,title,2,(175,558,483,635),5,mm,entities=levels,transpose=True,expected_rows=5,footnote=fn)
 p.table(24,title,'public-library',[2],25,'entire numeric grid: four levels plus total; includes reading rooms and outreach')
 title='全國公共圖書館數量統計—依縣市（105年）'
 fn=p.footnote('public-library',3,(56,637,483,688))
 mm=[metric(f'{k}_{lev}',f'{l}／{ll}','所',basis='同章前表同種設施明印所；本表未另印') for k,l in [('main','總館'),('branch','分館'),('reading_room','閱覽室'),('outreach','館外服務站')] for lev,ll in [('municipal','直轄市立'),('county_town','縣鎮市鄉立')]]+[metric('indigenous_autonomous','原住民自治區圖書館','所',basis='同章館數文義推定所；本欄未另印單位')]
 p.matrix(25,title,3,(100,180,483,635),9,mm,expected_rows=23,footnote=fn,note='原表按設施與隸屬分欄，原住民自治區館另列；未將此欄再與各館數欄相加。')
 p.table(25,title,'public-library',[3],207,'all22county rows and printed total; nine printed numeric columns')
 facility_notes={3:'（復興區立圖書館）',4:'（和平區立圖書館）',6:'（高雄市桃源區圖書館、高雄市那瑪夏圖書館、高雄市茂林區圖書館）',8:'（1、尖石鄉立圖書館2、五峰鄉立圖書館）'}
 for r in p.rows:
  if r['source_table']=='25' and r['source_column']==10 and r['source_row'] in facility_notes:
   r['source_cell_note_raw']=facility_notes[r['source_row']]
   r['source_cell_note_status']='printed_supplementary_facility_names'
   r['original_fields']['supplementary_facility_names']=facility_notes[r['source_row']]
 title='全國公共圖書館圖書資料購置經費及人均購書經費（105年）'
 fn='註：本表不含國臺圖及國資圖統計數據。'
 p.matrix(26,title,4,(104,150,259,340),3,c['spending'],expected_rows=12,footnote=fn)
 p.matrix(26,title,4,(325,150,483,322),3,c['spending'],expected_rows=11,row_offset=12,footnote=fn)
 p.table(26,title,'public-library',[4],69,'all22county rows and printed total; split continuation panels')
 title='全國公共圖書館人力資源（105年）'
 p.matrix(27,title,4,(175,450,483,588),5,c['staff'],entities=levels,transpose=True,expected_rows=8)
 p.table(27,title,'public-library',[4],40,'entire8metric ×5level numeric grid')
 title='全國公共圖書館館藏資源數量（105年）'
 p.matrix(28,title,5,(160,160,483,345),5,c['holdings'],entities=levels,transpose=True,expected_rows=10)
 p.table(28,title,'public-library',[5],50,'entire10metric ×5level numeric grid; mixed-unit totals retained')
 title='全國公共圖書館館藏資源數量及人均擁有書量（105年）'
 p.matrix(29,title,6,(101,150,259,340),3,c['county_holdings'],expected_rows=12,footnote=fn)
 p.matrix(29,title,6,(322,150,483,322),3,c['county_holdings'],expected_rows=11,row_offset=12,footnote=fn)
 p.table(29,title,'public-library',[6],69,'all22county rows and printed total; split continuation panels')
 title='全國公共圖書館圖書資料使用情形（105年）'
 p.matrix(30,title,7,(145,140,483,497),4,c['loans'],expected_rows=23,footnote=fn)
 p.table(30,title,'public-library',[7],92,'all22county rows and printed total; four metrics')
 # The2016 category order differs from2017–2018. Read original header order.
 activity=[('reading','閱讀推廣活動'),('story','說故事'),('education_arts','社教藝文活動'),('local','地方特色活動'),('film','影片欣賞'),('other','其他'),('subtotal','小計')]
 for table,pno,unit,titleend in [(31,8,'場次','辦理場次'),(32,9,'人次','參與人次')]:
  title=f'全國公共圖書館推廣活動類型及{titleend}（105年）'
  mm=[metric(k,l,unit,unit,basis='原表題名及同章活動敘述明示'+unit,temporal=FLOW) for k,l in activity]
  p.matrix(table,title,pno,(104,140,483,497),7,mm,expected_rows=23,footnote=fn,note='欄序按PDFium原圖：閱讀推廣、說故事、社教藝文、地方特色、影片欣賞、其他、小計。')
  p.table(table,title,'public-library',[pno],161,'all22county rows and printed total; seven activity categories including subtotal')
 title='全國公共圖書館提供新住民各類服務情形（105年）'
 immigrant=[dict(m) for m in c['immigrant']]
 immigrant[-1].update(label='活動（人數）',unit=None,unit_raw='人數',unit_basis='原表欄頭明印人數；未明示去重人數或累計人次，計數口徑未釐清，不推定為人次。')
 p.matrix(33,title,10,(120,128,483,485),5,immigrant,expected_rows=23,footnote=fn)
 for r in p.rows:
  if r['source_table']=='33' and r['metric_id']=='table33_immigrant_activity_attendance':
   r['unit_status']='source_heading_counting_basis_unresolved'
   r['quality_flags'].append('source_heading_counting_basis_unresolved')
   r['notes']+='；原表活動末欄明印人數，未明示去重人數或累計人次；normalized unit留空，不給人次候選，未改原數值。'
 p.table(33,title,'public-library',[10],115,'all22county rows and printed total; five immigrant service metrics')
 add_stats(p)
 for r in p.rows:
  if r['source_table']=='169':
   r['entity_raw']='公立公共圖書館'
   r['entity_contextual_name']='全國'
   r['entity_kind']='national_total'
   r['source_row_label_raw']='公立公共圖書館'
   r['original_fields']['entity']='公立公共圖書館'
  if r['source_table']=='171':
   r['entity_label_status']='contextual_national_aggregate_inferred'
   r['notes']+='；全國為本表公共館整體範圍的context，不是原印實體地理列名。'
   r['interpretation_basis']+='全國標籤是依本表整體公共館範圍推定的context，非原印實體地理列名。'
   r['original_fields']['entity_context_status']='inferred_national_aggregate_context_not_printed_geography_label'
 for r in p.rows:
  if r['source_table']=='171' and r['metric_id']=='table171_holdings':
   r['metric_raw']='館藏量';r['unit_raw']=None;r['unit']=None
   r['unit_status']='source_unit_unconfirmed_or_not_printed'
   r['unit_basis']='原歷史表該列只印館藏量，未印跨年單位；跨年統一口徑未證，不沿用同卷單年basic欄頭或註腳。'
   r['original_fields']['metric']='館藏量';r['original_fields']['unit_raw']=None
   r['quality_flags'].append('source_historical_unit_not_printed')
   r['notes']+='；原歷史表列名未印單位，normalized unit留空，不將同卷單年基本表冊、件硬套全部五年。'
def main():
 a=argparse.ArgumentParser();a.add_argument('--offline',action='store_true');args=a.parse_args();p=Producer(2016,args.offline);extract(p);p.write([{'document_kind':'public-library','table':34,'reason':'intentional_exclusion: named reading-environment/equipment and exemplary-library construction/project applications and grants; not ordinary aggregate operational statistics'},{'document_kind':'statistics','tables':[170,172,173,174,175],'reason':'intentional_exclusion: separate National Central Library and educational-library types, not public-library core cohort'},{'reason':'Other named projects, awards, individual cases, photos, prose and personal details excluded; completeness claim is limited to inventoried operational core tables.'}])
if __name__=='__main__':main()
