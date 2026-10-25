#!/usr/bin/env python3
"""Reviewed 2022–2024 NCL facts producer; shared only by its three wrappers.

Numeric extraction uses positioned glyphs; a separate word tokenizer verifies
every selected cell. Frozen table specs retain image-reviewed original labels,
table geometry, scope and literal source anchors. No text decoder is required.
"""
from __future__ import annotations
import argparse,collections,csv,hashlib,io,json,re,unicodedata
from decimal import Decimal
from pathlib import Path
from urllib.request import Request,urlopen
import pdfplumber

BASE=Path(__file__).resolve().parents[1]
NUMBER=re.compile(r'^[0-9][0-9,]*(?:\.[0-9]+)?$')
SOURCE_MARKERS={'-','--','—','–','…','...','NA','N/A'}

def digest(body): return hashlib.sha256(body).hexdigest()
def stable(path,body):
    body=body.encode('utf-8') if isinstance(body,str) else body
    if path.exists() and path.read_bytes()==body:return
    path.parent.mkdir(parents=True,exist_ok=True);tmp=path.with_name(path.name+'.tmp');tmp.write_bytes(body);tmp.replace(path)
def jread(path):return json.loads(path.read_text())
def norm(raw):return re.sub(r'\s+','',unicodedata.normalize('NFKC',raw))
def parse(raw):
    token=norm(raw)
    if not token:return None,'blank_in_source'
    if token=='無':return None,'source_marker'
    if token in SOURCE_MARKERS:return None,'not_available_in_source'
    if not NUMBER.fullmatch(token):raise ValueError('Unexpected source text, requires review: '+repr(raw))
    return str(Decimal(token.replace(',',''))),'reported_decimal' if '.' in token else 'reported'
def text_cell(pg,bbox):
    x0,y0,x1,y1=bbox
    cs=[c for c in pg.chars if x0<=(c['x0']+c['x1'])/2<x1 and y0<=(c['top']+c['bottom'])/2<y1]
    return ''.join(c['text'] for c in sorted(cs,key=lambda c:c['x0'])).strip()
def fingerprint(path,root):
    return {'path':str(path.relative_to(root)),'sha256':digest(path.read_bytes()),'bytes':path.stat().st_size}

class Batch:
    def __init__(self,year,root=BASE,offline=True):
        self.year=year;self.root=Path(root);self.raw=self.root/f'raw/ncl-{year}';self.edition=year-1910;self.offline=offline
        self.spec_path=self.root/f'scripts/audit_ncl_recent_specs_{year}.json';self.spec=jread(self.spec_path)
        self.docs={};self.pdfs={};self.pages={};self.words={};self.rows=[];self.checks=[]
    def load(self,kind):
        if kind in self.docs:return self.docs[kind]
        m=jread(self.raw/f'yearbook-{self.edition}-{kind}.metadata.json');path=self.root/m['source_local_path']
        if not path.exists():
            if self.offline:raise FileNotFoundError(path)
            with urlopen(Request(m['source_download_url'],headers={'User-Agent':'Taiwan-public-library-statistics/source-linked-research'}),timeout=60) as response:b=response.read()
            if not b.startswith(b'%PDF') or digest(b)!=m['sha256']:raise ValueError('Changed source body: new version/image review required; old outputs retained')
            stable(path,b)
        if digest(path.read_bytes())!=m['sha256']:raise ValueError('Original PDF SHA differs from reviewed version; old outputs retained')
        self.docs[kind]=m;self.pdfs[kind]=pdfplumber.open(path);return m
    def page(self,kind,n):
        self.load(kind);key=(kind,n)
        if key not in self.pages:self.pages[key]=self.pdfs[kind].pages[n-1].dedupe_chars(tolerance=.3)
        return self.pages[key]
    def emit(self,table,cell):
        kind=table['kind'];m=self.load(kind);pg=self.page(kind,cell['pdf_page']);key=(kind,cell['pdf_page'])
        if key not in self.words:self.words[key]=pg.extract_words(x_tolerance=1,y_tolerance=2)
        bbox=cell['bbox'];raw=text_cell(pg,bbox);value,status=parse(raw);x0,y0,x1,y1=bbox
        tokens=[w for w in self.words[key] if x0<=(w['x0']+w['x1'])/2<x1 and y0<=(w['top']+w['bottom'])/2<y1]
        token_raw=''.join(w['text'] for w in sorted(tokens,key=lambda w:w['x0']))
        if norm(raw)!=norm(token_raw):raise ValueError(('Glyph/word path disagreement',table['table'],cell,raw,token_raw))
        if any(w['x0']<x0-.01 or w['x1']>x1+.01 for w in tokens):raise ValueError(('Clipped source token',table['table'],cell))
        if 'anchor' in cell and (value is None or Decimal(value)!=Decimal(str(cell['anchor']))):raise ValueError(('Literal image anchor differs',table['table'],cell,raw))
        metric=table['metrics'][cell['metric']];entity=cell['entity'];year=cell.get('year',self.year)
        role='derived_ratio' if metric['temporal_kind']=='derived_ratio' else 'published_total' if cell.get('entity_kind')=='national_total' or metric.get('aggregate') else 'reported_component'
        start,end=(f'{year}-01-01',f'{year}-12-31') if metric['temporal_kind'] in {'flow_calendar_year','annual_financial'} else (None,None)
        notes=[table.get('note',''),metric.get('note',''),cell.get('note','')];flags=list(table.get('quality_flags',[]))+list(cell.get('quality_flags',[]))
        if role=='published_total':flags.append('published_total_overlaps_components')
        if status=='source_marker':notes.append('原刊字樣「無」語義未釐清，不推定0、不適用或未填報。')
        if ',' in norm(raw) and not re.fullmatch(r'[0-9]{1,3}(?:,[0-9]{3})+(?:\.[0-9]+)?',norm(raw)):flags.append('source_nonstandard_digit_grouping')
        if cell.get('label_bbox'):
            actual=text_cell(pg,cell['label_bbox'])
            if actual!=cell['label_source_glyphs']:raise ValueError(('Printed label glyph signature differs',cell))
        locator=f"PDF page {cell['pdf_page']}; printed page {cell['printed_page']}; table {table['table']}; data row {cell['source_row']}; column {cell['source_column']}; bbox "+','.join(f'{v:.3f}' for v in bbox)
        scope=table['national_libraries_scope']
        if entity in {'國臺圖','國資圖'}:scope='separate_national_public_library_institution'
        r=dict(data_year=year,entity_raw=entity,entity_contextual_name=cell.get('entity_contextual_name',entity),entity_kind=cell['entity_kind'],
            geography_vintage=f'{year} original printed labels and ordering; no geographic harmonization',national_libraries_scope=scope,
            metric_id=f"table{table['table']}_{metric['id']}",metric_raw=metric['raw'],value_raw=raw,value=value,value_status=status,
            unit=metric['unit'],unit_raw=metric.get('unit_raw'),unit_basis=metric['unit_basis'],unit_status=metric.get('unit_status','printed_unit' if metric.get('unit_raw') else 'contextual_inference' if metric['unit'] else 'no_uniform_unit_reported'),
            unit_interpretation_candidate=metric.get('unit_interpretation_candidate'),temporal_kind=metric['temporal_kind'],
            source_id=m['source_id'],source_url=m['source_page_url'],source_download_url=m['source_download_url'],source_sha256=m['sha256'],source_local_path=m['source_local_path'],source_agency='國家圖書館',source_retrieved_at=m['source_retrieved_at'],
            source_pdf_page=cell['pdf_page'],source_printed_page=str(cell['printed_page']),source_table=str(table['table']),source_row=cell['source_row'],source_column=cell['source_column'],source_locator=locator,
            raw_extracted_line=raw,extraction_status='image_reviewed_table_specs_positioned_glyphs_and_separate_word_token_check',license_status='not_confirmed',license_url='https://www.ncl.edu.tw/open-government-declaration',
            publication_date=self.spec['publication_date'],publication_date_basis='official_entry_visible_date; original_copyright_month_checked',source_edition=str(self.edition),source_edition_roc=self.edition,
            table_title_raw=table['title_raw'],source_table_title=table['title_raw'],source_title=f'中華民國{self.edition}年圖書館年鑑／'+('公共圖書館' if kind=='public-library' else '圖書館統計'),
            population_scope=table['population_scope'],period_raw=f'{year-1911}年（原表明列資料年）',period_start=start,period_end=end,
            notes='；'.join(n for n in notes if n),cell_annotation='',cell_bbox=bbox,source_cell_bbox=bbox,source_cell_bbox_kind='frozen_reviewed_numeric_row_band_and_column_bounds',snapshot_distribution='not_in_public_bundle',aggregation_role=role,
            institutional_level=cell.get('institutional_level','原刊列名及層級合計'),source_column_path=cell.get('column_path',metric['raw']),source_version_id=m['source_id']+':'+m['sha256'],source_data_year_raw=f'{year-1911}年',scope_note=table['population_scope'],
            time_reference=f'{year}年全年' if start else f'原表{year-1911}年；精確時點未明示，未以卷號／出版／檢索日補時點',quality_flags=flags,
            source_footnotes_raw=table.get('footnotes_raw'),source_footnotes_status='relevant_original_table_notes_whitespace_normalized' if table.get('footnotes_raw') else 'no_table_specific_note_printed',source_original_access_date_raw=table.get('original_access_date_raw'),
            observation_identity_suffix='row:'+str(cell['source_row']),entity_label_status=cell.get('entity_label_status','original_printed_label_preserved'),interpretation_basis=metric.get('interpretation_basis'),parse_rule='exact_decimal_remove_source_grouping_commas_keep_all_digits',
            source_original_entity_glyphs=cell.get('label_source_glyphs'),original_fields={'entity':entity,'metric':metric['raw'],'value_raw':raw,'table_title':table['title_raw'],'unit_raw':metric.get('unit_raw')})
        self.rows.append(r)
    def arithmetic(self,name,target,parts):
        if target['value'] is None or any(r['value'] is None for r in parts):return
        total=Decimal(target['value']);summed=sum(Decimal(r['value']) for r in parts);same=total==summed
        self.checks.append(dict(check=name,source_table=target['source_table'],source_row=target['source_row'],entity=target['entity_raw'],metric_id=target['metric_id'],reported=str(total),sum_components=str(summed),matches=same,source_locator=target['source_locator'],interpretation='Numeric comparison only; difference is preserved and not proof that source definitions are disjoint or that official data are wrong.'))
        if not same:target['quality_flags'].append('source_component_sum_difference_preserved')
    def validate(self):
        if len(self.rows)!=self.spec['expected_cells']:raise ValueError('Batch source position count differs')
        keys=[(r['source_id'],r['source_table'],r['source_row'],r['source_column']) for r in self.rows]
        if len(set(keys))!=len(keys):raise ValueError('Duplicate original source position')
        for t in self.spec['tables']:
            rs=[r for r in self.rows if r['source_table']==str(t['table']) and r['source_id'].endswith(t['kind'])]
            if len(rs)!=t['expected_cells']:raise ValueError('Table incomplete')
            groups=collections.defaultdict(list)
            for r in rs:groups[r['source_row']].append(r)
            for group in groups.values():
                byid={r['metric_id'].split('_',1)[1]:r for r in group}
                if t.get('row_subtotal_metric'):
                    target=byid[t['row_subtotal_metric']];self.arithmetic('printed_row_subtotal',target,[r for r in group if r is not target and r['metric_id'].split('_',1)[1] in t['row_subtotal_components']])
                if t['layout']=='levels':
                    totals=[r for r in group if r['entity_raw']=='合計']
                    if len(totals)==1:self.arithmetic('printed_level_total_numeric_comparison_scope_not_assumed_disjoint',totals[0],[r for r in group if r is not totals[0]])
            if t.get('column_total'):
                for metric in t['metrics']:
                    if metric['temporal_kind']=='derived_ratio':continue
                    group=[r for r in rs if r['metric_id']==f"table{t['table']}_{metric['id']}"]
                    totals=[r for r in group if r['entity_raw'] in {'合計','小計'}]
                    if len(totals)==1:self.arithmetic('printed_column_total',totals[0],[r for r in group if r is not totals[0]])
        populations=collections.defaultdict(list)
        for r in self.rows:
            if r['metric_id'].endswith('_population'):populations[r['entity_raw']].append(r)
        differences=[]
        for entity,rs in populations.items():
            vals={r['value'] for r in rs if r['value'] is not None}
            if len(vals)>1:
                differences.append({'entity':entity,'variants':[{'value_raw':r['value_raw'],'source_table':r['source_table'],'source_locator':r['source_locator']} for r in rs]})
                for r in rs:r['quality_flags'].append('source_same_year_population_disagreement_unresolved')
        return differences
    def run(self):
        # Load both sources before writing anything. A failure keeps all former
        # derived outputs intact, including public copies restoring originals.
        for kind in ['public-library','statistics']:self.load(kind)
        for table in self.spec['tables']:
            for cell in table['cells']:self.emit(table,cell)
        population_differences=self.validate()
        statuses=dict(collections.Counter(r['value_status'] for r in self.rows));year=self.year
        report={'reference_year':year,'edition_roc':self.edition,'publication_date':self.spec['publication_date'],'long_rows':len(self.rows),'table_count':len(self.spec['tables']),
            'source_ids':dict(collections.Counter(r['source_id'] for r in self.rows)),'value_status_counts':statuses,'zero_cells':sum(r['value'] is not None and Decimal(r['value'])==0 for r in self.rows),
            'all_selected_tables_complete':True,'word_token_cells_checked':len(self.rows),'label_glyph_signatures_checked':sum(bool(c.get('label_bbox')) for t in self.spec['tables'] for c in t['cells']),
            'literal_image_anchors_checked':sum('anchor' in c for t in self.spec['tables'] for c in t['cells']),'tables':[{k:v for k,v in t.items() if k!='cells'} for t in self.spec['tables']],
            'arithmetic_checks':self.checks,'arithmetic_discrepancies':[r for r in self.checks if not r['matches']],'same_year_population_variants':population_differences,
            'quality_flag_counts':dict(collections.Counter(f for r in self.rows for f in r['quality_flags'])),'intentional_exclusions':self.spec['intentional_exclusions'],
            'review_limit':'Producer original-image table/header/scope review and literal anchors, exhaustive glyph/word-token checks. Not an independent human full-cell double collation.','network_used_for_extraction':False}
        out=io.StringIO(newline='');writer=csv.DictWriter(out,fieldnames=list(self.rows[0]));writer.writeheader()
        for r in self.rows:writer.writerow({k:json.dumps(v,ensure_ascii=False,separators=(',',':')) if isinstance(v,(list,dict)) else v for k,v in r.items()})
        outputs={f'derived/ncl_{year}_long.csv':out.getvalue(),f'derived/ncl_{year}_long.jsonl':''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in self.rows),f'raw/ncl-{year}/extraction-validation.json':json.dumps(report,ensure_ascii=False,indent=2)+'\n'}
        documents=[]
        for kind,m in self.docs.items():
            m=dict(m);m.update(license_url='https://www.ncl.edu.tw/open-government-declaration',license_evidence='官方宣告出版品與專人專案撰文等須另經權利人同意；未確認全文開放授權，僅統計事實投影，完整PDF/HTML/PNG私有。',selected_tables=[t['table'] for t in self.spec['tables'] if t['kind']==kind],source_cells=sum(r['source_id']==m['source_id'] for r in self.rows));documents.append(m)
        outputs[f'raw/ncl-{year}/documents.json']=json.dumps(documents,ensure_ascii=False,indent=2)+'\n'
        for name,body in outputs.items():stable(self.root/name,body)
        dependencies=[self.root/f'scripts/extract_ncl_{year}.py',self.root/'scripts/audit_ncl_recent_helper.py',self.spec_path]
        for kind in self.docs:dependencies.extend([self.raw/f'yearbook-{self.edition}-{kind}.metadata.json',self.root/self.docs[kind]['source_local_path']])
        contract={'producer_inputs':[fingerprint(p,self.root) for p in dependencies],'producer_outputs':[fingerprint(self.root/p,self.root) for p in outputs],
            'cache_contract':'Every input SHA and producer signature unchanged; every output present and SHA-valid. Missing or changed original is not a valid cache. Changed original SHA requires new review; never apply old coordinates.','unchanged_outputs_keep_mtime':True,'full_originals_distribution':'not_in_public_bundle'}
        stable(self.raw/'incremental-contract.json',json.dumps(contract,ensure_ascii=False,indent=2)+'\n')
        print(json.dumps({k:report[k] for k in ['reference_year','long_rows','table_count','value_status_counts','zero_cells','literal_image_anchors_checked']},ensure_ascii=False))
        return report

def cli(year):
    p=argparse.ArgumentParser();p.add_argument('--offline',action='store_true');args=p.parse_args();Batch(year,offline=args.offline).run()
