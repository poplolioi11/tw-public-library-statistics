#!/usr/bin/env python3
"""NCL95 tables6/7: complete independent programme listings and quantities.

This is not calendar-year operating data and does not modify the existing
2005 annual-core producer. Chinese labels are transcribed from private PDFium
source images; every numerical value is read and verified from PDF coordinates
using local Python, never supplied as a model calculation. Required runtime:
Python3.12 stdlib and pdfplumber. No network or AI calls occur in this script.
"""
from __future__ import annotations
import argparse
from collections import Counter
import csv
from decimal import Decimal
import hashlib
import io
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

BASE = Path(__file__).resolve().parents[1]
RAW = BASE / 'raw/ncl-2005-programmes'
ORIGINAL = BASE / 'raw/ncl-2005/yearbook-95-public-library.pdf'
ORIGINAL_META = BASE / 'raw/ncl-2005/yearbook-95-public-library.metadata.json'
REVIEWED_SHA = 'b5f6a52c5b861e1d74b4d917497cd9c806286845ee9bb1a3b8349b2b23a19efe'
SOURCE_ID = 'ncl-yearbook-95-public-library-programmes'
TITLES = {6: '公共圖書館辦理「推廣閱讀活動」及「示範觀摩館」一覽表',
          7: '全國閱讀運動活動內容、場次及參加人數一覽表'}
PERIOD6 = '94年6月核定後，各館陸續於8月至11月展開辦理'
NUMBER = re.compile(r'^\d[\d,]*$')

# All original strings below were read from the source images, without filling
# missing 圖書館 suffixes or substituting geographically plausible names.
# Each tuple is county, left-hand facility names, right-hand merged-cell name,
# and its printed nonnumeric state (None means an actual numeric count exists).
LAYOUT = {
 14: [
  ('臺北市', ['力行分館','文山分館','天母分館','西湖分館','中崙分館'], '文山分館', None),
  ('金門縣', ['金寧鄉立圖書館'], '文化局圖書館', None),
  ('苗栗縣', ['三灣鄉立圖書館','南庄鄉立圖書館','苗栗市立圖書館','後龍鎮立圖書館','苑裡鎮立圖書館'], '公館鄉立圖書館', None),
  ('桃園縣', ['中壢市立圖書館','龜山鄉立圖書館','平鎮市立圖書館','復興鄉立圖書館'], '桃園市立圖書館', None),
  ('新竹縣', ['湖口鄉立圖書館','新豐鄉立圖書館','關西鎮立圖書館'], '竹北市立圖書館', None),
  ('新竹市', ['香山分館'], '不參加', 'source_marker'),
  ('臺北縣', ['深坑鄉立圖書館','新店市立圖書館','平溪鄉立圖書館'], '泰山鄉立圖書館', None),
  ('臺中縣', ['神岡鄉立圖書館','大甲鎮立圖書館','沙鹿鎮立深波圖書館','霧峰鄉立以文圖書館'], '大安鄉立圖書館', None),
  ('臺中市', ['中區圖書館','西區圖書館','南區圖書館','北區圖書館','南屯區圖書館'], '西屯區圖書館', None)],
 15: [
  ('南投縣', ['集集鎮立圖書館','南投市立圖書館','名間鄉立圖書館','魚池鄉立圖書館','鹿谷鄉立圖書館','竹山鎮立圖書館'], '埔里鎮立圖書館', None),
  ('彰化縣', ['溪州鄉立圖書館','埔鹽鄉立圖書館','伸港鄉立圖書館','二水鄉立圖書館'], '埔鹽鄉立圖書館', None),
  ('雲林縣', ['北港鎮立圖書館','虎尾鎮立圖書館','大埤鄉立圖書館','古坑鄉立圖書館'], '西螺鎮立圖書館', None),
  ('嘉義縣', ['朴子市立圖書館','大林鎮立圖書館','民雄鄉立圖書館'], '竹崎鄉立圖書館', None),
  ('嘉義市', ['世賢分館'], '', 'blank_in_source'),
  ('臺南市', ['東區分館','中區分館','安南區分館'], '東區分館', None),
  ('臺南縣', ['仁德鄉立圖書館','學甲鎮立圖書館','山上鄉立圖書館','麻豆鎮立圖書館'], '歸仁鄉立圖書館', None),
  ('高雄市', ['鹽埕分館','新興分館','寶珠分館','三民分館','楠梓分館'], '鼓山分館', None)],
 16: [
  ('澎湖縣', ['湖西鄉立圖書館','白沙鄉立圖書館','七美鄉立圖書館','望安鄉立圖書館'], '湖西鄉立圖書館', None),
  ('高雄縣', ['橋頭鄉立圖書館','岡山鎮立圖書館','路竹鄉立圖書館','杉林鄉立圖書館','大樹鄉立第二圖書館'], '橋頭鄉立圖書館', None),
  ('屏東縣', ['萬丹鄉立圖書館','林邊鄉立圖書館','萬巒鄉立圖書館','南州鄉立圖書館','竹田鄉立圖書館'], '長治鄉立圖書館', None),
  ('花蓮縣', ['吉安鄉立圖書館','光復鄉立圖書館','玉里鎮立圖書館'], '花蓮市立圖書館', None),
  ('臺東縣', ['卑南鄉立圖書館','關山鎮立圖書館','池上鄉立圖書館','太武鄉立圖書館','成功鎮立圖書館'], '鹿野鄉立圖書館', None),
  ('宜蘭縣', ['羅東鎮立圖書館','礁溪鄉立圖書館','壯圍鄉立圖書館','冬山鄉立圖書館','南澳鄉立圖書館'], '宜蘭市立圖書館', None)]}
GROUP_BOUNDS = {
 14: [145.647,228.953,245.526,328.947,395.407,445.526,462.247,511.734,578.667,661.526],
 15: [145.647,245.526,312.047,378.407,428.597,445.526,495.034,561.667,644.598],
 16: [145.747,212.253,295.747,378.507,428.526,511.734,594.967]}
COLS = {14: [56.8,103.369,223.117,291.968,412.405,482.48],
        15: [57.3,103.958,223.705,292.546,413.155,482.48],
        16: [56.8,103.366,223.118,291.965,412.319,482.48]}
ACTIVITIES7 = [
 '與作家有約講座、簽書會、導讀會、座談會',
 '與作家有約體驗之旅',
 '主題書展、票選好書、新書發表會',
 '讀劇說唱、舞畫說書、朗誦、主題影片欣賞',
 '網路閱讀 & 部落格',
 '徵文比賽']
OUTPUTS = ['derived/ncl_2005_programmes.csv', 'derived/ncl_2005_programmes.jsonl',
           'derived/ncl_2005_programmes_long.csv', 'derived/ncl_2005_programmes_long.jsonl',
           'raw/ncl-2005-programmes/metadata.json', 'raw/ncl-2005-programmes/cell-audit.json']


def sha(b):
    return hashlib.sha256(b).hexdigest()


def stable_write(path, body):
    body = body.encode('utf-8') if isinstance(body, str) else body
    if path.exists() and path.read_bytes() == body:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.tmp')
    tmp.write_bytes(body)
    tmp.replace(path)
    return True


def serialize(rows):
    names = list(dict.fromkeys(k for r in rows for k in r))
    buf = io.StringIO(newline='')
    w = csv.DictWriter(buf, fieldnames=names)
    w.writeheader()
    for row in rows:
        w.writerow({k: json.dumps(v, ensure_ascii=False, separators=(',', ':')) if isinstance(v, (list,dict))
                    else '' if v is None else v for k,v in row.items()})
    cb = buf.getvalue().encode()
    jb = ''.join(json.dumps(r, ensure_ascii=False, separators=(',', ':')) + '\n' for r in rows).encode()
    actual = list(csv.DictReader(io.StringIO(cb.decode())))
    assert len(actual) == len(rows)
    for a,b in zip(actual, rows):
        for k in names:
            v = b.get(k)
            expected = json.dumps(v, ensure_ascii=False, separators=(',', ':')) if isinstance(v,(dict,list)) else '' if v is None else str(v)
            assert a[k] == expected, (k,a[k],expected)
    return cb,jb


def contains(w,b):
    return b[0] <= (w['x0']+w['x1'])/2 < b[2] and b[1] <= (w['top']+w['bottom'])/2 < b[3]


class Producer:
    def __init__(self, source=ORIGINAL):
        import pdfplumber
        self.source = Path(source)
        # No output is touched before the reviewed source has passed SHA check.
        if not self.source.is_file():
            raise FileNotFoundError('Required reviewed PDF missing; prior outputs retained')
        if sha(self.source.read_bytes()) != REVIEWED_SHA:
            raise ValueError('Original source changed: stop for new image review; prior outputs retained')
        self.meta = json.loads(ORIGINAL_META.read_text())
        if self.meta['sha256'] != REVIEWED_SHA:
            raise ValueError('Source metadata version differs; prior outputs retained')
        self.pdf = pdfplumber.open(self.source)
        self.pages = {n:self.pdf.pages[n-1].dedupe_chars(tolerance=.2) for n in (13,14,15,16,34)}
        self.words = {n:p.extract_words(x_tolerance=1,y_tolerance=2) for n,p in self.pages.items()}
        self.programmes, self.quantities, self.audit, self.issues = [],[],[],[]
        self.consumed = []

    def numeric(self,pno,bbox,expected_words=1):
        matches = [w for w in self.words[pno] if contains(w,bbox)]
        if len(matches) != expected_words or not all(NUMBER.fullmatch(w['text']) for w in matches):
            raise ValueError(('Expected original numeric words',pno,bbox,matches))
        if expected_words != 1:
            for word in matches:
                wb=(word['x0']-.1,word['top']-.1,word['x1']+.1,word['bottom']+.1)
                chars=sorted([c for c in self.pages[pno].chars if contains(c,wb)],key=lambda c:c['x0'])
                assert ''.join(c['text'] for c in chars).strip()==word['text'],'Period word/char roundtrip failed'
            return matches
        word = matches[0]
        chars = sorted([c for c in self.pages[pno].chars if contains(c,bbox)],key=lambda c:c['x0'])
        raw = ''.join(c['text'] for c in chars).strip()
        if raw != word['text']:
            raise ValueError(('Word/character roundtrip failed',pno,bbox,raw,word))
        value = str(Decimal(raw.replace(',','')))
        self.consumed.append((pno,round(word['x0'],3),round(word['top'],3),raw))
        return raw,value

    def common(self,table,pno,row,column,bbox):
        printed = pno+18
        return dict(source_id=SOURCE_ID,source_parent_id=self.meta['source_id'],
                    source_url=self.meta['source_page_url'],source_download_url=self.meta['source_download_url'],
                    source_sha256=REVIEWED_SHA,source_local_path=self.meta['source_local_path'],
                    source_agency='國家圖書館',source_retrieved_at=self.meta['source_retrieved_at'],
                    source_title='中華民國九十五年圖書館年鑑／公共圖書館',source_edition_roc=95,
                    source_version_id=SOURCE_ID+':'+REVIEWED_SHA,publication_date='2006-11-01',
                    publication_date_basis='官方卷入口明列，非資料年或活動日期。',
                    source_table=str(table),source_table_title=TITLES[table],source_pdf_page=pno,
                    source_printed_page=str(printed),source_row=row,source_column=column,
                    source_locator=f'PDF page {pno}; printed page {printed}; table {table}; row {row}; column {column}; bbox '+','.join(f'{v:.3f}' for v in bbox),
                    source_cell_bbox=[round(v,3) for v in bbox],
                    source_location_kind='programme_table_row_or_merged_cell',
                    source_row_indexing='data-row sequence within original continued table; ranges identify right-hand merged cells; not a printed ordinal',
                    license_status='not_confirmed',license_url='https://www.ncl.edu.tw/open-government-declaration',
                    snapshot_distribution='not_in_public_bundle',source_report_reference_year=2005,
                    data_year=None,
                    geography_vintage='原表當時縣市及館名，未轉換現行22縣市或補館名後綴。',
                    source_footnotes_raw=None,source_footnotes_status='no_table_specific_note_printed',
                    extraction_status='PDFium_headers_labels_and_periods_reviewed; native_numeric_word_and_character_roundtrip')

    def period6(self):
        # Native numbers independently constrain the short image-transcribed
        # programme-period phrase; no day or individual-facility date invented.
        b=(430,344,470,360)
        assert [w['text'] for w in self.words[13] if contains(w,b)] == ['94','6']
        b=(365,361,415,378)
        assert [w['text'] for w in self.words[13] if contains(w,b)] == ['8','11']
        return dict(period_raw=PERIOD6,source_table_period_raw=None,
                    period_status='programme_window_in_preceding_text_not_individual_event_dates',
                    period_start=None,period_end=None,
                    period_start_month_candidate=f'{94+1911}-08',period_end_month_candidate=f'{94+1911}-11',
                    period_interpretation_basis='同句民國94年作計畫參照年，8至11月為各館陸續辦理窗；未逐館列日期，非全年年度值。',
                    period_source_pdf_page=13,period_source_printed_page='31',
                    period_source_bbox=[278,344,484,377],temporal_kind='programme_window_month_precision',
                    time_reference='94年6月核定後各館陸續於8月至11月辦理；原章另稱期程5個月，未以計算改字。')

    def quantity(self,parent,key,label,raw_value,bbox,column,unit_raw,*,role='reported_programme_quantity',unit=None):
        pno = parent['source_pdf_page']
        raw,value = self.numeric(pno,bbox)
        if raw_value is not None:
            assert raw == raw_value
        r = self.common(int(parent['source_table']),pno,parent['source_row'],column,bbox)
        r.update({k:v for k,v in parent.items() if k.startswith('period_') or k in ('time_reference','temporal_kind','source_reference_year_basis')})
        r.update(observation_id=parent['programme_id']+':'+key,programme_id=parent['programme_id'],
                 entity_raw=parent.get('facility_name_raw') or parent.get('activity_label_raw') or '總計',
                 source_row_label_raw=parent.get('source_row_label_raw') or parent.get('facility_name_raw') or parent.get('activity_label_raw'),
                 county_raw=parent.get('county_raw'),programme_type_raw=parent['programme_type_raw'],
                 metric_id=f'table{parent["source_table"]}_{key}',metric_raw=label,
                 source_column_path=parent['programme_type_raw']+'／'+label,
                 value_raw=raw,value=value,value_status='reported',unit_raw=unit_raw,unit=unit or unit_raw,
                 unit_status='printed_unit',unit_basis='原表欄頭或原格字尾明印；未把人視為去重人數。',
                 population_scope=parent['population_scope'],aggregation_role=role,
                 source_location_kind='programme_table_numeric_cell',
                 observation_identity_suffix=f'table{parent["source_table"]}:p{pno}:row{parent["source_row"]}:col{column}:{key}',
                 quality_flags=list(parent.get('quality_flags',[])),
                 notes='特定計畫／活動的原報數量，不是公共館全年營運量；同人可否重複計數原表未明示。',
                 original_fields={'programme_type':parent['programme_type_raw'],'entity_raw':parent.get('facility_name_raw'),
                                  'activity_label_raw':parent.get('activity_label_raw'),'metric_raw':label,
                                  'value_raw':raw,'unit_raw':unit_raw,'period_raw':parent.get('period_raw')})
        self.quantities.append(r)
        self.audit.append(dict(observation_id=r['observation_id'],source_pdf_page=pno,
                               source_table=r['source_table'],source_row=r['source_row'],source_column=column,
                               bbox=r['source_cell_bbox'],raw_value=raw,normalized_value=value,
                               method='deduplicated_original_word_and_char_exact_roundtrip'))
        return r

    def extract6(self):
        period = self.period6()
        ordinal = 0
        demo_ordinal = 0
        for pno in (14,15,16):
            c=COLS[pno]
            count_words=[w for w in self.words[pno] if c[2] <= w['x0'] < c[3]
                         and 145 < w['top'] < (595 if pno==16 else 670) and NUMBER.fullmatch(w['text'])]
            expected=sum(len(group[1]) for group in LAYOUT[pno])
            assert len(count_words)==expected,(pno,len(count_words),expected)
            count_words.sort(key=lambda w:w['top'])
            index=0
            for gi,(county,names,demo,state) in enumerate(LAYOUT[pno]):
                top,bottom=GROUP_BOUNDS[pno][gi:gi+2]
                first_ordinal=ordinal+1
                for name in names:
                    word=count_words[index];index+=1;ordinal+=1
                    box=(c[2],word['top']-1,c[3],word['bottom']+1)
                    r=self.common(6,pno,ordinal,'2–3',(c[1],word['top']-3,c[3],word['bottom']+3))
                    r.update(programme_id=f'ncl95-table6-reading-{ordinal:03}',record_kind='programme_facility_row',
                             programme_type_raw='推廣閱讀活動',county_raw=county,facility_name_raw=name,
                             facility_name_status='printed_source_label_retained',activity_label_raw=None,
                             source_field_bboxes={'county':[c[0],top,c[1],bottom],
                                                  'facility_name':[c[1],word['top']-3,c[2],word['bottom']+3],
                                                  'participant_count':list(box)},
                             population_scope='原表具名推廣閱讀活動之參加人數；人數是否跨場去重未明示。',
                             participation_status='reported_numeric_participation',non_numeric_state_raw=None,
                             source_value_annotation_raw=None,quality_flags=[],notes='原名原字保留，未改為現行館名或另補地理字。')
                    r.update(period)
                    if name=='太武鄉立圖書館':
                        r['quality_flags'].append('printed_facility_label_retained_unresolved_not_geocoded')
                        r['notes']+='原表在臺東縣印太武鄉立圖書館；不按其他地理知識替換館名或轉縣市，未驗證機構身分。'
                    q=self.quantity(r,'participants','參加人數（人）',word['text'],box,3,'人')
                    r['quantities']=[{'observation_id':q['observation_id'],'metric_id':q['metric_id'],'value_raw':q['value_raw'],'value':q['value'],'unit_raw':q['unit_raw']}]
                    self.programmes.append(r)
                demo_ordinal+=1
                rowrange=f'{first_ordinal}–{ordinal}' if first_ordinal!=ordinal else str(ordinal)
                box=(c[3],top,c[5],bottom)
                r=self.common(6,pno,rowrange,'4–5',box)
                r.update(programme_id=f'ncl95-table6-demonstration-{demo_ordinal:02}',
                         record_kind='programme_merged_county_slot',programme_type_raw='示範觀摩館',
                         county_raw=county,facility_name_raw=demo if state is None else None,
                         facility_name_status='printed_source_label_retained' if state is None else state,
                         activity_label_raw=None,source_field_bboxes={'county':[c[0],top,c[1],bottom],
                                                                   'facility_name':[c[3],top,c[4],bottom],
                                                                   'participant_count':[c[4],top,c[5],bottom]},
                         population_scope='原表按縣市合併欄的一個示範觀摩館紀錄；不逐左側館列重複展開。',
                         participation_status='reported_numeric_participation' if state is None else state,
                         non_numeric_state_raw=demo if state else None,source_value_annotation_raw=None,
                         quality_flags=[],notes='右側縣市合併格只記一次；未複製到每個左側活動列。')
                r.update(period)
                if state is None:
                    ws=[w for w in self.words[pno] if c[4] <= w['x0'] < c[5] and top < (w['top']+w['bottom'])/2 < bottom]
                    assert len(ws)==1 and NUMBER.fullmatch(ws[0]['text']),(pno,county,ws)
                    w=ws[0];qb=(c[4],w['top']-1,c[5],w['bottom']+1)
                    q=self.quantity(r,'participants','參加人數（人）',w['text'],qb,5,'人')
                    r['quantities']=[{'observation_id':q['observation_id'],'metric_id':q['metric_id'],'value_raw':q['value_raw'],'value':q['value'],'unit_raw':q['unit_raw']}]
                else:
                    assert not [w for w in self.words[pno] if contains(w,box)]
                    r['quantities']=[]
                    r['source_field_bboxes']={'merged_facility_and_participant_state':list(box),'county':[c[0],top,c[1],bottom]}
                    r['notes']+='原合併欄明印不參加，不是數值0。' if state=='source_marker' else '原右側整格留白，原因未確認；不視為不參加、0或不適用。'
                    self.audit.append(dict(programme_id=r['programme_id'],source_pdf_page=pno,
                                           source_table='6',source_row=rowrange,source_column='4–5',bbox=list(box),
                                           raw_value=demo,normalized_value=None,value_status=state,
                                           method='PDFium_image_transcribed_Chinese_outlines_or_visual_blank; native_text_empty'))
                self.programmes.append(r)
        assert ordinal==88 and demo_ordinal==23
        # Four printed totals are distinct source cells, never computed values.
        c=COLS[16]
        for kind,cols in [('推廣閱讀活動',(2,3)),('示範觀摩館',(4,5))]:
            left,right=cols
            r=self.common(6,16,89,f'{left}–{right}',(c[left-1],594.967,c[right],611.626))
            r.update(programme_id='ncl95-table6-total-'+('reading' if left==2 else 'demonstration'),
                     record_kind='printed_programme_total',programme_type_raw=kind,county_raw=None,
                     facility_name_raw=None,facility_name_status='not_applicable_summary_row',activity_label_raw=None,
                     source_row_label_raw='總計',population_scope='本原表所列該計畫總計，不是全臺公共館數量。',
                     participation_status='printed_total',non_numeric_state_raw=None,
                     source_value_annotation_raw=None,quality_flags=['published_total_overlaps_programme_components'],
                     notes='原印總計；館數與參加人數是不同指標，不相加。')
            r.update(period)
            qq=[]
            for col,key,label,unit in [(left,'facilities','圖書館名稱','館'),(right,'participants','參加人數（人）','人')]:
                bbox=(c[col-1],599,c[col],611)
                q=self.quantity(r,key,label,None,bbox,col,unit,role='published_programme_total')
                q['source_value_annotation_raw']=q['value_raw']+unit
                qq.append({'observation_id':q['observation_id'],'metric_id':q['metric_id'],'value_raw':q['value_raw'],'value':q['value'],'unit_raw':unit})
            r['quantities']=qq
            self.programmes.append(r)

    def extract7(self):
        for i,label in enumerate(ACTIVITIES7,1):
            top=327.898+(i-1)*16.6535
            bbox=(86.69,top-3,482.48,top+11.5)
            r=self.common(7,34,i,'2–4',bbox)
            r.update(programme_id=f'ncl95-table7-activity-{i:02}',record_kind='programme_activity_row',
                     programme_type_raw='全國閱讀運動',county_raw=None,facility_name_raw=None,
                     facility_name_status='not_a_facility_row',activity_label_raw=label,
                     participation_status='reported_activity',non_numeric_state_raw=None,
                     population_scope='原表列示的特定全國閱讀運動活動，非公共館全年營運合計。',
                     source_field_bboxes={'ordinal':[56.8,top-3,86.69,top+11.5],
                                          'activity':[86.69,top-3,313.455,top+11.5],
                                          'count_or_period':[313.455,top-3,423.618,top+11.5],
                                          'participants':[423.618,top-3,482.48,top+11.5]},
                     period_raw=None,source_table_period_raw=None,period_status='not_printed_in_this_activity_row',
                     period_start=None,period_end=None,period_start_month_candidate=None,period_end_month_candidate=None,
                     period_interpretation_basis='本活動列未印期間；不由報告參照年或其他活動的期間補成整年。',
                     period_source_pdf_page=34,period_source_printed_page='52',period_source_bbox=None,
                     temporal_kind='programme_activity_period_unknown',time_reference='原列未印期間；出版日不是活動日。',
                     quality_flags=[],notes='原列活動標籤及數量照印，未收錄周邊大段署名正文或個人資料。')
            ordinal=self.numeric(34,(56.8,top-1,86.69,top+9.5))
            # Ordinals are consumed separately; they are not statistical quantities.
            assert ordinal[0]==str(i)
            self.consumed.pop()
            qq=[]
            if i<=4:
                q=self.quantity(r,'events','辦理場次／辦理時間',None,(313.455,top-1,423.618,top+9.5),3,'次')
                q['source_value_annotation_raw']=q['value_raw']+'次'
                qq.append({'observation_id':q['observation_id'],'metric_id':q['metric_id'],'value_raw':q['value_raw'],'value':q['value'],'unit_raw':'次'})
            else:
                words=self.numeric(34,(313.455,top-1,423.618,top+9.5),expected_words=4 if i==5 else 3)
                digits=[int(w['text']) for w in sorted(words,key=lambda w:w['x0'])]
                expected=[94,12,95,5] if i==5 else [95,4,5]
                assert digits==expected,('Original period numeric tokens differ',i,digits)
                start_year,start_month,end_year,end_month=(digits[0]+1911,digits[1],digits[2]+1911,digits[3]) if i==5 else (digits[0]+1911,digits[1],digits[0]+1911,digits[2])
                period='94年12月至95年5月' if i==5 else '95年4月至5月'
                r.update(period_raw=period,source_table_period_raw=period,
                         period_status='printed_month_range_not_calendar_year',
                         period_start_month_candidate=f'{start_year}-{start_month:02}',
                         period_end_month_candidate=f'{end_year}-{end_month:02}',
                         period_interpretation_basis='原期中文字依PDFium核讀，全部年/月數字與原生PDF word逐一吻合；民國年加1911；未補起訖日。',
                         period_source_bbox=[313.455,round(top-3,3),423.618,round(top+11.5,3)],
                         temporal_kind='programme_interval_month_precision',
                         time_reference=period+'；保留跨年或次年期間，不歸為2005全年。')
                self.audit.append(dict(programme_id=r['programme_id'],source_table='7',source_pdf_page=34,
                                       source_row=i,source_column=3,bbox=r['period_source_bbox'],
                                       raw_period=period,native_numeric_tokens=[w['text'] for w in sorted(words,key=lambda w:w['x0'])],
                                       converted_start_month_candidate=r['period_start_month_candidate'],
                                       converted_end_month_candidate=r['period_end_month_candidate'],
                                       method='image_transcribed_Chinese_period_words; original_native_numeric_tokens_verified; ROC_year_plus1911'))
            q=self.quantity(r,'participants','參加人數',None,(423.618,top-1,482.48,top+9.5),4,'人')
            q['source_value_annotation_raw']=q['value_raw']+'人'
            qq.append({'observation_id':q['observation_id'],'metric_id':q['metric_id'],'value_raw':q['value_raw'],'value':q['value'],'unit_raw':'人'})
            r['quantities']=qq
            self.programmes.append(r)

    def validate(self):
        assert len(self.programmes)==119,len(self.programmes)
        assert len(self.quantities)==123,len(self.quantities)
        assert len({r['programme_id'] for r in self.programmes})==119
        assert len({r['observation_id'] for r in self.quantities})==123
        assert len(set(self.consumed))==len(self.consumed)==123
        assert all(r['data_year'] is None for r in self.programmes+self.quantities)
        for r in self.quantities:
            assert r['value']==str(Decimal(r['value_raw'].replace(',','')))
            assert r['source_sha256']==REVIEWED_SHA and r['source_cell_bbox']
        # Complete selected numeric regions, excluding headers/page numbers,
        # table7 printed ordinals and period tokens (separately audited).
        all_tokens=[]
        for n in (14,15,16):
            c=COLS[n]
            for w in self.words[n]:
                if not NUMBER.fullmatch(w['text']):continue
                centre=(w['top']+w['bottom'])/2
                if 145<centre<(612 if n==16 else 670) and c[1] <= w['x0'] < c[5]:
                    all_tokens.append((n,round(w['x0'],3),round(w['top'],3),w['text']))
        for w in self.words[34]:
            centre=(w['top']+w['bottom'])/2
            if NUMBER.fullmatch(w['text']) and 326<centre<422 and (w['x0']>=423.618 or (313.455<=w['x0']<423.618 and centre<390)):
                all_tokens.append((34,round(w['x0'],3),round(w['top'],3),w['text']))
        if Counter(all_tokens)!=Counter(self.consumed):
            raise ValueError(('Unconsumed/duplicate numeric quantity tokens',Counter(all_tokens)-Counter(self.consumed),Counter(self.consumed)-Counter(all_tokens)))
        # Diagnose sums/counts; printed totals always remain the source values.
        for kind in ('推廣閱讀活動','示範觀摩館'):
            rows=[r for r in self.programmes if r['source_table']=='6' and r['programme_type_raw']==kind and r['record_kind']!='printed_programme_total']
            quantities=[q for r in rows for q in r['quantities']]
            totalrow=next(r for r in self.programmes if r['record_kind']=='printed_programme_total' and r['programme_type_raw']==kind)
            totals={q['metric_id'].split('_')[-1]:q for q in totalrow['quantities']}
            count=len(quantities)
            total=sum(Decimal(q['value']) for q in quantities)
            result=dict(programme=kind,listed_numeric_facility_rows=count,
                        printed_facilities=totals['facilities']['value'],component_participants_sum=str(total),
                        printed_participants=totals['participants']['value'])
            if count!=int(totals['facilities']['value']) or total!=Decimal(totals['participants']['value']):
                result['flag']='source_printed_total_differs_from_listed_components'
                result['difference_printed_minus_components']=str(Decimal(totals['participants']['value'])-total)
                totalrow['quality_flags'].append(result['flag'])
                totalrow['notes']+='原印參加人數總計與逐館數字加總不同，未覆寫任何來源格。'
                q=next(q for q in self.quantities if q['programme_id']==totalrow['programme_id'] and q['metric_id']=='table6_participants')
                q['quality_flags'].append(result['flag'])
                q['notes']+='原印總計'+q['value_raw']+'與原列數字加總'+str(total)+'不同，保留原總計。'
            self.issues.append(result)

    def write(self):
        self.validate()
        pc,pj=serialize(self.programmes);qc,qj=serialize(self.quantities)
        metadata=dict(schema_version='ncl_programmes_source_rows_and_quantities_v1',
                      source_report_reference_year=2005,data_year_policy='data_year stays null; source-report reference year and row-specific programme periods are independent',
                      source_edition_roc=95,publication_date='2006-11-01',source_id=SOURCE_ID,
                      source_url=self.meta['source_page_url'],source_download_url=self.meta['source_download_url'],
                      source_sha256=REVIEWED_SHA,source_local_path=self.meta['source_local_path'],
                      records=dict(programme_rows=119,numeric_quantity_cells=123,
                                   table6=dict(reading_facility_rows=88,demonstration_county_slots=23,
                                               demonstration_numeric_facility_rows=21,nonparticipating_marker_slots=1,
                                               blank_slots_reason_unknown=1,printed_summary_rows=2,numeric_cells=113),
                                   table7=dict(activity_rows=6,numeric_cells=10,explicit_period_cells=2,period_unknown_rows=4)),
                      tables=[dict(table=6,title=TITLES[6],pdf_pages=[14,15,16],printed_pages=['32','33','34'],
                                   column_headers_raw=['縣市別','推廣閱讀活動／圖書館名稱','推廣閱讀活動／參加人數（人）','示範觀摩館／圖書館名稱','示範觀摩館／參加人數（人）'],
                                   completeness='entire continued table including right merged cells, explicit不參加, blank嘉義市slot and four printed totals'),
                              dict(table=7,title=TITLES[7],pdf_pages=[34],printed_pages=['52'],
                                   column_headers_raw=['項次','活動內容','辦理場次／辦理時間','參加人數'],
                                   completeness='all six rows, four printed event counts, six participant counts and two exact month-range cells')],
                      scope_limits=['programme-specific data, not annual public-library operating totals or complete nationwide facility registry',
                                    'right-hand merged county slots are recorded once, never repeated for left-hand facilities',
                                    'blank and 不參加 are nonnumeric listing states, not invented numeric zeros',
                                    'source county and complete facility labels retained verbatim; 太武鄉立圖書館 under臺東縣 is not silently reassigned',
                                    'source參加人數（人） does not establish unique people across events/programmes',
                                    'date candidates preserve month precision; no exact days filled; first four table7 rows have null periods'],
                      source_context_issues=[
                          dict(issue='preceding_text_vs_table_facility_count_disagreement',source_context_pdf_page=13,source_context_printed_page='31',
                               source_context_short_fact='推廣閱讀活動正文稱91館，表6總計88館；全部原表值保留，不用正文改表。'),
                          dict(issue='programme_window_and_duration_wording_not_harmonized',source_context_pdf_page=13,
                               source_context_short_fact='同段明印8月至11月展開辦理，也稱執行期程5個月；未自行改月份或期程。')],
                      component_checks=self.issues,
                      rights=dict(license_status='not_confirmed',license_url='https://www.ncl.edu.tw/open-government-declaration',
                                  basis='Publication and authored-text rights not confirmed open; extracted factual labels/quantities/necessary period notes only. Full PDF, HTML, OCR/full text and images stay private.',
                                  full_originals_distribution='not_in_public_bundle'),
                      dependencies=['Python3.12 standard library','pdfplumber','scripts/extract_ncl_2005_programmes.py'],
                      evidence=dict(private_source_images='Maintainer-side original page images/crops; not in the public distribution or required to run the extractor.',
                                    existing_images=['raw/ncl-2005/public-library-p14-hires.private.png','raw/ncl-2005/public-library-p34-hires.private.png'],
                                    image_review_method='PDFium full pages plus source-only crops; glyph/label review by producer, not human double proofreading'),
                      output_statistics=[dict(path=path,sha256=sha(body),bytes=len(body)) for path,body in zip(OUTPUTS[:4],(pc,pj,qc,qj))])
        mb=(json.dumps(metadata,ensure_ascii=False,indent=2)+'\n').encode()
        ab=(json.dumps(self.audit,ensure_ascii=False,indent=2)+'\n').encode()
        # Everything validates/serializes before replacing any successful file.
        for path,body in zip(OUTPUTS,(pc,pj,qc,qj,mb,ab)):
            stable_write(BASE/path,body)
        inputs=['scripts/extract_ncl_2005_programmes.py','raw/ncl-2005/yearbook-95-public-library.pdf',
                'raw/ncl-2005/yearbook-95-public-library.metadata.json']
        manifest=dict(producer_inputs=[dict(path=p,sha256=sha((BASE/p).read_bytes()),bytes=(BASE/p).stat().st_size) for p in inputs],
                      producer_outputs=[dict(path=p,sha256=sha((BASE/p).read_bytes()),bytes=(BASE/p).stat().st_size) for p in OUTPUTS],
                      cache_contract='source SHA and all input/output hashes must match; unchanged outputs keep bytes/mtime; missing/changed source stops before output mutation',
                      unchanged_outputs_keep_mtime=True,full_originals_distribution='not_in_public_bundle')
        stable_write(RAW/'incremental-contract.json',json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
        print(json.dumps(metadata['records'],ensure_ascii=False))

    def close(self):
        self.pdf.close()


def self_test():
    def snapshot():
        return {p:(sha((BASE/p).read_bytes()),(BASE/p).stat().st_mtime_ns) for p in OUTPUTS+['raw/ncl-2005-programmes/incremental-contract.json']}
    before=snapshot()
    for _ in range(2):
        subprocess.run([sys.executable,str(Path(__file__).resolve()),'--offline'],cwd=BASE,
                       env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'),check=True,
                       stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    assert snapshot()==before,'no-op changed output bytes or mtime'
    fixtures=[]
    for fault in ('missing','changed'):
        with tempfile.TemporaryDirectory(prefix='ncl95-programme-input-fixture-') as td:
            path=Path(td)/'source.pdf'
            if fault=='changed':path.write_bytes(b'%PDF-synthetic changed-version fixture, not a source')
            try:
                p=Producer(source=path)
            except (FileNotFoundError,ValueError) as e:
                fixtures.append(dict(fault=fault,error=type(e).__name__,previous_outputs_untouched=snapshot()==before))
            else:
                p.close();raise AssertionError('bad source accepted')
    assert all(x['previous_outputs_untouched'] for x in fixtures)
    result=dict(programme_rows=119,numeric_cells=123,complete_table6_numeric_cells=113,
                complete_table7_numeric_cells=10,nonparticipating_marker_slots=1,blank_slots=1,
                checks=dict(full_selected_tables=True,unique_programme_and_quantity_ids=True,
                            all_original_numeric_words_and_characters_roundtrip=True,
                            all_selected_numeric_tokens_consumed_once=True,csv_jsonl_every_field_equal=True,
                            no_op_bytes_and_mtime_two_runs=True,failure_preserves_previous_outputs=fixtures),
                limits='producer source verification is not official reporting correctness or human double proofreading')
    stable_write(RAW/'verification.json',json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(result,ensure_ascii=False))


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--offline',action='store_true',help='Use reviewed existing PDF only (all modes are local and never download).')
    ap.add_argument('--self-test',action='store_true',help='After successful extraction, verify no-op and failure-preserves-prior fixtures.')
    args=ap.parse_args()
    p=Producer()
    try:
        p.extract6();p.extract7();p.write()
    finally:
        p.close()
    if args.self_test:self_test()


if __name__=='__main__':main()
