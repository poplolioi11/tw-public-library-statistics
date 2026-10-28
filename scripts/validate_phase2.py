#!/usr/bin/env python3
"""Validate the phase2 definition layer offline, independently of its producer.

Checks published three-format projections, immutable source representations,
evidence/ID membership, exact Decimal scaling, partitions and input checksums.
It does not download or certify the content of omitted original documents.
"""
from __future__ import annotations
import argparse,collections,csv,gzip,hashlib,json,re,sqlite3
from decimal import Decimal,InvalidOperation,localcontext
from html.parser import HTMLParser
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
LAYERS={'canonical':'data/combined/observations.jsonl','local_statistical_cells':'derived/phase1_local_sources_long.jsonl','programme_quantities':'derived/ncl_2005_programmes_long.jsonl'}
IGNORED={'snapshot_distribution','public_evidence_path','public_evidence_sha256','public_projection_policy','original_fields'}
csv.field_size_limit(1<<30)

def require(ok,message):
 if not ok:raise ValueError(message)
def stable(value):return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'))
def digest(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
 return h.hexdigest()
def local(root,name):
 require(isinstance(name,str) and not Path(name).is_absolute(),'Not a relative project path')
 p=(root/name).resolve();require(p.is_relative_to(root.resolve()),'Path escapes project: '+name);return p
def textopen(path):return gzip.open(path,'rt',encoding='utf-8-sig',newline='') if path.suffix=='.gz' else path.open(encoding='utf-8-sig',newline='')
def source_path(root,name):
 p=local(root,name)
 return p if p.is_file() else p.with_suffix(p.suffix+'.gz')
def iterjson(path):
 with textopen(path) as f:
  for i,line in enumerate(f,1):
   require(bool(line.strip()),'Blank JSONL row: '+path.name+':'+str(i));value=json.loads(line);require(isinstance(value,dict),'JSONL row is not an object');yield value

def fingerprint(rows):
 h=hashlib.sha256();h.update(b'[');first=True
 for r in rows:
  if not first:h.update(b',')
  h.update(stable({k:v for k,v in r.items() if k not in IGNORED}).encode());first=False
 h.update(b']');return h.hexdigest()
def sql_ident(name):return '"'+name.replace('"','""')+'"'
def scalar(value):return stable(value) if isinstance(value,(dict,list,bool)) else None if value is None else str(value)
def compare_formats(rows,fields,csvrows,sqlfields,sqlrows,label):
 union=set().union(*(row.keys() for row in rows)) if rows else set()
 require(len(fields)==len(set(fields)) and set(fields)==union,'CSV field union differs: '+label)
 require(len(sqlfields)==len(set(sqlfields)) and set(sqlfields)==union,'SQLite field union differs: '+label)
 count=0;missing=0
 ci=iter(csvrows);si=iter(sqlrows)
 for count,row in enumerate(rows,1):
  c=next(ci,None);s=next(si,None);require(c is not None and s is not None,'Format rows missing: '+label);s=dict(s)
  require(None not in c and set(c)==union and set(s)==union,'Malformed format row: '+label)
  for key in union:
   raw=row.get(key);missing+=key not in row;value=scalar(raw);loc=label+':'+str(count)+':'+key
   if isinstance(raw,(dict,list,bool)):
    try:cv=json.loads(c[key]);sv=json.loads(s[key])
    except (ValueError,TypeError) as exc:raise ValueError('Structured JSON differs: '+loc) from exc
    require(stable(cv)==stable(raw) and stable(sv)==stable(raw),'Structured value differs: '+loc)
   else:
    require(c[key]==('' if value is None else value),'CSV value differs: '+loc)
    require(s[key]==value,'SQLite value differs: '+loc)
 require(next(ci,None) is None and next(si,None) is None,'Format has additional rows: '+label)
 return {'records':count,'fields':len(union),'sparse_missing_keys_checked_as_null':missing}
def compare_csv(rows,path,label):
 with textopen(path) as f:
  reader=csv.DictReader(f);fields=reader.fieldnames or []
  # Reuse the strict projection checker without a separate SQL dependency.
  sqlrows=({k:scalar(r.get(k)) for k in fields} for r in rows)
  return compare_formats(rows,fields,reader,fields,sqlrows,label)

class EmbeddedJSON(HTMLParser):
 def __init__(self):super().__init__();self.active=False;self.parts=[];self.items=[];self.identifiers=[];self.active_id=None
 def handle_starttag(self,tag,attrs):
  d=dict(attrs)
  if tag=='script' and d.get('type')=='application/json':self.active=True;self.parts=[];self.active_id=d.get('id')
 def handle_data(self,text):
  if self.active:self.parts.append(text)
 def handle_endtag(self,tag):
  if tag=='script' and self.active:
   self.items.append(json.loads(''.join(self.parts)));self.identifiers.append(self.active_id);self.active=False

def validate_reader(html,summary,groups):
 parser=EmbeddedJSON();parser.feed(html.read_text());payloads=[x for identifier,x in zip(parser.identifiers,parser.items) if identifier=='phase2-data' and isinstance(x,dict) and 'summary' in x and 'groups' in x];require(len(payloads)==1,'Reader payload missing or duplicated');payload=payloads[0]
 require(payload['summary']==summary,'Reader summary payload differs')
 original={g['comparison_group_id']:g for g in groups};projected=payload['groups'];require(len(projected)==len(original) and {g['comparison_group_id'] for g in projected}==set(original),'Reader group IDs incomplete or duplicated')
 required={'comparison_group_id','layer','raw_indicator','source_ids','source_urls','comparison_unit','records','years','status_counts','eligible_periods','has_multiple_eligible_periods'}
 for row in projected:
  g=original[row['comparison_group_id']];require((required&set(g))<=set(row),'Reader omits a required group projection field')
  for key in set(row)&set(g):require(row[key]==g[key],'Reader projected group value differs: '+key)
  for key,value in row.get('scope_summary',{}).items():require(key in g['facets'] and value==g['facets'][key],'Reader scope summary differs')
  require(row.get('sample_record_keys')==g['record_keys'][:2],'Reader sample IDs differ')
 return 'summary_complete_group_ID_set_common_fields_scope_and_samples_match'

def validate_sources(annotations,cards,root,summary):
 amap={r['record_key']:r for r in annotations};require(len(amap)==len(annotations),'Duplicate record_key')
 require(len({(r['layer'],r['observation_id']) for r in annotations})==len(annotations),'Duplicate layer observation ID')
 memberships=collections.defaultdict(list);eids=set()
 for card in cards:
  eid=card['evidence_id'];require(eid not in eids,'Duplicate evidence ID');eids.add(eid)
  ids=card.get('observation_ids',[]);require(len(ids)==len(set(ids)),'Duplicate observation IDs in one evidence card')
  for oid in ids:
   key=card['layer']+':'+oid;require(key in amap,'Evidence names unknown observation: '+key)
   require(card['source_id']==amap[key]['source_id'] and card['source_sha256']==amap[key]['source_sha256'],'Evidence original mismatch: '+key)
   memberships[key].append(eid)
 require(set(memberships)==set(amap),'Evidence membership does not cover every annotation')
 for key,ann in amap.items():
  ids=[ann['evidence_id'],*ann.get('supporting_evidence_ids',[])];require(len(ids)==len(set(ids)) and set(ids)==set(memberships[key]),'Annotation evidence IDs differ: '+key)
 counts=collections.Counter();seen=set();raw_fingerprints={};special=collections.Counter();zero=0;scale1000=0
 for layer,name in LAYERS.items():
  h=hashlib.sha256();h.update(b'[');first=True
  for raw in iterjson(source_path(root,name)):
   if not first:h.update(b',')
   h.update(stable({k:v for k,v in raw.items() if k not in IGNORED}).encode());first=False
   key=layer+':'+raw['observation_id'];require(key not in seen,'Duplicate original observation');seen.add(key);require(key in amap,'Original record omitted: '+key);ann=amap[key];counts[layer]+=1
   expected={'record_key':key,'layer':layer,'observation_id':raw['observation_id'],'source_id':raw['source_id'],'source_sha256':raw['source_sha256'],'source_url':raw.get('source_url') or raw.get('source_download_url'),'source_locator':raw['source_locator'],'raw_value':raw.get('raw_value',raw.get('value_raw')),'original_value':raw.get('value'),'value_status':raw.get('value_status')}
   for field,value in expected.items():require(stable(ann.get(field))==stable(value),'Original source representation changed: '+key+':'+field)
   provenance={'source_version_id':raw.get('source_version_id') or raw['source_id']+'@sha256:'+raw['source_sha256'],'source_edition_raw':raw.get('source_edition') or raw.get('source_edition_roc'),'source_retrieved_at':raw.get('retrieved_at') or raw.get('source_retrieved_at'),'source_license_status':raw.get('license_status'),'source_license_url':raw.get('license_url')}
   for field,value in provenance.items():
    if field in ann:require(stable(ann[field])==stable(value),'Original provenance changed: '+key+':'+field)
   if 'raw_indicator' in ann:require(ann['raw_indicator']==str(raw.get('indicator') or raw.get('metric_raw') or raw.get('source_field') or ''),'Original indicator label changed: '+key)
   require(re.fullmatch('[a-f0-9]{64}',ann['source_sha256']) and ann['source_url'] and ann['source_locator'],'Missing source provenance: '+key)
   value=raw.get('value');unit=ann.get('comparison_unit');scaled=ann.get('comparison_value');scale=ann.get('unit_scale');require(scale in {'1','1000'},'Unapproved scale: '+key)
   if value is None or not unit:require(scaled is None,'Missing or unqualified unit converted into number: '+key)
   else:
    try:
     with localcontext() as ctx:ctx.prec=100;number=Decimal(str(value))*Decimal(scale);actual=Decimal(scaled)
    except (InvalidOperation,TypeError) as exc:raise ValueError('Invalid Decimal: '+key) from exc
    require(number==actual,'Exact Decimal conversion differs: '+key)
   if scale=='1000':
    require(raw.get('unit') in {'千冊','千人次','千人','千元'},'Scale1000 lacks explicit original unit: '+key);scale1000+=1
   if ann.get('unit_audit_status')=='literal_suffix_verified':
    label=str(raw.get('indicator') or raw.get('metric_raw') or raw.get('source_field') or '');expected_unit='冊' if label.endswith('冊數') else '人次' if label.endswith('人次') else None
    require(layer=='canonical' and raw.get('source_family')=='地方政府開放歷史表' and raw.get('unit') in (None,'') and expected_unit and unit==expected_unit and scale=='1','Unsupported literal unit promotion: '+key)
   if ann.get('period_audit_status')=='verified_original_statistical_year_month_code':
    code=str(raw.get('period_raw') or '')
    require(re.fullmatch('[0-9]{5}',code) and int(code[:3])>=1 and 1<=int(code[-2:])<=12 and raw.get('period_basis')=='observation_field','Invalid original literal month code: '+key)
    require(ann['comparison_year']==int(code[:3])+1911 and ann['comparison_month']==int(code[-2:]) and ann['period_kind']=='monthly_source_statistic','Literal month decoding differs: '+key)
   if value is not None and Decimal(str(value))==0:zero+=1;require(ann['original_value'] is not None,'Original zero lost: '+key)
   if raw.get('value_status')=='source_display_typed_value_conflict_unresolved':
    special['display_typed_conflict']+=1;require(value is None and scaled is None and ann['comparison_status']=='unresolved','Display/typed conflict resolved: '+key)
   if raw.get('period_status') in {'source_sheet_name_header_period_conflict_unresolved','catalog_title_year_only_attachment_undated'}:
    special[raw['period_status']]+=1;require(ann['comparison_year'] is None and ann['comparison_month'] is None and ann['period_kind']=='unresolved','Unknown period assigned: '+key)
   if layer=='programme_quantities':require(ann['comparison_year'] is None and ann['period_kind']=='programme_not_annual','Programme recoded as annual: '+key)
   if layer=='canonical' and raw.get('data_year')==2012 and 'ratio' in str(raw.get('temporal_kind','')):
    expected_period='monthly_source_statistic' if raw.get('source_location_kind')=='verified_original_cell' and raw.get('period_basis')=='literal_original_year_month' else 'source_ratio_period'
    special['2012_original_ratios']+=1;require(ann['measure_class']=='ratio_or_per_capita' and ann['period_kind']==expected_period,'2012 ratio reinterpreted as original quantity or wrong period: '+key)
  h.update(b']');raw_fingerprints[layer]=h.hexdigest()
 require(seen==set(amap),'Annotation does not have exactly one original')
 require(dict(counts)==summary['layers'],'Source layer counts differ from summary')
 require(raw_fingerprints==summary['layer_raw_fingerprints'],'Statistical source fingerprints differ')
 require(raw_fingerprints['canonical']==summary['canonical_statistical_content_sha256'],'Canonical fingerprint differs')
 return {'layers':dict(counts),'special_guards':dict(special),'source_zeros_preserved':zero,'exact1000_scaling_checked':scale1000}

def validate(root=ROOT):
 root=Path(root).resolve();summary_path=root/'docs/phase2-summary.json';summary=json.loads(summary_path.read_text());version=(root/'VERSION').read_text().strip()
 require(summary['dataset_version']==version,'Phase2 version differs');require(summary['canonical_values_modified'] is False and summary['no_imputation'] is True,'Unsafe source-data policy')
 for name,expected in summary['inputs'].items():require(local(root,name).is_file() and digest(local(root,name))==expected,'Summary input checksum differs: '+name)
 for name,spec in summary['outputs'].items():
  p=local(root,name);require(p.is_file() and p.stat().st_size==spec['bytes'] and digest(p)==spec['sha256'],'Summary output checksum differs: '+name)
 data=root/'derived/phase2';datasets={};reports={}
 con=sqlite3.connect((data/'definitions.sqlite').as_uri()+'?mode=ro',uri=True);con.row_factory=sqlite3.Row
 try:
  require(con.execute('PRAGMA quick_check').fetchone()[0]=='ok','SQLite integrity check failed')
  for name,table,order,compressed in [('annotations','annotations','record_key',True),('groups','comparison_groups','comparison_group_id',False),('evidence_cards','evidence_cards','rowid',False),('breakpoints','breakpoints','rowid',False)]:
   rows=list(iterjson(data/(name+'.jsonl'+('.gz' if compressed else ''))));datasets[name]=rows
   sqlfields=[r[1] for r in con.execute('PRAGMA table_info('+sql_ident(table)+')')]
   query='SELECT * FROM '+sql_ident(table)+' ORDER BY '+sql_ident(order)
   with textopen(data/(name+'.csv'+('.gz' if compressed else ''))) as f:
    csvreader=csv.DictReader(f);reports[name]=compare_formats(rows,csvreader.fieldnames or [],csvreader,sqlfields,con.execute(query),name)
 finally:con.close()
 anns=datasets['annotations'];groups=datasets['groups'];cards=datasets['evidence_cards'];breaks=datasets['breakpoints']
 require(len(anns)==summary['total_quantitative_records']==sum(summary['layers'].values()),'Quantitative total differs')
 require(len(cards)==summary['source_definition_cards'] and len(groups)==summary['comparison_groups'] and len(breaks)==summary['breakpoint_rules'],'Side table counts differ')
 require(dict(sorted(collections.Counter(a['comparison_status'] for a in anns).items()))==summary['comparison_status_counts'],'Status counts differ')
 require(sum(a['unit_audit_status']=='literal_suffix_verified' for a in anns)==summary['literal_unit_suffix_upgrades'],'Unit upgrade count differs')
 require(sum(a['period_audit_status']=='verified_original_statistical_year_month_code' for a in anns)==summary['strict_literal_month_code_records'],'Literal month count differs')
 source_report=validate_sources(anns,cards,root,summary)
 amap={a['record_key']:a for a in anns};group_members=[];expected_groups=collections.defaultdict(list)
 for a in anns:expected_groups[a['comparison_group_id']].append(a['record_key'])
 for g in groups:
  keys=g['record_keys'];require(len(keys)==len(set(keys))==g['records'],'Group count differs');require(keys==expected_groups[g['comparison_group_id']],'Group membership/order differs')
  for key in keys:require(amap[key]['facets']==g['facets'],'Group facets differ: '+key)
  members=[amap[k] for k in keys]
  periods=sorted({(a['comparison_year'],a['comparison_month']) for a in members if a['comparison_year'] is not None},key=lambda x:(x[0],x[1] or 0));eligible=sorted({(a['comparison_year'],a['comparison_month']) for a in members if a['comparison_status']=='published_panel_limited'},key=lambda x:(x[0] or 0,x[1] or 0))
  derived={'source_ids':sorted({a['source_id'] for a in members}),'source_urls':sorted({a['source_url'] for a in members}),'source_sha256s':sorted({a['source_sha256'] for a in members}),'evidence_ids':sorted({a['evidence_id'] for a in members}),'periods':[list(x) for x in periods],'years':sorted({y for y,m in periods}),'eligible_periods':[list(x) for x in eligible],'status_counts':dict(sorted(collections.Counter(a['comparison_status'] for a in members).items())),'has_multiple_eligible_periods':len(eligible)>1}
  for field,value in derived.items():
   if field in g:require(stable(g[field])==stable(value),'Derived group field differs: '+field)
  group_members.extend(keys)
 require(len(group_members)==len(set(group_members))==len(anns),'Groups do not partition annotations')
 require(sum(g['has_multiple_eligible_periods'] for g in groups)==summary['groups_with_multiple_eligible_periods'],'Eligible group count differs')
 if 'groups_with_multiple_eligible_years' in summary:require(sum(len({y for y,m in g['eligible_periods'] if y is not None})>1 for g in groups)==summary['groups_with_multiple_eligible_years'],'Eligible multi-year group count differs')
 index=json.loads(local(root,summary['partition_index']).read_text());require(index['version']==version and index['records']==len(anns),'Partition index version/count differs');parts_seen=[];partkeys=set()
 for part in index['partitions']:
  key=(part['layer'],part['comparison_year']);require(key not in partkeys,'Duplicate year partition');partkeys.add(key)
  expected=[a for a in anns if (a['layer'],a['comparison_year'])==key];require(len(expected)==part['records'],'Partition row count differs')
  jp=local(root,part['jsonl']);cp=local(root,part['csv']);require(digest(jp)==part['jsonl_sha256'] and digest(cp)==part['csv_sha256'],'Partition SHA differs')
  rows=list(iterjson(jp));require(rows==expected,'Partition rows or row order differ')
  compare_csv(rows,cp,'partition '+str(key));parts_seen.extend(r['record_key'] for r in rows)
 require(len(parts_seen)==len(set(parts_seen))==len(anns) and set(parts_seen)==set(amap),'Partition union incomplete or duplicated')
 html=root/'site/phase2.html';reader='not_present'
 if html.is_file():
  reader=validate_reader(html,summary,groups)
 return {'status':'PASS','dataset_version':version,'records':len(anns),'evidence_cards':len(cards),'groups':len(groups),'partitions':len(partkeys),'formats':reports,'source_guards':source_report,'reader':reader,'original_document_fulltext_verified':False}

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,default=ROOT);a=p.parse_args();print(json.dumps(validate(a.root),ensure_ascii=False))
if __name__=='__main__':main()
