#!/usr/bin/env python3
"""All four reviewed local-library ODS/XLSX source-cell batches, offline.

Stdlib XML/ZIP parsing preserves original stored values, formatted ODS text,
styles, formula/cache distinction, merged cells and source coordinates. No
spreadsheet is edited/recalculated. No source-period conflict is resolved by
guessing, and no result is inserted into the annual canonical dataset.
"""
from __future__ import annotations
import argparse
from collections import Counter
import csv
from decimal import Decimal, InvalidOperation
import hashlib
import io
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as E
import zipfile

BASE=Path(__file__).resolve().parents[1]
RAW=BASE/'raw/phase1_local_sources'
DEFAULT_SOURCE_ROOT=Path(os.environ.get('TW_LIBRARY_PHASE1_SOURCE_ROOT',str(RAW/'originals')))
MANIFEST=RAW/'sources.json'
T='{urn:oasis:names:tc:opendocument:xmlns:table:1.0}'
O='{urn:oasis:names:tc:opendocument:xmlns:office:1.0}'
X='{urn:oasis:names:tc:opendocument:xmlns:text:1.0}'
S='{urn:oasis:names:tc:opendocument:xmlns:style:1.0}'
SS='{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'
RR='{http://schemas.openxmlformats.org/officeDocument/2006/relationships}'
PKG='{http://schemas.openxmlformats.org/package/2006/relationships}'
OUTPUTS=['derived/phase1_local_sources_cells.csv','derived/phase1_local_sources_cells.jsonl',
         'derived/phase1_local_sources_long.csv','derived/phase1_local_sources_long.jsonl']
MARKERS={'-','－','—','–','…','...','NA','N/A','無'}


def sha(b):return hashlib.sha256(b).hexdigest()


def write(path,b):
    b=b.encode() if isinstance(b,str) else b
    if path.exists() and path.read_bytes()==b:return
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_name(path.name+'.tmp');tmp.write_bytes(b);tmp.replace(path)


def colnum(text):
    v=0
    for c in text:v=v*26+ord(c)-64
    return v


def colname(n):
    out=''
    while n:n,r=divmod(n-1,26);out=chr(65+r)+out
    return out


def coord(r,c):return colname(c)+str(r)


def uncoord(c):
    m=re.fullmatch(r'([A-Z]+)(\d+)',c)
    return int(m[2]),colnum(m[1])


def odf_text(node):
    def rec(e):
        if e.tag==X+'s':return ' '*int(e.get(X+'c','1'))
        if e.tag==X+'tab':return '\t'
        if e.tag==X+'line-break':return '\n'
        return (e.text or '')+''.join(rec(c)+(c.tail or '') for c in e)
    return '\n'.join(rec(p) for p in node.findall(X+'p'))


def empty_cell():
    return dict(display_raw='',stored_raw=None,native_type=None,formula_raw=None,
                style_name=None,number_format_raw=None,covered=False,merge_origin=None,
                merge_range=None,xml_present=False,display_basis='not_present_in_bounded_source_region')


def parse_ods(path):
    with zipfile.ZipFile(path) as z:
        root=E.fromstring(z.read('content.xml'))
        stylemap={}
        for xml in ('styles.xml','content.xml'):
            if xml in z.namelist():
                for s in E.fromstring(z.read(xml)).findall('.//'+S+'style'):
                    stylemap[s.get(S+'name')]=dict(parent=s.get(S+'parent-style-name'),number=s.get(S+'data-style-name'))
        def fmt(name):
            seen=set()
            while name and name not in seen:
                seen.add(name);s=stylemap.get(name,{})
                if s.get('number'):return s['number']
                name=s.get('parent')
            return None
        sheets=[]
        for table in root.findall('.//'+T+'table'):
            segments=[];rr=1;last_row=0;last_col=0;declared_cols=0
            for row in table.findall(T+'table-row'):
                nr=int(row.get(T+'number-rows-repeated','1'));cc=1
                for cell in row:
                    if cell.tag not in {T+'table-cell',T+'covered-table-cell'}:continue
                    nc=int(cell.get(T+'number-columns-repeated','1'))
                    display=odf_text(cell);stored=cell.get(O+'value',cell.get(O+'date-value',cell.get(O+'boolean-value',cell.get(O+'string-value'))))
                    native=cell.get(O+'value-type');formula=cell.get(T+'formula')
                    span_c=int(cell.get(T+'number-columns-spanned','1'));span_r=int(cell.get(T+'number-rows-spanned','1'))
                    obj=dict(display_raw=display,stored_raw=stored,native_type=native,
                             formula_raw=formula,style_name=cell.get(T+'style-name'),
                             number_format_raw=fmt(cell.get(T+'style-name')),
                             covered=cell.tag==T+'covered-table-cell',merge_origin=None,merge_range=None,
                             xml_present=True,display_basis='ODS text:p with text:s/tab/line-break expanded exactly')
                    segments.append((rr,nr,cc,nc,span_r,span_c,obj))
                    if display or stored is not None or formula:
                        last_row=max(last_row,rr+nr+span_r-2);last_col=max(last_col,cc+nc+span_c-2)
                    cc+=nc
                declared_cols=max(declared_cols,cc-1);rr+=nr
            if last_row>200000 or last_col>1024:raise ValueError('Unexpected source data dimensions; manual review required')
            cells={};merges={}
            for r,nr,c,nc,sr,sc,obj in segments:
                if r>last_row or c>last_col:continue
                for ri in range(r,min(r+nr,last_row+1)):
                    for ci in range(c,min(c+nc,last_col+1)):
                        cells[ri,ci]=dict(obj)
                        if sc>1 or sr>1:
                            rng=coord(ri,ci)+':'+coord(ri+sr-1,ci+sc-1)
                            for mr in range(ri,ri+sr):
                                for mc in range(ci,ci+sc):merges[mr,mc]=(coord(ri,ci),rng)
            for p,(origin,rng) in merges.items():
                if p in cells:cells[p].update(merge_origin=origin,merge_range=rng)
            sheets.append(dict(name=table.get(T+'name'),xml_part='content.xml',cells=cells,
                               used_rows=last_row,used_columns=last_col,
                               declared_rows=rr-1,declared_columns=declared_cols,
                               omitted_trailing_format_only_region='Repeated blank formatting rows/columns outside the actual nonempty used bounds are not observations.'))
        return sheets


def parse_xlsx(path):
    with zipfile.ZipFile(path) as z:
        strings=[]
        if 'xl/sharedStrings.xml' in z.namelist():
            for si in E.fromstring(z.read('xl/sharedStrings.xml')).findall(SS+'si'):
                strings.append(''.join(si.itertext()))
        formats={0:'General',1:'0',2:'0.00',3:'#,##0',4:'#,##0.00',9:'0%',10:'0.00%'}
        styleids=[]
        if 'xl/styles.xml' in z.namelist():
            st=E.fromstring(z.read('xl/styles.xml'))
            for n in st.findall(SS+'numFmts/'+SS+'numFmt'):formats[int(n.get('numFmtId'))]=n.get('formatCode')
            styleids=[int(x.get('numFmtId','0')) for x in st.findall(SS+'cellXfs/'+SS+'xf')]
        rels={r.get('Id'):r.get('Target') for r in E.fromstring(z.read('xl/_rels/workbook.xml.rels')).findall(PKG+'Relationship')}
        sheets=[]
        for ws in E.fromstring(z.read('xl/workbook.xml')).findall(SS+'sheets/'+SS+'sheet'):
            target=rels[ws.get(RR+'id')]
            part=target.lstrip('/') if target.startswith('/') else 'xl/'+target
            rt=E.fromstring(z.read(part));cells={}
            for c in rt.findall(SS+'sheetData/'+SS+'row/'+SS+'c'):
                r,n=uncoord(c.get('r'));v=c.find(SS+'v');stored=v.text if v is not None else None
                nt=c.get('t','n');f=c.find(SS+'f');style=int(c.get('s','0'))
                display=''
                if nt=='s' and stored is not None:display=strings[int(stored)];stored=display
                elif nt=='inlineStr':display=''.join(c.find(SS+'is').itertext());stored=display
                elif nt in {'str','e','b'}:display=stored or ''
                numfmt=styleids[style] if style<len(styleids) else 0
                cells[r,n]=dict(display_raw=display,stored_raw=stored,native_type=nt,
                                formula_raw=f.text if f is not None else None,
                                formula_attributes=dict(f.attrib) if f is not None else None,
                                style_name=str(style),number_format_raw=formats.get(numfmt,'builtin_numFmtId:'+str(numfmt)),
                                number_format_id=numfmt,covered=False,merge_origin=None,merge_range=None,
                                xml_present=True,display_basis='original shared/inline string' if nt in {'s','str','inlineStr'} else
                                'formatted display not stored in XLSX XML; original cached numeric value and number format preserved, not rendered or recalculated')
            for m in rt.findall(SS+'mergeCells/'+SS+'mergeCell'):
                start,end=m.get('ref').split(':');r0,c0=uncoord(start);r1,c1=uncoord(end)
                for r in range(r0,r1+1):
                    for c in range(c0,c1+1):
                        obj=cells.setdefault((r,c),empty_cell());obj.update(merge_origin=start,merge_range=m.get('ref'),covered=(r,c)!=(r0,c0))
            nonempty=[p for p,c in cells.items() if c['display_raw'] or c['stored_raw'] is not None or c['formula_raw']]
            dim=rt.find(SS+'dimension')
            sheets.append(dict(name=ws.get('name'),sheet_id=ws.get('sheetId'),xml_part=part,cells=cells,
                               used_rows=max((p[0] for p in nonempty),default=0),used_columns=max((p[1] for p in nonempty),default=0),
                               declared_dimension=dim.get('ref') if dim is not None else None))
        return sheets


def text(sheet,r,c):
    x=sheet['cells'].get((r,c),empty_cell())
    return x['display_raw'] if x['display_raw']!='' else x['stored_raw'] or ''


def at(sheet,r,c):return sheet['cells'].get((r,c),empty_cell())


def numeric_state(cell):
    raw=cell['display_raw'];stored=cell['stored_raw'];nt=cell['native_type'];display=raw.strip()
    typed=None
    if stored is not None and nt in {'float','percentage','currency','n'}:
        try:typed=str(Decimal(stored))
        except InvalidOperation:pass
    if cell['covered']:return None,'source_covered_cell',typed
    if typed is not None and display in MARKERS:
        return None,'source_display_typed_value_conflict_unresolved',typed
    if display in MARKERS:return None,'source_marker',typed
    if typed is not None:return typed,'reported_typed_numeric',typed
    if display and re.fullmatch(r'[-+]?\d[\d,]*(?:\.\d+)?',display):
        return str(Decimal(display.replace(',',''))),'reported_numeric_text',None
    if raw=='' and stored is None:return None,'blank_in_source',None
    return None,'source_text',None


def period(source,sheet):
    if source['source_filename']=='lienchiang-113-overview.ods':
        return dict(period_raw=None,source_sheet_period_raw=None,source_catalog_period_raw='113年',
                    period_year_candidate=113+1911,period_month_candidate=None,period_year=113+1911,period_month=None,
                    period_status='catalog_title_year_only_attachment_undated',period_basis='官方目錄題名113年；附件本身未列年度，未借用114版本定義補精確時點。',period_candidates={'catalog_year':2024})
    raw=text(sheet,4,1) if source['format']=='XLSX' else text(sheet,6,1)
    if source['format']=='XLSX':
        m=re.search(r'(\d+)\s*年',raw)
        if not m:raise ValueError('Missing original year header')
        return dict(period_raw=raw,source_sheet_period_raw=raw,source_catalog_period_raw='114年',
                    period_year=int(m[1])+1911,period_month=None,period_year_candidate=int(m[1])+1911,period_month_candidate=None,
                    period_status='explicit_sheet_year',period_basis='原工作表A4明印年度；未以出版日替代。',period_candidates={'header_year':int(m[1])+1911})
    a=re.search(r'(\d+)年\s*(\d+)月',raw);b=re.search(r'(\d+)年(\d+)月',sheet['name'])
    if not a and sheet['name']=='空白':
        return dict(period_raw=raw,source_sheet_period_raw=raw,period_year=None,period_month=None,
                    period_year_candidate=None,period_month_candidate=None,period_status='blank_template_not_data',period_basis='空白樣表，不增加統計觀測。',period_candidates={})
    if not a or not b:raise ValueError(('Unknown period schema',sheet['name'],raw))
    header={'roc_year':int(a[1]),'year':int(a[1])+1911,'month':int(a[2])}
    label={'roc_year':int(b[1]),'year':int(b[1])+1911,'month':int(b[2])}
    match=header==label
    return dict(period_raw=raw,source_sheet_period_raw=raw,source_catalog_period_raw=None,
                period_year=header['year'] if match else None,period_month=header['month'] if match else None,
                period_year_candidate=None if not match else header['year'],period_month_candidate=None if not match else header['month'],
                period_status='matching_sheet_name_and_header_month' if match else 'source_sheet_name_header_period_conflict_unresolved',
                period_basis='原表A6與工作表名皆保留；矛盾時正式期間未知，不選任一候選。',
                period_candidates={'header':header,'sheet_name':label})


def serialize(rows):
    names=list(dict.fromkeys(k for r in rows for k in r));buf=io.StringIO(newline='');w=csv.DictWriter(buf,fieldnames=names);w.writeheader()
    for r in rows:w.writerow({k:json.dumps(v,ensure_ascii=False,separators=(',',':')) if isinstance(v,(dict,list)) else '' if v is None else v for k,v in r.items()})
    cb=buf.getvalue().encode();jb=''.join(json.dumps(r,ensure_ascii=False,separators=(',',':'))+'\n' for r in rows).encode()
    rr=list(csv.DictReader(io.StringIO(cb.decode())))
    assert len(rr)==len(rows)
    for a,b in zip(rr,rows):
        for k in names:
            v=b.get(k);expected=json.dumps(v,ensure_ascii=False,separators=(',',':')) if isinstance(v,(dict,list)) else '' if v is None else str(v)
            assert a[k]==expected,('CSV/JSONL mismatch',k)
    return cb,jb


class Producer:
    def __init__(self,source_override=None,source_root=DEFAULT_SOURCE_ROOT):
        self.sources=json.loads(MANIFEST.read_text())['sources'];self.cells=[];self.long=[];self.metadata=[]
        self.paths={}
        for source in self.sources:
            path=Path(source_override) if source_override else Path(source_root)/source['source_filename']
            if not path.is_file():raise FileNotFoundError('Required reviewed source missing; old outputs retained: '+source['source_filename'])
            if sha(path.read_bytes())!=source['source_sha256']:raise ValueError('Source SHA changed; stop for new review before replacing outputs: '+source['source_filename'])
            self.paths[source['source_id']]=path

    def base(self,s,sh,r,c,role):
        obj=at(sh,r,c);value,status,typed=numeric_state(obj)
        raw=obj['display_raw'] if obj['display_raw']!='' else obj['stored_raw']
        return dict(source_id=s['source_id'],source_url=s['source_url'],source_download_url=s['source_download_url'],
                    source_sha256=s['source_sha256'],source_version_id=s['source_id']+':'+s['source_sha256'],
                    source_agency=s['source_agency'],source_title=s['source_title'],source_retrieved_at=s['source_retrieved_at'],
                    source_sheet=sh['name'],source_sheet_xml_part=sh['xml_part'],source_row=r,source_column=c,source_cell=coord(r,c),
                    source_locator=f"sheet {sh['name']}; cell {coord(r,c)}; {sh['xml_part']}",
                    source_cell_role=role,value_raw=raw,source_display_raw=obj['display_raw'],source_stored_value_raw=obj['stored_raw'],
                    source_native_value_type=obj['native_type'],source_formula_raw=obj['formula_raw'],source_formula_attributes=obj.get('formula_attributes'),
                    source_style_name=obj['style_name'],source_number_format_raw=obj['number_format_raw'],
                    source_display_basis=obj['display_basis'],source_merge_origin=obj['merge_origin'],source_merge_range=obj['merge_range'],
                    source_covered_cell=obj['covered'],source_xml_cell_present=obj['xml_present'],
                    value=value,value_status=status,source_typed_numeric_value=typed,
                    license_status=s['license_status'],license_url=s['license_url'],snapshot_distribution='not_in_public_bundle')

    def emit(self,s,sh,r,c,labels,pp,notes,entity,metric,unit_raw,*,dimension=None):
        rec=self.base(s,sh,r,c,'statistical_data_cell')
        rec.update(observation_id=s['source_id']+':'+sh['name']+':'+coord(r,c),county=s['county'],
                   entity_raw=entity,metric_raw=metric,source_row_label_raw=labels,
                   source_column_path=dimension or entity,source_header_hierarchy_raw=dimension or entity,
                   unit_raw=unit_raw,unit=None if ('人數' in metric or '人次(人)' in metric) else unit_raw,
                   unit_status='source_counting_basis_unresolved' if ('人數' in metric or '人次(人)' in metric) else 'printed_header_unit',
                   unit_basis='原統計表列／多層欄頭或全表單位原字；未把人數、人次混同。',
                   source_notes=notes,aggregation_role='published_total_overlaps_components' if labels=='總計' or entity=='總計' or dimension and dimension[-1]=='總計' else 'reported_component',
                   temporal_kind='monthly_source_statistic' if pp.get('period_month') or 'header' in pp['period_candidates'] else 'annual_source_statistic_reference_date_not_assumed',
                   quality_flags=[])
        rec.update(pp)
        if rec['value_status']=='source_display_typed_value_conflict_unresolved':
            rec['quality_flags'].append('source_display_marker_and_typed_numeric_value_unresolved')
        if pp['period_status']=='source_sheet_name_header_period_conflict_unresolved':
            rec['quality_flags'].append('source_sheet_name_header_period_conflict_unresolved')
        if rec['source_formula_raw']:rec['quality_flags'].append('original_formula_cached_value_not_recalculated')
        self.long.append(rec)
        return rec

    def extract(self):
        for s in self.sources:
            path=self.paths[s['source_id']];sheets=parse_xlsx(path) if s['format']=='XLSX' else parse_ods(path)
            startcells=len(self.cells);startlong=len(self.long);profiles=[]
            for sh in sheets:
                profile={k:v for k,v in sh.items() if k!='cells'}
                if s['format']=='XLSX' and sh['name']=='古蹟概況':
                    profile.update(status='intentional_exclusion_unrelated_sheet',evidence={'title_cell':'A3','title_raw':text(sh,3,1)},reason='古蹟統計非公共圖書館資料，未增加觀測。')
                    profiles.append(profile);continue
                if s['format']=='XLSX' and '背景說明' in sh['name']:
                    profile.update(status='definition_reference_only_not_numeric_data',excluded_contact_ranges=['A7:A9'],
                                   necessary_definition_cells=['A17','A24','A26'],reason='保留必要統計時點／借閱定義；聯絡與私人欄不公開，其他填報程序不增加觀測。')
                    for row in (17,24,26):self.cells.append(self.base(s,sh,row,1,'necessary_statistical_definition'))
                    profiles.append(profile);continue
                if s['source_filename']=='lienchiang-113-overview.ods':
                    assert sh['name']=='工作表1' and sh['used_rows']==6 and sh['used_columns']==8
                    pp=period(s,sh);rows=list(range(2,7));cols=list(range(2,9));selected={(r,c) for r in range(1,7) for c in range(1,9)}
                    for r in rows:
                        label=text(sh,r,1)
                        u=re.search(r'\(([^)]+)\)',label);unit=u[1] if u else None
                        for c in cols:self.emit(s,sh,r,c,label,pp,[],text(sh,1,c),label,unit)
                    profile.update(status='complete_related_statistical_sheet',statistical_grid='B2:H6',expected_data_cells=35)
                elif s['format']=='XLSX':
                    assert text(sh,3,1)=='連江縣公共圖書館概況'
                    pp=period(s,sh);rows=list(range(8,13));cols=list(range(3,10));selected={(r,c) for r in range(1,13) for c in range(1,14)}
                    notes=[dict(cell='A25',raw=text(sh,25,1))]
                    for r in rows:
                        label=text(sh,r,1);u=re.search(r'\(([^)]+)\)',label);unit=u[1] if u else None
                        for c in cols:
                            entity='總計' if c==3 else text(sh,7,c)
                            parent='總計' if c==3 else '縣立' if c in {4,5} else '鄉鎮市立'
                            q=self.emit(s,sh,r,c,label,pp,notes,entity,label,unit,dimension=[parent,text(sh,7,c)])
                            if '借閱人次' in label:
                                q['unit']='人次';q['unit_status']='same_workbook_definition_basis';q['unit_basis']='本工作簿背景說明A24明定全年借閱人次計算；原列括號人仍保留，不沿用到113附件。'
                            q['time_definition_reference']='背景說明-圖書館概況!A17'
                    profile.update(status='complete_related_statistical_sheet',statistical_grid='C8:I12',expected_data_cells=35,
                                   non_statistical_footer_excluded='signature/personnel blocks and administrative filler outside data/header regions',
                                   necessary_note_cells=['A25'])
                else:
                    pp=period(s,sh);template=sh['name']=='空白'
                    stop=next((r for r in range(10,sh['used_rows']+1) if text(sh,r,1).strip() in {'填表','填 表'}),None)
                    if stop is None:raise ValueError(('Unknown monthly table footer boundary',sh['name']))
                    rows=[r for r in range(10,stop) if text(sh,r,1)!=''];cols=list(range(2,10))
                    selected={(r,c) for r in range(1,stop) for c in range(1,10)}
                    notes=[]
                    for (rr,cc),cell in sh['cells'].items():
                        raw=cell['display_raw']
                        if raw.startswith(('備註','附註')):
                            notes.append(dict(cell=coord(rr,cc),raw=raw))
                            if text(sh,rr,cc+1):notes.append(dict(cell=coord(rr,cc+1),raw=text(sh,rr,cc+1)))
                    if not template:
                        for r in rows:
                            label=text(sh,r,1)
                            for c in cols:
                                metric=text(sh,8,2 if c<=5 else 6);sex=text(sh,9,c)
                                self.emit(s,sh,r,c,label,pp,notes,label,metric,'人次' if c<=5 else '冊',dimension=[metric,sex])
                    profile.update(status='blank_template_not_observations' if template else 'complete_related_monthly_sheet',
                                   statistical_grid=f'B10:I{rows[-1]}',expected_data_cells=0 if template else len(rows)*8,
                                   template_blank_grid_cells=len(rows)*8 if template else 0,
                                   original_data_row_labels=[text(sh,r,1) for r in rows],period=pp,
                                   excluded_personnel_footer_row_start=stop,source_note_cells=notes)
                for r,c in sorted(selected):
                    role='template_cell_not_observation' if sh['name']=='空白' else 'statistical_data_cell' if (r in rows and c in cols) else 'original_header_or_structural_blank'
                    self.cells.append(self.base(s,sh,r,c,role))
                profiles.append(profile)
            data=self.long[startlong:];cellrows=self.cells[startcells:]
            expected=sum(p.get('expected_data_cells',0) for p in profiles)
            assert len(data)==expected,(s['source_filename'],len(data),expected)
            assert len({(x['source_sheet'],x['source_cell']) for x in cellrows})==len(cellrows)
            assert len({x['observation_id'] for x in data})==len(data)
            # Every selected source cell must retain the raw XML strings and
            # stored typed values byte-for-character after parsing/serialization.
            shmap={sh['name']:sh for sh in sheets}
            for q in data:
                original=at(shmap[q['source_sheet']],q['source_row'],q['source_column'])
                assert q['source_display_raw']==original['display_raw'] and q['source_stored_value_raw']==original['stored_raw']
                assert q['source_formula_raw']==original['formula_raw'] and q['source_style_name']==original['style_name']
            self.metadata.append(dict(source=s,sheets=profiles,records=dict(source_cell_facts=len(cellrows),statistical_data_cells=len(data),
                                                                           value_status_counts=dict(Counter(x['value_status'] for x in data)),
                                                                           resolved_numeric_cells=sum(x['value'] is not None for x in data),
                                                                           typed_numeric_cells=sum(x['source_typed_numeric_value'] is not None for x in data)),
                                      period_conflicts=[p for p in profiles if p.get('period',{}).get('period_status')=='source_sheet_name_header_period_conflict_unresolved'],
                                      completeness='Every related sheet and the entire declared statistical grids included; templates are source-cell facts only, not observations.',
                                      rights='The113 data.gov.tw resource has explicit catalog OGDL as recorded; other public statistical attachments remain license-unconfirmed. No claim that download grants full-workbook redistribution.',
                                      public_exclusions='Raw documents, unrelated古蹟sheet, contacts/private footer/signature fields and original internal workbook paths are not distributed.',
                                      checks=dict(expected_grid_cells_equal=True,unique_source_cells=True,source_raw_typed_formula_style_roundtrip=True)))

    def save(self):
        assert len(self.long)==18486,len(self.long)
        cc,cj=serialize(self.cells);lc,lj=serialize(self.long)
        buffers=list(zip(OUTPUTS,(cc,cj,lc,lj)))
        for meta in self.metadata:
            name='raw/phase1_local_sources/'+meta['source']['source_id']+'/metadata.json'
            buffers.append((name,(json.dumps(meta,ensure_ascii=False,indent=2)+'\n').encode()))
        summary=dict(source_files=4,sheet_counts={m['source']['source_id']:len(m['sheets']) for m in self.metadata},
                     records=dict(source_cell_facts=len(self.cells),statistical_data_cells=len(self.long),
                                  value_status_counts=dict(Counter(q['value_status'] for q in self.long))),
                     source_records={m['source']['source_id']:m['records'] for m in self.metadata},
                     period_policy='Monthly sheet/header conflicts keep both candidates; official period unknown. Annual two sources remain separate versions and populations.',
                     normalization_policy='Display marker plus typed numeric is unresolved: value null, original typed value separate; neither reported missing nor certified measured zero.',
                     cache_policy='All sources validated before writes; changed SHA requires review; unchanged output bytes retain mtime.',
                     source_sheets_not_canonical='This independent phase1 source-cell layer does not modify the annual canonical observations.',
                     dependencies=['Python3.12 standard library ZIP/XML/Decimal','scripts/extract_phase1_local_sources.py'],
                     outputs=[dict(path=p,sha256=sha(b),bytes=len(b)) for p,b in buffers])
        buffers.append(('raw/phase1_local_sources/summary.json',(json.dumps(summary,ensure_ascii=False,indent=2)+'\n').encode()))
        # All input validation, extraction, reconciliation and serialization
        # finish before replacing any successful output file.
        for p,b in buffers:write(BASE/p,b)
        for m in self.metadata:
            s=m['source'];filename='raw/phase1_local_sources/'+s['source_id']+'/contract.json'
            contract=dict(source_id=s['source_id'],source_sha256=s['source_sha256'],
                          producer_inputs=[dict(path='scripts/extract_phase1_local_sources.py',sha256=sha(Path(__file__).read_bytes())),
                                           dict(path='raw/phase1_local_sources/sources.json',sha256=sha(MANIFEST.read_bytes())),
                                           dict(source_filename=s['source_filename'],sha256=s['source_sha256'],bytes=s['source_bytes'])],
                          producer_outputs=[o for o in summary['outputs'] if o['path'] in OUTPUTS or o['path'].endswith(s['source_id']+'/metadata.json')],
                          unchanged_outputs_keep_mtime=True,original_distribution='not_in_public_bundle')
            write(BASE/filename,json.dumps(contract,ensure_ascii=False,indent=2)+'\n')
        print(json.dumps(summary['records'],ensure_ascii=False))


def selftest(source_root):
    paths=OUTPUTS+['raw/phase1_local_sources/summary.json']
    def snapshot():return {p:(sha((BASE/p).read_bytes()),(BASE/p).stat().st_mtime_ns) for p in paths}
    before=snapshot()
    for _ in range(2):
        subprocess.run([sys.executable,str(Path(__file__).resolve()),'--offline','--source-root',str(source_root)],cwd=BASE,
                       env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'),check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    assert snapshot()==before,'no-op changed content/mtime'
    failures=[]
    for fault in ('missing','changed'):
        with tempfile.TemporaryDirectory(prefix='phase1-source-failure-') as td:
            path=Path(td)/'source'
            if fault=='changed':path.write_bytes(b'synthetic wrong source version')
            try:Producer(source_override=path)
            except (FileNotFoundError,ValueError) as e:failures.append(dict(fault=fault,error=type(e).__name__,previous_outputs_preserved=snapshot()==before))
            else:raise AssertionError('Bad source accepted')
    assert all(f['previous_outputs_preserved'] for f in failures)
    result=dict(source_files=4,statistical_data_cells=18486,checks=dict(all_related_sheets_and_cells=True,raw_typed_formula_style_roundtrip=True,
                 csv_jsonl_every_field_equal=True,unique_cell_identifiers=True,no_op_bytes_mtime_two_runs=True,
                 failure_preserves_previous_outputs=failures),limitations='Source-cell verification is not official-report correctness, recalculation or human double proofreading.')
    write(RAW/'verification.json',json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(result,ensure_ascii=False))


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--offline',action='store_true');p.add_argument('--self-test',action='store_true')
    p.add_argument('--source-root',type=Path,default=DEFAULT_SOURCE_ROOT,help='Directory containing the four source_filename originals; defaults to relative raw/phase1_local_sources/originals or TW_LIBRARY_PHASE1_SOURCE_ROOT. Never saved to data outputs.')
    a=p.parse_args();producer=Producer(source_root=a.source_root);producer.extract();producer.save()
    if a.self_test:selftest(a.source_root)


if __name__=='__main__':main()
