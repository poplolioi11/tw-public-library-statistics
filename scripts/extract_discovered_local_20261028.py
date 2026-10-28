#!/usr/bin/env python3
"""Extract complete reviewed local-library tables from pinned official originals.

Only statistical cells and essential original labels are exported. Supply local
originals with --source-root; this script does not download or publish files.
"""
from __future__ import annotations
import argparse, collections, decimal, hashlib, json, re, unicodedata
from pathlib import Path
import pdfplumber
import pypdfium2 as pdfium

ROOT = Path(__file__).resolve().parents[1]


def stable(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def numeric(raw):
    normalized = re.sub(r'[\s,]', '', unicodedata.normalize('NFKC', raw)).replace('−', '-')
    if normalized == '':
        return None, 'source_blank'
    if normalized in ('-', '--', '—', '–', '…', '...'):
        return None, 'source_marker'
    if not re.fullmatch(r'[+-]?\d+(?:\.\d+)?', normalized):
        raise ValueError('Unreviewed original token: ' + repr(raw))
    return format(decimal.Decimal(normalized), 'f'), 'reported'


def groups(words, tolerance=2):
    result = []
    for word in sorted(words, key=lambda x: (x['top'], x['x0'])):
        found = next((r for r in result if abs(r['top']-word['top']) < tolerance), None)
        if found is None:
            found = {'top': word['top'], 'words': []}; result.append(found)
        found['words'].append(word)
    for row in result:
        row['words'].sort(key=lambda x: x['x0'])
        row['raw'] = ''.join(w['text'] for w in row['words'])
    return sorted(result, key=lambda x: x['top'])


class Document:
    def __init__(self, root, source_root, sid):
        candidates = json.loads((root/'docs/source-discovery-20261028.json').read_text())['candidates']
        self.meta = next(x for x in candidates if x['candidate_id'] == sid)
        self.sid = sid
        path = source_root/(sid+'.pdf')
        body = path.read_bytes()
        if hashlib.sha256(body).hexdigest() != self.meta['source_sha256']:
            raise ValueError('Original version differs: ' + sid)
        self.pdf = pdfplumber.open(path)
        self.independent = pdfium.PdfDocument(path)
        self.pages = {}; self.words_cache = {}; self.records = []

    def close(self):
        for page, text in self.pages.values(): text.close(); page.close()
        self.pdf.close(); self.independent.close()

    def words(self, page):
        if page not in self.words_cache:
            self.words_cache[page] = self.pdf.pages[page-1].extract_words(x_tolerance=1, y_tolerance=1)
        return self.words_cache[page]

    def raw_cell(self, page, bbox):
        x0, top, x1, bottom = bbox
        words = [w for w in self.words(page) if x0 <= (w['x0']+w['x1'])/2 < x1 and top <= (w['top']+w['bottom'])/2 < bottom]
        raw = ' '.join(w['text'] for w in sorted(words, key=lambda x: (x['top'], x['x0'])))
        if page not in self.pages:
            pg = self.independent[page-1]; self.pages[page] = (pg, pg.get_textpage())
        text = self.pages[page][1]
        height = self.pdf.pages[page-1].height
        other = text.get_text_bounded(left=x0+0.2, right=x1-0.2, bottom=height-bottom+0.2, top=height-top-0.2).strip()
        a, sa = numeric(raw); b, sb = numeric(other)
        if (a, sa) != (b, sb):
            raise ValueError('Independent engines differ: '+str((self.sid,page,bbox,raw,other)))
        return raw, a, sa, {'method':'pdfplumber_and_pdfium_bounded_original_cell', 'numeric_and_status_agree':True, 'pdfium_raw':other}

    def emit(self, *, page, table, title, row, column, label, entity, kind, year, period,
             metric, metric_id, bbox, unit, unit_raw=None, unit_status='source_heading',
             temporal='source_annual_reference', period_status='explicit_original_year',
             population=None, national='not_independently_certified', geography=None,
             role='source_component', notes=None, flags=None, month=None, **extra):
        raw, value, status, independent = self.raw_cell(page,bbox)
        identity = '/'.join(map(str,[self.sid,table,page,row,column,period]))
        printed=str(page-3) if self.sid.startswith('kaohsiung') else str(page) if self.sid.startswith('changhua') else None
        record = {
            'cell_id':'cell-'+hashlib.sha256(identity.encode()).hexdigest()[:26],
            'source_document_id':self.sid,'source_url':self.meta['official_url']+'#page='+str(page),
            'source_sha256':self.meta['source_sha256'],'source_version_id':self.meta['source_version_id'],
            'source_pdf_page':page,'source_printed_page':printed,
            'source_table':str(table),'source_table_title':title,'source_row':str(row),'source_column':str(column),
            'source_locator':f'PDF page {page}; printed page {printed if printed is not None else "unprinted"}; table/section {table}; data row {row}; column {column}; period {period}; bbox '+','.join(f'{n:.4f}' for n in bbox),
            'source_cell_bbox':[round(n,4) for n in bbox], 'row_label_raw':label,'column_label_raw':metric,
            'entity_raw':entity,'entity_kind':kind,'data_year':year,'data_month':month,
            'period_raw':period,'period_status':period_status,'metric_id':metric_id,'metric_raw':metric,
            'value_raw':raw,'value':value,'value_status':status,'unit':unit,'unit_raw':unit_raw or unit,
            'unit_status':unit_status,'temporal_kind':temporal,'population_scope':population or '依原表所列公共圖書館與原列範圍，不自行擴大或合併。',
            'national_libraries_scope':national,'geography_vintage':geography or '原刊地理標籤；未以現行界線重編',
            'aggregation_role':role,'source_notes':notes or [],'quality_flags':flags or [],
            'independent_check':independent, 'source_retrieved_at':self.meta['retrieved_at'],
            'source_edition':self.meta['edition_raw'], 'license_status':'published_statistical_facts_document_license_unconfirmed',
            'source_original_required_to_reproduce':True, **extra,
        }
        self.records.append(record)
        return record

    def emit_character_number(self, page, selected, **kwargs):
        """Use original character geometry for numbers embedded inside a word."""
        box=(min(x['x0'] for x in selected)-.1,min(x['top'] for x in selected)-.1,max(x['x1'] for x in selected)+.1,max(x['bottom'] for x in selected)+.1)
        raw=''.join(c['text'] for c in selected)
        saved=self.words_cache.get(page)
        self.words_cache[page]=[{'text':raw,'x0':box[0], 'x1':box[2],'top':box[1],'bottom':box[3]}]
        try:return self.emit(page=page,bbox=box,**kwargs)
        finally:
            if saved is None:self.words_cache.pop(page,None)
            else:self.words_cache[page]=saved


def numeric_rows(doc, page, x0, x1, top, bottom):
    return groups([w for w in doc.words(page) if x0 <= w['x0'] and w['x1'] <= x1 and top <= w['top'] <= bottom])


def taoyuan(doc):
    rows = numeric_rows(doc,40,170,256,183,740)
    if len(rows) != 24: raise ValueError('Taoyuan full 24-row inventory differs')
    names=['文化局','桃園區','中壢區','大溪區','楊梅區','蘆竹區','大園區','龜山區','八德區','龍潭區','平鎮區','新屋區','觀音區','復興區']
    cols=[('年底圖書館數','library_count','所'),('年底圖書資料收藏數/圖書/合計','books_total','冊'),('年底圖書資料收藏數/圖書/中文','books_chinese','冊'),('年底圖書資料收藏數/圖書/外文','books_foreign','冊'),('年底圖書資料收藏數/期刊/合計','serial_titles_total','種'),('年底圖書資料收藏數/期刊/中文','serial_titles_chinese','種'),('年底圖書資料收藏數/期刊/外文','serial_titles_foreign','種'),('年底電子書收藏數','ebook_titles','種'),('圖書借閱人次','borrower_visits','人次'),('圖書借閱冊數','loans_volumes','冊')]
    bounds={40:[169.9,256.1,349.8,443.4,533.7],41:[38.4,124.44,201.2,278,369,445.8,533.7]}
    for i,r in enumerate(rows):
        year=2012+i if i<10 else None
        label=f'民國{101+i}年 {year}' if i<10 else names[i-10]
        if i<10:
            chars=[w for w in doc.words(40) if w['x1']<169 and abs(w['top']-r['top'])<2]
            raw=''.join(w['text'] for w in sorted(chars,key=lambda x:x['x0']))
            if str(year) not in raw or str(101+i) not in raw:raise ValueError('Taoyuan original year mismatch')
            label=raw
        else:
            # Chinese label can be above the numeric baseline for the bilingual department row.
            tokens=[w['text'] for w in doc.words(40) if w['x1']<169 and r['top']-10 <= w['top'] <= r['top']+1]
            if not any(names[i-10] in t for t in tokens):raise ValueError('Taoyuan district/department label differs')
        y=r['top']
        for ci,(metric,mid,unit) in enumerate(cols):
            page=40 if ci<4 else 41; c=ci if ci<4 else ci-4;b=bounds[page]
            doc.emit(page=page,table='8-11',title='公立公共圖書館概況',row=i+1,column=ci+1,label=label,
                entity='桃園市' if year else names[i-10],kind='county_official_table' if year else 'source_department' if i==10 else 'district_source_label',
                year=year,period=label,metric=metric,metric_id=mid,bbox=(b[c],y-1,b[c+1],y+12),unit=unit,
                temporal='stock_year_end' if ci<8 else 'source_annual_reference',role='published_total' if i<10 else 'source_component',
                period_status='explicit_bilingual_original_year' if year else 'district_or_department_row_year_not_explicit',source_table_year_context=2021,
                notes=['左右兩頁為同一表的續欄；未從人均值推算。','原區別列沒有逐列年份，僅保留2021表脈絡；年度列原地域基礎未另核。'],
                population='桃園市110年統計年報表8-11所列公立公共圖書館，資料來源為公共圖書館統計系統及文化局；年度與區別不可相加。')


def tpml(doc):
    # All primary numeric fields across both pages, plus two explicitly printed components of 43.
    page=1; rows=numeric_rows(doc,1,220,286,130,790)
    if len(rows)!=24:raise ValueError('Taipei first-page primary-value row inventory differs: '+str(len(rows)))
    definitions=[('分館數','facilities_libraries','所','stock_month_reference'),('民眾閱覽室數','facilities_reading_rooms','間','stock_month_reference'),('智慧圖書館','facilities_smart_libraries','間','stock_month_reference'),('借書站','facilities_borrow_stations','處','stock_month_reference'),('借還書工作站','facilities_return_workstations','處','stock_month_reference')]
    for group,unit in [('圖書','冊'),('非書資料(含影片、錄影帶)','片(捲)'),('期刊','冊'),('報紙','份')]:
        for raw,temporal in [('原有','stock_previous_month_reference'),('本月增加','flow_source_month'),('本月減少','flow_source_month'),('現有','stock_month_reference')]:
            definitions.append((group+'/'+raw, 'collections_'+str(len(definitions))+'_'+raw,unit,temporal))
    definitions.extend([('外借冊(片、捲)數/圖書','loans_books','冊','flow_source_month'),('外借冊(片、捲)數/雜誌','loans_magazines','冊','flow_source_month'),('外借冊(片、捲)數/視聽資料','loans_audiovisual','片(捲)','flow_source_month')])
    for i,(r,d) in enumerate(zip(rows,definitions)):
        metric,mid,unit,temporal=d
        rec=doc.emit(page=1,table='monthly-primary',title='臺北市立圖書館統計數據/101年12月',row=i+1,column=1,label=metric,entity='臺北市立圖書館',kind='municipal_library_system',year=2012,month=12,period='民國101年12月',metric=metric,metric_id=mid,bbox=(220,r['top']-1,286,r['top']+14),unit=unit,temporal=temporal,role='source_component',notes=['月資料，不當2012全年。','分館數43原註含1所總館及42所分館，不再把總館另加。'] if i==0 else ['月資料；原有／增加／減少／現有與外借分開。'])
        if metric in ['民眾閱覽室數','智慧圖書館','借書站','借還書工作站']:
            rec['unit']=None;rec['unit_raw']=None;rec['unit_status']='unit_not_printed_in_original_label';rec['source_notes'].append('設施類別已明列，實際數量單位未另印，未以通用量詞填補。')
        if i==0:rec['unit_status']='explicit_original_parenthetical_component_units';rec['source_notes'].append('所依同列原註1所總館／42所分館，不冒充主標題獨立明印單位。')
        if unit=='片(捲)':rec['unit']=None;rec['unit_raw']=unit;rec['unit_status']='source_mixed_media_units_unresolved'
    # Explicit statement inside the same row; values are not independently summed.
    original=doc.pdf.pages[0]
    chars=[c for c in original.chars if 288<c['x0']<435 and 138<c['top']<153]
    for mid,label,pattern in [('libraries_main_component','分館數原註/總館',r'[１1]'),('libraries_branch_component','分館數原註/分館',r'42')]:
        text=''.join(c['text'] for c in chars);match=re.search(pattern,text)
        if not match:raise ValueError('Taipei facility component not found')
        selected=chars[match.start():match.end()];box=(min(x['x0'] for x in selected)-.1,min(x['top'] for x in selected)-.1,max(x['x1'] for x in selected)+.1,max(x['bottom'] for x in selected)+.1)
        # raw_cell uses words; for a number inside a parenthetical word use a character-bounded check.
        raw=''.join(c['text'] for c in selected);saved=doc.words_cache.get(1);doc.words_cache[1]=[{'text':raw,'x0':box[0], 'x1':box[2],'top':box[1],'bottom':box[3]}]
        try:doc.emit(page=1,table='facility-parenthetical',title='分館數原註',row=1,column=mid,label=label,entity='臺北市立圖書館',kind='municipal_library_system',year=2012,month=12,period='民國101年12月',metric=label,metric_id=mid,bbox=box,unit='所',temporal='stock_month_reference',role='component_of_reported_libraries_43',notes=['原註直接明列；43已含這兩個分項，不重複加總。'])
        finally:doc.words_cache[1]=saved
    page2=numeric_rows(doc,2,220,286,50,570)
    if len(page2)!=21:raise ValueError('Taipei second-page primary-value inventory differs: '+str(len(page2)))
    first=[('續借冊數','renewal_volumes','冊')]
    ebook=['NetLibrary','TumbleBook','Tumble TalkingBooks','遠景繁體中文電子書','Little Kiss','格林咕嚕熊親子共讀網','長晉FUN電書','FUN-DAY線上學習英語網','UDN電子書','節慶大書','凌網HyRead電子書','遠流Koobe金庸電子書']
    first += [('電子書點閱次數/'+name,'ebook_usage_'+str(i),'次') for i,name in enumerate(ebook)]
    first += [('借閱人次','borrower_visits','人次'),('網站瀏覽人次','website_visits','人次'),('使用人數','library_use_persons_raw',None),('電腦查詢登記使用人數','computer_registered_use_persons_raw',None),('圖書預約冊(片、捲)數','reservation_items',None),('本月新增辦理借閱證人數','new_cards_persons_raw',None),('場地租借次數','space_rental_count','次'),('隨選視訊使用次數','video_on_demand_uses','次')]
    for i,(r,(metric,mid,unit)) in enumerate(zip(page2,first)):
        doc.emit(page=2,table='monthly-services',title='臺北市立圖書館統計數據/101年12月服務',row=i+1,column=1,label=metric,entity='臺北市立圖書館',kind='municipal_library_system',year=2012,month=12,period='民國101年12月',metric=metric,metric_id=mid,bbox=(220,r['top']-1,286,r['top']+14),unit=unit,unit_raw='人數' if mid.endswith('persons_raw') else '冊(片、捲)' if mid=='reservation_items' else unit,unit_status='source_counting_basis_or_mixed_unit_unresolved' if unit is None else 'source_heading',temporal='flow_source_month',notes=['人數不升為已去重獨立人數；混合冊片捲不改成純冊數。','電子書為點閱次數，不當借出冊數。'] if unit is None or mid.startswith('ebook') else ['月資料，不當全年。'])
    activities=['演講','展覽','影片欣賞','說故事活動','參訪','研習班','讀書會','小博士信箱','其他']
    ys=numeric_rows(doc,2,310,336,600,750)
    if len(ys)!=9:raise ValueError('Taipei activity rows differ')
    for i,(r,name) in enumerate(zip(ys,activities)):
        for ci,(metric,unit,bound) in enumerate([('場次','場',(310,336)),('人數',None,(450,486))],1):
            doc.emit(page=2,table='monthly-activities',title='101年12月活動',row=i+1,column=ci,label=name,entity='臺北市立圖書館',kind='municipal_library_system',year=2012,month=12,period='民國101年12月',metric=name+'/'+metric,metric_id='activity_'+str(i)+'_'+metric,bbox=(bound[0],r['top']-1,bound[1],r['top']+14),unit=unit,unit_raw='人數' if unit is None else '場次',unit_status='source_counting_basis_unresolved' if unit is None else 'source_heading',temporal='flow_source_month',notes=['人數為原欄標籤，未改成人次或去重人數。'] if unit is None else ['月資料，不當全年。'])


def changhua(doc):
    common={'entity':'彰化縣','kind':'county_official_table','national':'依原刊公共館系統，是否完整納入國立館未另認證','population':'原刊彰化縣公共圖書館；來源為教育部公共圖書館統計系統，109年比較限臺灣地區20縣市，不含金門及連江。','notes':['檔名標110年7月，PDF封面印110年8月，未指定單一出版月份。'],'flags':['publication_month_conflict_filename_vs_printed_cover'],'publication_month_raw':'民國110年8月（PDF封面）；民國110年7月（檔名）','publication_date':None}
    # Every statistical table1–7 in this nine-page bulletin, not isolated sample rows.
    specs=[(2,'1','彰化縣公共圖書館收藏數量及每人擁書量統計',125,155,300,705,[125,155,222,287,345,398,461,530],
        [('所數','library_count','所'),('圖書及非書資料收藏數量(A)','collection_including_nonbook_total','冊'),('圖書資料','book_collections','冊'),('非書資料','nonbook_collections','冊'),('電子資源','electronic_collections','冊'),('總人口數','population','人'),('每人擁書量','collection_per_capita','冊/人')],10),
        (5,'3','彰化縣公共圖書館借閱狀況統計',145,220,165,400,[127,220,294,376,456,531],
        [('借閱冊數','loans_volumes','冊'),('借閱人次','borrower_visits','人次'),('年底總人口數','population','人'),('每人借閱量','loans_per_capita','冊/人'),('借閱率','borrowing_rate','%')],10)]
    for page,table,title,x0,x1,lo,hi,bounds,cols,count in specs:
        ys=numeric_rows(doc,page,x0,x1,lo,hi)
        if len(ys)!=count:raise ValueError('Changhua original annual row inventory differs: '+table+' '+str(len(ys)))
        for i,r in enumerate(ys):
            label=next((q['raw'] for q in groups([w for w in doc.words(page) if w['x1']<127 and abs(w['top']-r['top'])<1]) if re.fullmatch(r'\d+年',q['raw'])),None)
            if not label or int(label[:-1])!=100+i:raise ValueError('Changhua printed annual label differs')
            for ci,(metric,mid,unit) in enumerate(cols):
                temporal='stock_year_end' if table=='1' and ci<6 or table=='3' and ci==2 else 'source_annual_reference'
                role='published_total' if mid in ('collection_including_nonbook_total','loans_volumes','borrower_visits','library_count') else 'source_ratio' if 'per_capita' in mid or 'rate' in mid else 'source_component'
                rec=doc.emit(page=page,table=table,title=title,row=i+1,column=ci+1,label=label,year=2011+i,period=label,metric=metric,metric_id=mid,bbox=(bounds[ci],r['top']-1,bounds[ci+1],r['top']+14),unit=unit,unit_raw='冊' if 'per_capita' in mid else unit,unit_status='per_capita_denominator_explicit_in_metric' if 'per_capita' in mid else 'source_heading',temporal=temporal,role=role,**common)
                if mid=='collection_per_capita':rec['source_formula_raw']='(A)/(B)';rec['source_formula_denominator_raw']='總人口數(B)'
                if mid=='loans_per_capita':rec['source_formula_raw']='(A)/(C)';rec['source_formula_denominator_raw']='年底總人口數(C)'
                if mid=='borrowing_rate':rec['source_formula_raw']='(B)/(C)*100';rec['source_formula_denominator_raw']='年底總人口數(C)';rec['source_notes'].append('借閱率為借閱人次除以人口，不當獨立借閱人口比例或借出冊數除館藏。')
    left=['新北市','臺北市','桃園市','臺中市','臺南市','高雄市','宜蘭縣','新竹縣','苗栗縣','彰化縣']
    right=['南投縣','雲林縣','嘉義縣','屏東縣','臺東縣','花蓮縣','澎湖縣','基隆市','新竹市','嘉義市']
    for page,table,title,limits,boxset,cols in [
        (3,'2','109年底臺灣地區各縣市每人擁書量統計',(145,350),[(260,307),(490,533)],[('每人擁書量','collection_per_capita','冊/人')]),
        (5,'4','109年底全國各縣市每人借閱量及借閱率統計',(500,675),[(190,230,305),(417,456,533)],[('每人借閱量','loans_per_capita','冊/人'),('借閱率','borrowing_rate','%')])]:
        for side,names in enumerate((left,right)):
            lx0,lx1=(110,180) if page==3 and side==0 else (340,400) if page==3 else (90,140) if side==0 else (315,365)
            labels=groups([w for w in doc.words(page) if lx0<=w['x0'] and w['x1']<=lx1 and limits[0]<=w['top']<=limits[1]])
            labels=[r for r in labels if r['raw'] in names]
            if [r['raw'] for r in labels]!=names:raise ValueError('Changhua county inventory differs: table'+table)
            for i,r in enumerate(labels):
                for ci,(metric,mid,unit) in enumerate(cols):
                    b=boxset[side];bounds=b if page==5 else b
                    use=dict(common);use['entity']=r['raw'];use['notes']=common['notes']+['原刊比較為臺灣地區20縣市，不含金門及連江。'];use['kind']='county_official_table';use['population']='原刊109年各縣市公共圖書館比較，臺灣地區20縣市，不含金門及連江；依教育部公共圖書館統計系統所列範圍，不另認證國立館。'
                    rec=doc.emit(page=page,table=table,title=title,row=side*10+i+1,column=ci+1,label=r['raw'],year=2020,period='109年底',period_status='explicit_original_table_caption_year_end',metric=metric,metric_id=mid,bbox=(bounds[ci],r['top']-1,bounds[ci+1],r['top']+14),unit=unit,unit_raw='冊' if 'per_capita' in mid else unit,unit_status='per_capita_denominator_explicit_in_metric' if 'per_capita' in mid else 'source_heading',temporal='stock_year_end_ratio' if table=='2' else 'source_annual_ratio',role='source_ratio',**use)
                    if table=='4':rec['source_formula_reference_to']={'source_table':'3','source_pdf_page':5};rec['source_notes'].append('表題印109年底，借閱指標依原刊年度借閱口徑；借閱率原表3口徑為借閱人次／人口×100，不當獨立人數比例。')
    activities=['一般閱讀推廣活動','幼兒閱讀推廣活動','兒童閱讀推廣活動','青少年閱讀推廣活動','樂齡推廣活動','新住民閱讀推廣活動','社教藝文活動','地方特色活動','說故事','影片欣賞','其他']
    for page,table,title,bounds,lo,hi,unit in [
        (8,'5','彰化縣閱讀推廣活動場次統計',[100,138.8,179,216.9,254.8,292.6,330.4,368.2,406.1,443.9,481.7,519.6,557.4],190,355,'場'),
        (9,'7','彰化縣閱讀推廣活動人次統計',[82,126,165.3,204.7,244,283.3,322.6,361.9,401.2,440.5,479.8,519.1,558.4],220,505,'人次')]:
        ys=groups([w for w in doc.words(page) if w['x1']<bounds[0] and lo<=w['top']<=hi]);ys=[r for r in ys if re.fullmatch(r'\d+年',r['raw'])]
        if len(ys)!=7:raise ValueError('Changhua complete activity row inventory differs')
        for i,r in enumerate(ys):
            if int(r['raw'][:-1])!=103+i:raise ValueError('Changhua activity period differs')
            for ci,name in enumerate(['總計']+activities):
                doc.emit(page=page,table=table,title=title,row=i+1,column=ci+1,label=r['raw'],year=2014+i,period=r['raw'],metric=name+('/活動場次' if table=='5' else '/活動人次'),metric_id=('activity_events_' if table=='5' else 'activity_visits_')+str(ci),bbox=(bounds[ci],r['top']-1,bounds[ci+1],r['top']+14),unit=unit,temporal='source_annual_reference',role='published_total' if ci==0 else 'source_component',**common)
    bounds=[99,137.5,178.9,220.3,261.7,303.1,344.5,385.9,427.3,468.7,510.1,551.5]
    ys=numeric_rows(doc,8,100,137.5,540,670)
    if len(ys)!=3:raise ValueError('Changhua comparison table row inventory differs')
    for i,r in enumerate(ys):
        label=['109年(a)','103年(b)','增減情形(a-b)'][i]
        for ci,name in enumerate(activities):
            doc.emit(page=8,table='6',title='彰化縣閱讀推廣活動場次所占比例增減情形',row=i+1,column=ci+1,label=label,year=[2020,2014,None][i],period=label,period_status='explicit_original_year' if i<2 else 'multi_year_difference_not_single_year',metric=name+('/場次所占比例' if i<2 else '/場次所占比例增減'),metric_id='activity_share_'+str(ci) if i<2 else 'activity_share_change_'+str(ci),bbox=(bounds[ci],r['top']-1,bounds[ci+1],r['top']+14),unit='%' if i<2 else '百分點',temporal='source_annual_ratio' if i<2 else 'source_multi_year_difference',role='source_ratio' if i<2 else 'source_difference_not_annual_total',source_comparison_years=[2014,2020],**common)
    for page,figure in [(3,'1'),(6,'2'),(6,'3')]:
        words=[w for w in doc.words(page) if '平均值' in w['text']]
        word=words[0] if page==3 or figure=='2' else words[1]
        chars=[c for c in doc.pdf.pages[page-1].chars if word['x0']-.1<=c['x0'] and c['x1']<=word['x1']+.1 and abs(c['top']-word['top'])<1]
        chars=sorted(chars,key=lambda c:c['x0']);text=''.join(c['text'] for c in chars);match=re.search(r'\d+(?:\.\d+)?',text)
        if not match:raise ValueError('Graph reference number absent')
        use=dict(common);use['entity']='臺灣地區20縣市平均值';use['kind']='source_comparison_reference';use['notes']=common['notes']+['圖中已出現在表2／表4的縣市數值不重複新增；此格只保留表內未列的平均參考線。']
        doc.emit_character_number(page,chars[match.start():match.end()],table='figure-'+figure+'-reference',title='圖'+figure+'平均參考線',row=1,column=1,label='平均值',year=2020,period='109年',metric=['每人擁書量平均值','每人借閱量平均值','借閱率平均值'][int(figure)-1],metric_id='figure_mean_'+figure,unit='%' if figure=='3' else '冊/人',temporal='source_graph_reference',role='reference_line_not_business_total',chart_county_values_duplicate_reference_to={'source_table':'2' if figure=='1' else '4','source_pdf_page':3 if figure=='1' else 5},**use)


def kaohsiung(doc):
    """Every cell in tables7-1,3-1 and the entire 52-page table3-2."""
    base={'entity':'高雄市立圖書館','kind':'municipal_library_system','year':2012,
          'national':'municipal_system_no_national_libraries',
          'population':'原刊高雄市立公共圖書館／高雄市立圖書館系統；含原表列總館、分館與閱覽室，不擴大為全臺或全部設立類型。',
          'geography':'2012年高雄市原刊館別標籤，未以今日館名或行政區重編'}
    # One complete vertically arranged table. Source labels, compound units and
    # anomalous printed quantities are retained rather than repaired.
    overview=[('圖書館數/總館','libraries_main','館'),('圖書館數/分館','libraries_branches','館'),
        ('工作人員數','staff_count','人'),('閱覽席位數','reading_seats','位'),
        ('全年購買圖書資料費','purchase_expenditure','元'),('全年圖書資訊借閱人次','borrower_visits_raw_unit_person','人'),
        ('全年圖書資訊借閱冊數','loans_volumes','冊'),('圖書及非書資料收藏數量/圖書/小計','books_total','冊'),
        ('圖書及非書資料收藏數量/圖書/中文','books_chinese','冊'),('圖書及非書資料收藏數量/圖書/外文','books_foreign','冊'),
        ('圖書及非書資料收藏數量/期刊/小計','periodicals_total','種'),('圖書及非書資料收藏數量/期刊/中文','periodicals_chinese','種'),
        ('圖書及非書資料收藏數量/期刊/外文','periodicals_foreign','種'),('圖書及非書資料收藏數量/報紙','newspapers_total','種'),
        ('圖書及非書資料收藏數量/非書資料/小計','nonbook_total_mixed_units',None),
        ('圖書及非書資料收藏數量/非書資料/地圖','maps','張'),('圖書及非書資料收藏數量/非書資料/縮影單片','microfiche','片'),
        ('圖書及非書資料收藏數量/非書資料/縮影捲片','microfilm','捲'),
        ('圖書及非書資料收藏數量/非書資料/錄音資料片','audio_media_mixed_units',None),
        ('圖書及非書資料收藏數量/非書資料/錄影資料片','video_media_mixed_units',None),
        ('圖書及非書資料收藏數量/非書資料/靜畫資料','still_images','幅'),('圖書及非書資料收藏數量/非書資料/其他','other_nonbook','份'),
        ('圖書及非書資料收藏數量/電子資料庫/光碟資料庫','cd_databases','種'),('圖書及非書資料收藏數量/電子資料庫/線上資料庫','online_databases','種')]
    ys=numeric_rows(doc,100,520,630,100,515)
    if len(ys)!=24:raise ValueError('Kaohsiung table7-1 complete row inventory differs')
    for i,(r,(label,mid,unit)) in enumerate(zip(ys,overview)):
        flags=[];notes=['原刊印數照錄；未從其他表換算、推補或修正。']
        if i==3:flags.append('source_reported_seats_quantity_requires_context_review');notes.append('閱覽席位數113,484為原刊值，未改成一般館舍席次或推算更正。')
        if i==5:flags.append('metric_label_person_times_vs_unit_person_conflict');notes.append('原題為借閱人次，原印單位（人）；兩者均保留。')
        if unit is None:flags.append('source_mixed_units_not_normalized')
        doc.emit(page=100,table='7-1',title='高雄市立公共圖書館概況',row=i+1,column=1,label=label,
            period='民國101年度',metric=label,metric_id=mid,bbox=(520,r['top']-.5,630,r['top']+13),
            unit=unit,unit_raw='片、捲' if i in [18,19] else None if unit is None else unit,
            unit_status='source_mixed_media_units_unresolved' if unit is None else 'source_component_units' if i in [7,10] else 'source_heading',
            temporal='flow_source_year' if i in [4,5,6] else 'source_annual_reference_time_basis_unconfirmed',
            role='source_subtotal' if i in [7,10,14] else 'source_component',notes=notes,flags=flags,**base)
    stock=[('利用圖書館人次','library_visits','人次'),('利用視聽教室人次','audiovisual_room_visits','人次'),
        ('館藏數量/合計','collection_total','冊'),('館藏數量/圖書/中文書','collection_books_chinese','冊'),
        ('館藏數量/圖書/外文書','collection_books_foreign','冊'),('館藏數量/非書資料/地圖資料','collection_maps','冊'),
        ('館藏數量/非書資料/視聽資料','collection_audiovisual','冊')]
    loans=[('館藏借閱冊數/合計','loans_total','冊次'),('館藏借閱冊數/圖書/中文書','loans_books_chinese','冊次'),
        ('館藏借閱冊數/圖書/外文書','loans_books_foreign','冊次'),('館藏借閱冊數/非書資料/地圖資料','loans_maps','冊次'),
        ('館藏借閱冊數/非書資料/視聽資料','loans_audiovisual','冊次')]
    rates=[('借閱率/中文書','borrowing_rate_chinese','%'),('借閱率/外文書','borrowing_rate_foreign','%'),('借閱率/視聽資料','borrowing_rate_audiovisual','%')]
    for page,bounds,cols in [(29,[160,270,375,453,534,614,694,774],stock),
                             (30,[153,229,308,388,467,547,626,706,784],loans+rates)]:
        ys=numeric_rows(doc,page,bounds[0],bounds[1],180,470)
        if len(ys)!=13:raise ValueError('Kaohsiung table3-1 annual/monthly inventory differs')
        for ri,r in enumerate(ys):
            labels=groups([w for w in doc.words(page) if w['x1']<bounds[0] and abs(w['top']-r['top'])<1])
            label=labels[0]['raw'] if len(labels)==1 else ''
            expected='民國101年度' if ri==0 else f'2012年{ri}月'
            if label!=expected:raise ValueError('Kaohsiung table3-1 printed period differs: '+label)
            for ci,(metric,mid,unit) in enumerate(cols):
                flags=[];notes=['表3-1共13列：原刊年度列與12個月列分別保存；不能將年度與月列再加總。']
                if page==29 and ci>=2:
                    flags.append('source_reported_annual_collection_aggregation_basis_unresolved' if ri==0 else 'monthly_collection_reference_time_basis_unconfirmed')
                    notes.append('館藏合計含圖書與非書資料，原表統一標冊；不改成純圖書或年底庫存。')
                doc.emit(page=page,table='3-1',title='高雄市立圖書館閱覽概況-年月別資訊',row=ri+1,column=ci+1 if page==29 else ci+8,label=label,
                    period=label,month=ri or None,metric=metric,metric_id=mid,bbox=(bounds[ci],r['top']-1,bounds[ci+1],r['top']+13),unit=unit,
                    temporal='source_reported_annual_collection_aggregation_basis_unresolved' if page==29 and ci>=2 and ri==0 else 'source_month_collection_time_basis_unconfirmed' if page==29 and ci>=2 else 'source_annual_ratio' if page==30 and ci>=5 and ri==0 else 'source_month_ratio' if page==30 and ci>=5 else 'flow_source_year' if ri==0 else 'flow_source_month',
                    role='source_ratio' if page==30 and ci>=5 else 'published_total' if mid in ['collection_total','loans_total','library_visits','audiovisual_room_visits'] else 'source_component',notes=notes,flags=flags,**base)
    # The 52 pages are two column blocks, each with13 periods and two continuation
    # pages of31 rows. All62 rows include the reported total; names are derived
    # from the originals and must repeat identically across both blocks/periods.
    block1=stock+loans
    block2=rates+[('期刊/合計','periodicals_total','種'),('期刊/中文','periodicals_chinese','種'),('期刊/外文','periodicals_foreign','種'),
                  ('報紙/合計','newspapers_total','種'),('報紙/中文','newspapers_chinese','種'),('報紙/外文','newspapers_foreign','種')]
    inventories={};period_inventory={}
    for block,start,cols,bounds,label_bounds in [
        (1,31,block1,[188,245.8,312,358,405,453,500.5,548,595,643,690,738,785],(105,188)),
        (2,57,block2,[276,322,370,417,465,512,560,607,655,703],(192,274))]:
        for pi in range(13):
            period=None
            for half in range(2):
                page=start+pi*2+half;lo,hi=label_bounds
                ys=groups([w for w in doc.words(page) if lo<=w['x0'] and w['x1']<hi and 140<w['top']<510])
                names=[r['raw'] for r in ys]
                if len(names)!=31 or len(set(names))!=31:raise ValueError('Kaohsiung table3-2 all31 page rows required: '+str((page,names)))
                if half not in inventories:inventories[half]=names
                elif names!=inventories[half]:raise ValueError('Kaohsiung table3-2 names/order changed: '+str(page))
                if half==0:
                    x0,x1=(55,105) if block==1 else (140,191)
                    periods=groups([w for w in doc.words(page) if x0<=w['x0'] and w['x1']<x1 and abs(w['top']-ys[0]['top'])<1])
                    period=periods[0]['raw'] if len(periods)==1 else ''
                    if period!=('民國101年度' if pi==0 else f'2012年{pi}月'):raise ValueError('Kaohsiung3-2 original period not explicit or unexpected: '+str((page,period)))
                    if pi in period_inventory and period_inventory[pi]!=period:raise ValueError('Kaohsiung3-2 column blocks have different periods')
                    period_inventory[pi]=period
                for ri,r in enumerate(ys):
                    entity='高雄市立圖書館' if r['raw']=='總計' else r['raw']
                    for ci,(metric,mid,unit) in enumerate(cols):
                        flags=[];notes=['完整52頁表3-2，含原刊總計、各館別、年度及12個月，年度與月列、總計與館別不能再相加。','原刊調色板兒童玩具圖書館、民眾閱覽室等館別照列；館別列數不直接當分館家數。']
                        temporal='flow_source_year' if pi==0 else 'flow_source_month'
                        if block==1 and 2<=ci<=6:
                            temporal='source_reported_annual_collection_aggregation_basis_unresolved' if pi==0 else 'source_month_collection_time_basis_unconfirmed'
                            flags.append('source_reported_annual_collection_aggregation_basis_unresolved' if pi==0 else 'monthly_collection_reference_time_basis_unconfirmed')
                            notes.append('館藏欄原標冊且含非書資料，年度欄不當年底庫存，不推算月值。')
                        if block==2:
                            temporal=('source_annual_ratio_aggregation_basis_unresolved' if pi==0 else 'source_month_ratio') if ci<3 else ('source_reported_annual_serials_aggregation_basis_unresolved' if pi==0 else 'source_month_serials_reference_time_basis_unconfirmed')
                            if pi==0:flags.append('source_reported_annual_rate_aggregation_basis_unresolved' if ci<3 else 'source_reported_annual_serials_aggregation_basis_unresolved')
                        merged=block==2 and pi==0 and half==0 and ri==0 and ci>=3
                        if merged:flags.append('source_merged_crossed_out_region');notes.append('原刊此總計列的期刊與報紙6欄合併畫叉，無數字；保留欄位空白及原區域註記，不補值。')
                        use=dict(base);use['entity']=entity;use['kind']='municipal_library_system' if r['raw']=='總計' else 'source_library_facility'
                        rec=doc.emit(page=page,table='3-2',title='高雄市立圖書館閱覽概況-分館別資訊',row=ri+1+half*31,column=ci+1 if block==1 else ci+13,label=r['raw'],
                            period=period,month=pi or None,period_status='explicit_original_period_on_table_first_half' if half==0 else 'original_table_continuation_of_explicit_period',
                            metric=metric,metric_id=mid,bbox=(bounds[ci],r['top']-.2,bounds[ci+1],r['top']+8.5),unit=unit,
                            temporal=temporal,role='source_ratio' if block==2 and ci<3 else 'published_total' if r['raw']=='總計' else 'source_component',notes=notes,flags=flags,
                            source_table_column_block=block,source_period_pdf_page=start+pi*2,**use)
                        if merged:rec['source_display_region']={'status':'merged_crossed_out','pdf_page':page,'columns':[16,17,18,19,20,21],'bbox':[417,165,703,176]}
    if len(inventories[0])+len(inventories[1])!=62:raise ValueError('Kaohsiung complete62-row table inventory differs')


EXTRACTORS={'taoyuan-yearbook-ch8-2021':taoyuan,'tpml-2012-12':tpml,'changhua-bulletin-2021-ctrl':changhua,'kaohsiung-cultural-2012':kaohsiung}


def audit_source(doc):
    """Reproducible original-to-original checks; never repair printed values."""
    rows=doc.records;checks=[]
    def compare(name, cases, *, annotate=True):
        result={'check_id':name,'evaluated':0,'agree':0,'not_evaluable_with_original_missing':0,'source_differences':[]}
        for left, terms in cases:
            if left['value'] is None or any(r['value'] is None for _,r in terms):
                result['not_evaluable_with_original_missing']+=1;continue
            expected=sum(decimal.Decimal(r['value'])*sign for sign,r in terms)
            actual=decimal.Decimal(left['value']);result['evaluated']+=1
            if actual==expected:result['agree']+=1
            else:
                result['source_differences'].append({'left_cell_id':left['cell_id'],'component_cell_ids':[r['cell_id'] for _,r in terms],'original_left_value':left['value'],'computed_from_original_component_values':format(expected,'f'),'difference':format(actual-expected,'f')})
                if annotate:
                    for rec in [left]+[r for _,r in terms]:
                        if 'source_printed_total_differs_from_printed_components' not in rec['quality_flags']:rec['quality_flags'].append('source_printed_total_differs_from_printed_components')
                    left['source_notes'].append('同表原刊合計與完整已報分項不相等，原值照留；未改數字。')
        checks.append(result)
    byrow=collections.defaultdict(dict)
    for r in rows:byrow[(r['source_table'],r['source_row'],r['period_raw'])][int(r['source_column']) if str(r['source_column']).isdigit() else r['source_column']]=r
    if doc.sid.startswith('taoyuan'):
        for name,total,components in [('books_total_vs_chinese_foreign',2,[3,4]),('serials_total_vs_chinese_foreign',5,[6,7])]:
            compare(name,[(r[total],[(1,r[c]) for c in components]) for _,r in byrow.items()])
    if doc.sid.startswith('changhua'):
        for table,name,total,components in [('1','collection_total_vs_book_nonbook_electronic',2,[3,4,5]),('5','events_total_vs_all11_categories',1,list(range(2,13))),('7','participants_total_vs_all11_categories',1,list(range(2,13)))]:
            compare(name,[(r[total],[(1,r[c]) for c in components]) for key,r in byrow.items() if key[0]==table])
        a={int(r['source_column']):r for r in rows if r['source_table']=='6' and r['source_row']=='1'}
        b={int(r['source_column']):r for r in rows if r['source_table']=='6' and r['source_row']=='2'}
        c={int(r['source_column']):r for r in rows if r['source_table']=='6' and r['source_row']=='3'}
        compare('share_printed_difference_vs_printed_years',[(c[i],[(1,a[i]),(-1,b[i])]) for i in a])
    if doc.sid.startswith('tpml'):
        primary={int(r['source_row']):r for r in rows if r['source_table']=='monthly-primary'}
        compare('monthly_collection_opening_plus_added_minus_removed',[(primary[i+3],[(1,primary[i]),(1,primary[i+1]),(-1,primary[i+2])]) for i in [6,10,14,18]])
    if doc.sid.startswith('kaohsiung'):
        compare('table7-1_book_and_periodical_subtotals',[(r[1],[(1,byrow[('7-1',str(i),'民國101年度')][1]) for i in components]) for key,r,components in [(('7-1','8','民國101年度'),byrow[('7-1','8','民國101年度')],[9,10]),(('7-1','11','民國101年度'),byrow[('7-1','11','民國101年度')],[12,13])]])
        for table in ['3-1','3-2']:
            compare(table+'_collection_total_vs_all4_components',[(r[3],[(1,r[c]) for c in [4,5,6,7]]) for key,r in byrow.items() if key[0]==table])
        idx={(r['source_table'],r['period_raw'],r['entity_raw'],r['metric_id']):r for r in rows}
        duplicates=[(r,idx[('3-2',r['period_raw'],r['entity_raw'],r['metric_id'])]) for r in rows if r['source_table']=='3-1']
        agree=sum((a['value'],a['value_status'])==(b['value'],b['value_status']) for a,b in duplicates)
        checks.append({'check_id':'table3-1_vs_table3-2_system_total_cells','evaluated':len(duplicates),'agree':agree,'source_differences':[{'left_cell_id':a['cell_id'],'right_cell_id':b['cell_id'],'left_value':a['value'],'right_value':b['value']} for a,b in duplicates if (a['value'],a['value_status'])!=(b['value'],b['value_status'])]})
        # Descriptive comparison only: equality cannot establish a stock/flow
        # definition and is explicitly not permission to aggregate across time.
        annual=[r for r in rows if r['source_table']=='3-1' and r['data_month'] is None and r['metric_id'] not in ['loans_maps','borrowing_rate_chinese','borrowing_rate_foreign','borrowing_rate_audiovisual']]
        compare('descriptive_annual_printed_vs_sum12_months_not_definition_assertion',[(r,[(1,idx[('3-1',f'2012年{m}月',r['entity_raw'],r['metric_id'])]) for m in range(1,13)]) for r in annual],annotate=False)
    return checks


def run(root, source_root, sources=None):
    records=[]; metadata=[]
    for sid in sources or EXTRACTORS:
        doc=Document(root,source_root,sid)
        try:
            EXTRACTORS[sid](doc)
            checks=audit_source(doc)
            records.extend(doc.records)
            metadata.append({'source_document_id':sid,'source_sha256':doc.meta['source_sha256'],'source_url':doc.meta['official_url'],'source_edition':doc.meta['edition_raw'],'records':len(doc.records),'source_marker_cells':sum(r['value_status']=='source_marker' for r in doc.records),'source_blank_cells':sum(r['value_status']=='source_blank' for r in doc.records),'reported_zeros':sum(r['value']=='0' for r in doc.records),'unknown_year_cells':sum(r['data_year'] is None for r in doc.records),'unknown_unit_cells':sum(r['unit'] is None for r in doc.records),'pdf_pages':sorted({r['source_pdf_page'] for r in doc.records}),'tables':dict(collections.Counter(r['source_table'] for r in doc.records)),'all_exported_numeric_cells_cross_checked_with_pdfium':True,'source_to_source_arithmetic_checks':checks,'original_image_review':{'status':'representative_original_images_reviewed_not_manual_review_of_every_numeric_cell','pages':{'taoyuan-yearbook-ch8-2021':[40,41],'tpml-2012-12':[1,2],'changhua-bulletin-2021-ctrl':[1,2,3,5,6,8,9],'kaohsiung-cultural-2012':[29,30,31,32,57,58,81,82,100]}[sid]}})
        finally:doc.close()
    if len({r['cell_id'] for r in records})!=len(records):raise ValueError('Duplicate source-cell identity')
    path=root/'derived/discovered_local_20261028_cells.jsonl';path.parent.mkdir(exist_ok=True);body=('\n'.join(stable(r) for r in records)+'\n').encode();path.write_bytes(body)
    result={'schema_version':'1.0.0','role':'complete_reviewed_original_source_cells_pending_canonical_adapter','sources':metadata,'records':len(records),'original_documents_redistributed':False,'no_imputation':True,'cross_source_aggregation_permitted':False,'output_sha256':hashlib.sha256(body).hexdigest()}
    (root/'derived/discovered_local_20261028_metadata.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,default=ROOT);p.add_argument('--source-root',type=Path,required=True);p.add_argument('--sources',nargs='+',choices=list(EXTRACTORS));a=p.parse_args();r=run(a.root.resolve(),a.source_root.resolve(),a.sources);print(json.dumps(r,ensure_ascii=False))


if __name__=='__main__':main()
