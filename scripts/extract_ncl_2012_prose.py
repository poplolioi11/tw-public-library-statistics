#!/usr/bin/env python3
"""Image-reviewed 2012 public-library operational facts from yearbook102 prose.

Reconstruct glyph order from PDF text matrices (font bounding boxes displace
Latin digits relative to CJK text), retain exact original numeral spans, and
match every printed numeral in sections1–8 to an explicit interpretation.
Never manufacture a county table or infer unprinted values from ratios.
"""
from __future__ import annotations
import argparse,csv,hashlib,json,re
from collections import Counter,defaultdict
from decimal import Decimal
from pathlib import Path
import pdfplumber
BASE=Path(__file__).resolve().parents[1]
RAW=BASE/'raw/ncl-2012';DERIVED=BASE/'derived'
PDF=BASE/'raw/ncl-additional/yearbook-102-public-library.pdf'
META=BASE/'raw/ncl-additional/yearbook-102-public-library.metadata.json'
SOURCE='ncl-yearbook-102-operational-prose-2012'
NUM=re.compile(r'[0-9][0-9,]*(?:\.[0-9]+)?(?:億(?:[0-9][0-9,]*)?)?(?:萬(?:[0-9][0-9,]*)?)?')
COUNTIES={'臺北市','新北市','臺中市','臺南市','高雄市','基隆市','桃園縣','新竹市','新竹縣','苗栗縣','彰化縣','南投縣','雲林縣','嘉義市','嘉義縣','屏東縣','宜蘭縣','花蓮縣','臺東縣','澎湖縣','金門縣','連江縣'}
NATION='全國';LEVELS=['國立級圖書館','直轄市級圖書館','縣市級圖書館','鄉鎮市級圖書館','臺灣省政府圖書館'];ALL=[NATION]+LEVELS
FLOW='flow_calendar_year';STOCK='stock_year_end';RATIO='derived_ratio'
SPECS=[]

def normalize(raw):
    s=raw.replace(',','').replace('約','');total=Decimal(0)
    if '億' in s:a,s=s.split('億');total+=Decimal(a)*100000000
    if '萬' in s:a,s=s.split('萬');total+=Decimal(a)*10000
    if s:total+=Decimal(s)
    return str(total)

def spec(entity,key,label,unit,temporal=STOCK):return {'entity':entity,'key':key,'label':label,'unit':unit,'temporal':temporal}
def repeated(entities,key,label,unit,temporal=STOCK):return [spec(e,key,label,unit,temporal) for e in entities]
def add(number,title,first,last,columns):SPECS.append({'number':number,'title':title,'first':first,'last':last,'columns':columns})

def specifications():
    c=[]
    for entity,keys in [('國立臺中圖書館',['branch','reading_room','outreach']),('臺北市',['branch','reading_room','outreach']),('新北市',['branch','reading_room']),('高雄市',['branch','reading_room','outreach']),('臺中市',['main','branch','reading_room','outreach']),('臺南市',['main','branch','reading_room','outreach']),('縣市級圖書館',['library_count_unspecified','branch','reading_room','outreach']),('鄉鎮市級圖書館',['library_count_unspecified','branch','reading_room','outreach']),('臺灣省政府圖書館',['library_count_unspecified','reading_room']),(NATION,['library_count_unspecified','branch','reading_room','outreach'])]:
        for key in keys:c.append(spec(entity,key,{'main':'總館數','branch':'分館數','reading_room':'閱覽室數','outreach':'館外服務站數','library_count_unspecified':'圖書館數（原文未另稱總館）'}[key],'所'))
    add(1,'一、圖書館數量','至101年底','二、人力資源',c)
    c=[spec(NATION,'staff_'+k,l,'人') for k,l in [('all','工作人員總數'),('compiled','編制內人員'),('temporary','臨時人員'),('contract','約聘僱人員'),('student','工讀生'),('volunteer','志工'),('other','其他')]]+repeated(LEVELS,'staff_all','人力總計','人')
    staff_counties=['臺南市','嘉義市','新竹市','桃園縣','新北市','金門縣','新竹縣','高雄市','臺中市','屏東縣','彰化縣','臺東縣','雲林縣','嘉義縣','花蓮縣','苗栗縣','宜蘭縣','澎湖縣','南投縣','臺北市','基隆市']
    c+=repeated([NATION]+staff_counties,'service_population_per_staff','每位館員所服務之人口數','人／館員',RATIO)
    add(2,'二、人力資源','全國公立公共圖書館工作人員總數為','三、圖書資料經費',c)
    c=[spec(NATION,'acquisition_'+k,l,'新臺幣元',FLOW) for k,l in [('all','全年購買圖書資料經費總計'),('books','購買圖書'),('periodicals','期刊'),('newspapers','報紙'),('audiovisual','視聽資料'),('electronic','電子資料'),('other','其他資料')]]+repeated(LEVELS,'acquisition_all','全年購買圖書資料經費總計','新臺幣元',FLOW)
    c+=repeated([NATION,'連江縣','臺北市','金門縣','雲林縣','新北市','苗栗縣','澎湖縣','花蓮縣','臺中市','臺南市','高雄市','臺東縣','桃園縣','宜蘭縣','南投縣','嘉義市','新竹縣','嘉義縣','屏東縣','基隆市','彰化縣','新竹市'],'acquisition_per_capita','每人購書經費','新臺幣元／人',RATIO)
    add(3,'三、圖書資料經費','全國公立公共圖書館101年全年購買圖書資料經費總計','四、圖書資料數量',c)
    c=[spec(NATION,'holdings_'+k,l,u) for k,l,u in [('all','館藏數量總計','冊（件、種）'),('books','圖書','冊'),('periodicals','期刊','種'),('newspapers','報紙','種'),('other','其他','冊'),('nonbook','非書資料','冊（原文）'),('electronic','電子資源','種')]]+repeated(LEVELS,'holdings_all','館藏收藏數量','冊（原文；混合館藏）')
    c+=repeated([NATION,'連江縣','澎湖縣','臺北市','臺東縣','南投縣','花蓮縣','金門縣','宜蘭縣','苗栗縣','屏東縣','新北市','嘉義縣','臺中市','高雄市','雲林縣','臺南市','新竹縣','彰化縣','基隆市','嘉義市','桃園縣','新竹市'],'holdings_per_capita','每人擁有公共圖書館館藏冊數','冊／人（原文混合館藏）',RATIO)
    add(4,'四、圖書資料數量','全國公立公共圖書館101年全年館藏數量','五、閱覽席位及電腦數量',c)
    c=repeated(ALL,'seats','閱覽席位數','席')+repeated(ALL,'computers','供讀者使用電腦數','臺')
    add(5,'五、閱覽席位及電腦數量','全國公立公共圖書館101年提供之閱覽席位','六、借閱證數量',c)
    add(6,'六、借閱證數量','全國公立公共圖書館101年全年辦證數量','七、館藏使用情形',repeated(ALL,'library_cards','全年辦證數量（是否累計未明示）','張','annual_measure_cumulative_or_new_not_confirmed'))
    c=repeated(ALL,'loans','全年圖書資料借閱量','冊次（原文冊／件）',FLOW)
    c+=repeated([NATION,'臺北市','連江縣','臺中市','臺南市','高雄市','彰化縣','澎湖縣','苗栗縣','新北市','南投縣','宜蘭縣','新竹市','新竹縣','嘉義市','基隆市','金門縣','花蓮縣','桃園縣','屏東縣','雲林縣','臺東縣','嘉義縣'],'loans_per_capita','每人借閱冊數','冊次／人',RATIO)
    c+=repeated(ALL,'borrower_visits','全年圖書資料借閱人次','人次',FLOW)
    add(7,'七、館藏使用情形','全國公立公共圖書館101年全年圖書資料借閱量','八、推廣活動辦理情形',c)
    c=[]
    for base,unit,label in [('events','場次','推廣活動場次'),('attendance','人次','推廣活動參加人次')]:
        for entity in ALL:
            for key,category in [('all','總計'),('reading','閱讀推廣活動'),('education_arts','社教藝文活動'),('local','地方特色活動'),('story','說故事活動'),('film','影片欣賞活動'),('other','其他活動')]:
                if entity=='臺灣省政府圖書館' and key in {'local','other'}:continue
                c.append(spec(entity,base+'_'+key,label+'／'+category,unit,FLOW))
    add(8,'八、推廣活動辦理情形','全國公立公共圖書館101年全年推廣活動場次','國立中央圖書館臺灣分館',c)

def source_stream(pdf):
    text='';locations=[];line_records=[]
    for n,p in enumerate(pdf.pages[:4],1):
        for panel,(x0,x1) in [('L',(50,270)),('R',(278,490))]:
            chars=[c for c in p.chars if x0<c['x0']<x1 and 75<p.height-c['matrix'][5]<690];groups=[]
            for c in sorted(chars,key=lambda c:(-c['matrix'][5],c['x0'])):
                baseline=p.height-c['matrix'][5];g=next((g for g in groups if abs(g[0]-baseline)<1),None)
                if g is None:groups.append([baseline,[c]])
                else:g[1].append(c)
            for y,g in sorted(groups):
                g=sorted(g,key=lambda c:c['x0']);line=''.join(c['text'] for c in g).strip()
                if not line:continue
                line_records.append({'pdf_page':n,'panel':panel,'baseline':round(y,3),'text':line})
                for c in g:
                    for char in c['text']:
                        if char.isspace():continue
                        text+=char;locations.append({'pdf_page':n,'panel':panel,'baseline':y,'bbox':[c['x0'],y-10.5,c['x1'],y+3]})
    return text,locations,line_records

def extract():
    m=json.loads(META.read_text());sha=hashlib.sha256(PDF.read_bytes()).hexdigest();assert sha==m['sha256']
    text,locs,lines=source_stream(pdfplumber.open(PDF));rows=[];sections=[]
    specifications()
    for s in SPECS:
        start=text.index(s['first']);end=text.index(s['last'],start+len(s['first']));block=text[start:end]
        tokens=[]
        for match in NUM.finditer(block):
            # The explicit calendar-year label is provenance, not an indicator.
            if match.group()=='101' and block[match.end():].startswith('年'):continue
            tokens.append(match)
        if len(tokens)!=len(s['columns']):raise ValueError(('Unassigned or missing original numerals',s['number'],len(tokens),len(s['columns']),[v.group() for v in tokens]))
        for i,(match,c) in enumerate(zip(tokens,s['columns']),1):
            raw=match.group();prefix=block[max(0,match.start()-1):match.start()];qualifier='approximate_as_printed' if prefix=='約' else None
            if qualifier:raw='約'+raw
            selected=locs[start+match.start():start+match.end()];page_panels=defaultdict(list)
            for a in selected:page_panels[(a['pdf_page'],a['panel'],round(a['baseline'],1))].append(a['bbox'])
            boxes=[]
            for (p,panel,baseline),bs in page_panels.items():boxes.append({'pdf_page':p,'panel':panel,'bbox':[round(min(b[0] for b in bs),3),round(min(b[1] for b in bs),3),round(max(b[2] for b in bs),3),round(max(b[3] for b in bs),3)]})
            entity=c['entity'];kind='county' if entity in COUNTIES else 'national_total' if entity==NATION else 'public_library_institution' if entity in {'國立臺中圖書館','臺灣省政府圖書館'} else 'library_level'
            role='derived_ratio' if c['temporal']==RATIO else 'published_total' if entity==NATION or c['key'].endswith('_all') else 'reported_component'
            unit_suffix=block[match.end():match.end()+8];unit_raw=next((u for u in ['冊（件、種）','冊（件）','人次','場次','人','元','冊','種','席','臺','張','所','場'] if unit_suffix.startswith(u)),None)
            flags=[]
            if role=='published_total':flags.append('published_total_overlaps_components')
            if c['key'].startswith('holdings'):flags.append('source_holdings_mix_units_or_resources')
            if c['key']=='library_cards':flags.append('cumulative_vs_annual_new_not_confirmed')
            context=block[max(0,match.start()-32):min(len(block),match.end()+32)]
            locator='; '.join(f"PDF page {b['pdf_page']}; printed page {68+b['pdf_page']}; panel {b['panel']}; section {s['number']}; prose numeral {i}; bbox "+','.join(f'{v:.3f}' for v in b['bbox']) for b in boxes)
            r=dict(data_year=2012,source_data_year_raw='101年；綜述明示截至101年12月31日',source_edition_roc=102,source_edition='102',entity_raw=entity,entity_contextual_name=entity,entity_kind=kind,geography_vintage='2012原印行政區，保留桃園縣；未重編為現行界',national_libraries_scope='unknown_for_printed_county_ratios' if kind=='county' else 'explicit_national_level' if entity=='國立級圖書館' else 'separately_printed_provincial_library' if entity=='臺灣省政府圖書館' else 'original_section_scope; national_and_provincial_levels_separately_printed',metric_id=f"prose{s['number']:02d}_{c['key']}",metric_raw=c['label'],value_raw=raw,value=normalize(raw),value_status='reported_prose',value_qualifier=qualifier,unit=c['unit'],unit_raw=unit_raw,unit_basis='原段數字後明印單位；人均／每位館員之分母依段落標題。冊次及新臺幣為標準化解讀，原印單位另存。',temporal_kind=c['temporal'],time_reference='2012年全年' if c['temporal']==FLOW else '原文101年全年辦證數量；是否年度新增或累計未另明示' if c['key']=='library_cards' else '綜述明示截至2012年12月31日；比率的分子分母不另反推',period_start='2012-01-01' if c['temporal']==FLOW else None,period_end='2012-12-31',period_raw='101年全年' if c['temporal']==FLOW else '截至101年12月31日（綜述）',institutional_level=entity if kind!='county' else '縣市內涵未另釐清',aggregation_role=role,population_scope='公立公共圖書館；綜述所列四級另列臺灣省政府圖書館；縣市人均值是否含國立館未明示',scope_note='數字出自敘述；僅收明列值。分項、小計及母體重疊不得全表相加。未列縣市／類別不補0、不反算原量。',notes='原文稱每位館員所服務人口，未擅加編制內分母。' if c['key']=='service_population_per_staff' else '館藏混合冊、件、種；不同館級原量按原文保留。' if c['key'].startswith('holdings') else '省政府圖書館另列，未擅併入南投縣。',quality_flags=flags,source_id=SOURCE,source_url=m['source_page_url'],source_download_url=m['source_download_url'],source_sha256=sha,source_local_path=str(PDF.relative_to(BASE)),source_agency='國家圖書館',source_title='中華民國102年圖書館年鑑／公共圖書館',source_retrieved_at=m['source_retrieved_at'],source_pdf_page=boxes[0]['pdf_page'],source_printed_page=str(68+boxes[0]['pdf_page']),source_table='prose',source_table_title=s['title'],source_row=f"section{s['number']}_numeral{i}",source_column='prose',source_location_kind='prose_numeric_span',source_column_path=s['title']+'／'+c['label'],source_cell_bbox=boxes[0]['bbox'],source_cell_bboxes=boxes,source_cell_bbox_kind='PDF text matrix baseline band; Latin/CJK font metrics displacement corrected',source_locator=locator,source_version_id=SOURCE+':'+sha,source_notes='依據我國公共圖書館統計系統的數據資料，截至101年12月31日止。',source_footnotes_raw='按內政部全國人口統計數據加以計算。' if c['key'] in {'service_population_per_staff','acquisition_per_capita'} else None,raw_extracted_line=raw,original_fields={'section':s['title'],'numeral_ordinal':i,'numeral_raw':raw,'following_unit_raw':unit_raw},extraction_status='complete_selected_prose_numerals; all_four_PDFium_page_images_checked; matrix_baseline_order',license_status='not_confirmed',snapshot_distribution='not_in_public_bundle',publication_date='2014-05',publication_date_basis='102卷版權頁明印民國103年5月初版')
            rows.append(r)
        sections.append({'section':s['number'],'title':s['title'],'printed_numeric_spans':len(tokens),'extracted_observations':len(s['columns']),'complete_all_explicit_operational_numerals':True,'missing_cells_created':0})
    return rows,sections,lines,m,sha

def validate(rows):
    checks=[]
    def take(key,entity):return next(r for r in rows if r['metric_id'].split('_',1)[1]==key and r['entity_raw']==entity)
    def compare(label,total,parts):
        s=sum(Decimal(r['value']) for r in parts);v=Decimal(total['value']);checks.append({'check':label,'reported':str(v),'sum_parts':str(s),'matches':s==v,'target_locator':total['source_locator'],'component_locators':[r['source_locator'] for r in parts]})
        if s!=v:total['quality_flags'].append('source_arithmetic_difference')
    for key in ['staff_all','acquisition_all','holdings_all','seats','computers','library_cards','loans','borrower_visits','events_all','attendance_all']:compare(key+'_five_levels',take(key,NATION),[take(key,e) for e in LEVELS])
    compare('staff_categories',take('staff_all',NATION),[take('staff_'+k,NATION) for k in ['compiled','temporary','contract','student','volunteer','other']])
    compare('acquisition_categories',take('acquisition_all',NATION),[take('acquisition_'+k,NATION) for k in ['books','periodicals','newspapers','audiovisual','electronic','other']])
    for key in ['events','attendance']:
        for entity in ALL:
            cats=['reading','education_arts','story','film'] if entity=='臺灣省政府圖書館' else ['reading','education_arts','local','story','film','other']
            compare(key+'_categories_'+entity,take(key+'_all',entity),[take(key+'_'+k,entity) for k in cats])
    coverage={}
    for metric in ['service_population_per_staff','acquisition_per_capita','holdings_per_capita','loans_per_capita']:
        counties={r['entity_raw'] for r in rows if r['metric_id'].endswith('_'+metric) and r['entity_kind']=='county'}
        coverage[metric]={'county_count':len(counties),'missing_from_printed_prose':sorted(COUNTIES-counties),'interpretation':'not printed here; not evidence no official data exists'}
        assert len(counties)==(21 if metric=='service_population_per_staff' else 22)
    assert len(rows)==270
    assert len({(r['entity_raw'],r['metric_id']) for r in rows})==len(rows)
    assert all(normalize(r['value_raw'])==r['value'] for r in rows)
    assert sum(r['value_qualifier'] is not None for r in rows)==1
    return checks,coverage

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--offline',action='store_true',help='all extraction is local; kept for consistent updater invocation');ap.parse_args()
    rows,sections,lines,m,sha=extract();checks,coverage=validate(rows);DERIVED.mkdir(exist_ok=True);RAW.mkdir(exist_ok=True)
    with (DERIVED/'ncl_2012_prose_long.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows({k:json.dumps(v,ensure_ascii=False,separators=(',',':')) if isinstance(v,(dict,list)) else v for k,v in r.items()} for r in rows)
    (DERIVED/'ncl_2012_prose_long.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows))
    meta={'source_id':SOURCE,'source_sha256':sha,'source_pdf':str(PDF.relative_to(BASE)),'source_page_url':m['source_page_url'],'source_download_url':m['source_download_url'],'source_retrieved_at':m['source_retrieved_at'],'data_year':2012,'source_edition_roc':102,'publication_date':'2014-05','rows':len(rows),'inputs':[{'path':str(PDF.relative_to(BASE)),'sha256':sha,'source_id':SOURCE},{'path':str(META.relative_to(BASE)),'role':'official_attachment_fetch_metadata'}],'outputs':['derived/ncl_2012_prose_long.csv','derived/ncl_2012_prose_long.jsonl'],'image_review_paths':[f'raw/ncl-2012/rendered/ncl-yearbook-102-public-{i}.png' for i in range(1,5)],'scope':'All270 explicit operational numeral spans in sections1–8, PDF1–4 printed69–72. Calendar labels/introductory taxonomy counts and later named-institution narratives excluded.','value_status_counts':dict(Counter(r['value_status'] for r in rows)),'sections':sections,'county_ratio_coverage':coverage,'checks':checks,'arithmetic_discrepancies':[c for c in checks if not c['matches']],'intentional_exclusions':['Opening taxonomy count four, calendar year/date numerals and later individual-library narratives are not operational observations.','Unprinted values are never generated: no county core amount table is fabricated; no inferred 0, no blank table rows.','No assessment scores/pass-fail groups, named engineering projects, awards/personal names or book rankings.'],'limits':['Three ratio series cover22counties; staff-service-population ratio covers21 and does not print連江縣. County core absolute amounts remain incomplete.','原文直轄市購書費3,136萬9,190與全國總計及館級加總不一致，原值不修正。','原文直轄市說故事活動參加人次290萬742與所列館級小計不一致，原值不修正。','原文全國辦證998萬117與五館級所列分項加總1007萬1655不一致，原值不修正。','原文全年辦證數量是否年度新增或累計不明示；不能拿來計新增率。','No human double-check or expert certification is claimed.'],'license_status':'not_confirmed','snapshot_distribution':'not_in_public_bundle'}
    (RAW/'ncl-2012-prose.metadata.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2)+'\n');(RAW/'prose-baseline-text.private.json').write_text(json.dumps(lines,ensure_ascii=False,indent=2))
    print(json.dumps({'rows':len(rows),'section_counts':[s['extracted_observations'] for s in sections],'arithmetic_discrepancies':len(meta['arithmetic_discrepancies']),'county_ratio_coverage':coverage},ensure_ascii=False))
if __name__=='__main__':main()
