#!/usr/bin/env python3
"""Bounded original-cell probes, separate from the formal statistical dataset.

Reads the exact official originals supplied via --source-root. Does not acquire
sources, infer missing quantities, modify canonical data or select panel sources.
"""
import argparse,collections,decimal,hashlib,json,re
from pathlib import Path
import pdfplumber
import pypdfium2 as pdfium
ROOT=Path(__file__).resolve().parents[1]
SOURCES={
 'tainan-bulletin-10505':{'sha256':'adfe317a24a3a800414b819c5321b40917a3b44026141124dadd3a52cded1aa4','url':'https://w3fs.tainan.gov.tw/001/Upload/2/attachment/9368/99/month10505-3.pdf','edition_raw':'統計通報—臺南市公共圖書館概況（檔名month10505-3；刊日未由原件另核）'},
 'ntpc-cultural-2015':{'sha256':'d6774268bba568ab8fec748bc9ac23b84a1bf85e4ee65e75ba55cd8d6f39bb5f','url':'https://www.culture.ntpc.gov.tw/files/file_pool/1/0g289529270201779637/%E6%96%B0%E5%8C%97%E5%B8%82%E6%94%BF%E5%BA%9C%E6%96%87%E5%8C%96%E5%B1%80104%E5%B9%B4%E5%BA%A6%E7%B5%B1%E8%A8%88%E5%B9%B4%E5%A0%B1.pdf','edition_raw':'新北市政府文化局104年度統計年報'}
}
TN_ENTITIES=['全國','六都地區','新北市','臺北市','桃園市','臺中市','臺南市','高雄市','宜蘭縣','新竹縣','苗栗縣','彰化縣','南投縣','雲林縣','嘉義縣','屏東縣','臺東縣','花蓮縣','澎湖縣','基隆市','新竹市','嘉義市','金門縣','連江縣']
TN_COL1=[('圖書館數','所'),('圖書館數排名','序位'),('圖書冊數','冊'),('每人可分配藏書冊數','冊/人'),('每人可分配藏書冊數排名','序位'),('圖書資訊借閱人次','人次'),('每人借閱量','冊/人'),('每人借閱量排名','序位')]
TN_COL2=[('圖書冊數','冊'),('圖書冊數變動率','%'),('每人可分配藏書冊數','冊/人'),('每人可分配藏書冊數變動率','%'),('圖書資訊借閱人次','人次'),('圖書資訊借閱人次變動率','%'),('每人借閱量','冊/人'),('每人借閱量變動率','%')]
NT_COL=[('藏書冊數','冊'),('辦證人數',None),('借閱冊數','冊'),('借閱人次','人次')]
def stable(x):return (json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n').encode()
def normalized(x):return re.sub(r'[\s,]','',x)
def number(x):
 value=normalized(x)
 if value in ('--','…','-'):return None,'source_marker_uninterpreted'
 if not re.fullmatch(r'\d+(?:\.\d+)?',value):raise ValueError('Unknown source token: '+x)
 return format(decimal.Decimal(value),'f'),'reported'
def source_rows(words,xmax,ymin,ymax,accept):
 labels=[]
 for w in words:
  if w['x1']<=xmax and ymin<=w['top']<=ymax:
   row=next((r for r in labels if abs(r['top']-w['top'])<1.5),None)
   if row is None:row={'top':w['top'],'words':[]};labels.append(row)
   row['words'].append(w)
 return [{'label':''.join(w['text'] for w in sorted(r['words'],key=lambda w:w['x0'])),'top':r['top']} for r in sorted(labels,key=lambda r:r['top']) if accept(''.join(w['text'] for w in sorted(r['words'],key=lambda w:w['x0'])))]
def extract(root,source_root):
 records=[];source_meta=[];checks=0;format_differences=[]
 for sid,spec in SOURCES.items():
  path=source_root/(sid+'.pdf');body=path.read_bytes();digest=hashlib.sha256(body).hexdigest()
  if spec['sha256'] and spec['sha256']!=digest:raise ValueError('Original source version changed: '+sid)
  source_meta.append({'source_id':sid,'source_url':spec['url'],'source_sha256':digest,'source_edition_raw':spec['edition_raw'],'original_bytes':len(body),'original_pdf_distributed':False})
  with pdfplumber.open(path) as pdf,pdfium.PdfDocument(path) as independent:
   def emit(page_index,table,labels,bounds,columns,table_year=None):
    nonlocal checks
    page=pdf.pages[page_index];words=page.extract_words(x_tolerance=1,y_tolerance=1);tp=independent[page_index].get_textpage()
    for ri,label in enumerate(labels,1):
     line=[w for w in words if abs(w['top']-label['top'])<1.6]
     for ci,(metric,unit) in enumerate(columns,1):
      cell=[w for w in line if bounds[ci-1]<=w['x0'] and w['x1']<=bounds[ci]]
      if not cell:raise ValueError(f'Missing source cell {sid}/{table}/{label}/{metric}')
      raw=' '.join(w['text'] for w in sorted(cell,key=lambda w:w['x0']));value,status=number(raw);box=[min(w['x0'] for w in cell),min(w['top'] for w in cell),max(w['x1'] for w in cell),max(w['bottom'] for w in cell)]
      other=tp.get_text_bounded(left=box[0]-0.3,bottom=page.height-box[3]-0.3,right=box[2]+0.3,top=page.height-box[1]+0.3).strip();other_value,other_status=number(other)
      if value!=other_value or status!=other_status:raise ValueError('Independent PDF text differs: '+str((sid,table,label,metric,raw,other)))
      checks+=1
      if raw!=other:format_differences.append({'source_id':sid,'table':table,'row':label['label'],'column':metric,'pdfminer':raw,'pdfium':other,'numeric_identity_verified':True})
      raw_period=label['label'];year=table_year;period_status='table_title';scope=raw_period
      if sid.startswith('ntpc'):
       match=re.fullmatch(r'民國(\d+)年底',raw_period)
       year=int(match.group(1))+1911 if match else None;period_status='explicit_roc_year_plus_1911' if match else 'district_row_year_not_explicit';scope='新北市' if match else raw_period
      elif table=='2':
       year=int(raw_period)+1911 if raw_period.isdigit() else None;period_status='explicit_roc_year_plus_1911' if year else 'multi_year_change_not_single_year';scope='臺南市'
      records.append({'probe_record_id':'probe-'+hashlib.sha256(f'{sid}/{table}/{page_index+1}/{ri}/{ci}'.encode()).hexdigest()[:24],'source_id':sid,'source_version_id':sid+'@sha256:'+digest,'license_status':'published_statistical_facts_document_license_unconfirmed','source_url':spec['url']+'#page='+str(page_index+1),'source_sha256':digest,'source_edition_raw':spec['edition_raw'],'source_locator':{'pdf_page':page_index+1,'printed_page':('6-3' if page_index==108 else '6-4') if sid.startswith('ntpc') else None,'table':table,'row_ordinal':ri,'row_label_raw':raw_period,'column_ordinal':ci,'column_label_raw':metric,'bbox_pdfplumber':box},'geography_raw':scope,'source_row_label_raw':raw_period,'data_year':year,'period_status':period_status,'source_table_year_context':table_year,'raw_value_pdfminer':raw,'raw_value_pdfium':other,'value':value,'value_status':status,'unit':unit,'unit_status':'source_label' if unit else 'caption_mixed_card_count_unresolved','original_caption_unit_raw':'冊數、人次' if sid.startswith('ntpc') else None,'temporal_interpretation':'multi_year_change' if period_status=='multi_year_change_not_single_year' else 'as_printed_not_certified','comparison_permission':'none_probe_not_canonical_or_panel','official_original_required_to_reproduce':True})
    tp.close()
   if sid=='tainan-bulletin-10505':
    words=pdf.pages[1].extract_words(x_tolerance=1,y_tolerance=1);labels=source_rows(words,110,130,540,lambda s:s in TN_ENTITIES)
    assert [x['label'] for x in labels]==TN_ENTITIES
    emit(1,'1',labels,[108,177,204,260,345,380,450,510,543],TN_COL1,2015)
    labels=source_rows(words,140,650,755,lambda s:s in ['100','101','102','103','104','100-104變動情形']);assert len(labels)==6,[x['label'] for x in labels]
    emit(1,'2',labels,[135,194,229,310,342,415,450,508,543],TN_COL2)
   else:
    for page_index,count in [(108,22),(109,17)]:
     words=pdf.pages[page_index].extract_words(x_tolerance=1,y_tolerance=1);labels=source_rows(words,145,130,705,lambda s:bool(re.fullmatch(r'民國\d+年底|.+區',s)));assert len(labels)==count,[x['label'] for x in labels]
     emit(page_index,'6-2',labels,[152,260,357,454,545],NT_COL,2015)
 records.sort(key=lambda r:(r['source_id'],r['source_locator']['table'],r['source_locator']['pdf_page'],r['source_locator']['row_ordinal'],r['source_locator']['column_ordinal']))
 assert len({r['probe_record_id'] for r in records})==len(records), 'duplicate probe record ids'
 counts=collections.Counter(r['source_id'] for r in records);assert counts=={'tainan-bulletin-10505':240,'ntpc-cultural-2015':156}
 report={'schema_version':'1.0.0','role':'source_discovery_bounded_cell_evidence_not_formal_observations','sources':source_meta,'scope':'Tainan bulletin both tables in full; NTPC2015 table6-2 with its continuation in full. Not all tables in the NTPC yearbook.','canonical_data_modified':False,'cross_source_aggregation_permitted':False,'source_text_and_full_pdf_distributed':False,'records':records,'validation':{'source_cells':len(records),'independent_pdf_engine_numeric_checks':checks,'source_marker_cells':sum(r['value'] is None for r in records),'original_reported_zeros':sum(r['value'] is not None and decimal.Decimal(r['value'])==0 for r in records),'record_ids_unique':len({r['probe_record_id'] for r in records})==len(records),'format_differences_preserved':format_differences,'sources_by_count':dict(counts),'known_scope_notes':['Tainan2015 table1 library-count inclusion of branches was not independently certified; counts must not be joined to another series.','NTPC collection excludes non-book materials in2006–2009 and includes books/electronic/non-book resources since2010; preserved original table footnote.','NTPC card-count exact unit and temporal meaning not confirmed by its shared caption; unit stays null.','NTPC district rows have no individual printed year; keep data_year=null and table context2015 separately.','Tainan100-104 change row is a multi-year difference, never an annual2015 observation.']}}
 dest=root/'research/source-probes/20261028-original-cells.json';dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(stable(report));return report
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,default=ROOT);p.add_argument('--source-root',type=Path,required=True);a=p.parse_args();report=extract(a.root.resolve(),a.source_root.resolve());print(json.dumps({k:v for k,v in report['validation'].items() if k!='format_differences_preserved'},ensure_ascii=False))
if __name__=='__main__':main()
