#!/usr/bin/env python3
"""Generate bounded source documentation from canonical data and reviewed registry.

Importing this module is read-only. Only main() writes documentation. The
registry permits execution; its CSVs describe completed source cells. Canonical
counts separately describe the observations actually distributed for analysis.
"""
from __future__ import annotations
import record_io
import csv,json,re
from collections import Counter,defaultdict
from pathlib import Path
R=Path(__file__).resolve().parents[1]
YEARBOOK='國家圖書館年鑑統計事實'
READING='國家圖書館閱讀報告統計事實'
HISTORICAL={YEARBOOK,READING}
FAMILY_ORDER=['國資圖公開全國圖表','國資圖2023開放資料（含縣市）',YEARBOOK,READING,'主計總處歷史全國統計','主計總處縣市公共館數','地方政府開放歷史表']
UNCERTAIN_SCOPES={'county_source_label_uncertain','county_source_label_duplicate_unresolved'}
UNCERTAIN_FLAGS={'source_geography_label_alignment_suspect_unreassigned','duplicate_printed_geography_label'}

def read_json(path,default=None):
    return json.loads(path.read_text()) if path.exists() else default

def write_json(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')

def as_int(value):
    try:return int(value)
    except (TypeError,ValueError):return None

def flags(row):
    value=row.get('quality_flags')
    if isinstance(value,list):return value
    if not value:return []
    try:
        parsed=json.loads(value)
        return parsed if isinstance(parsed,list) else [str(parsed)]
    except (ValueError,TypeError):return [str(value)]

def uncertain_label(row):
    if row.get('geographic_scope') in UNCERTAIN_SCOPES or row.get('entity_kind') in UNCERTAIN_SCOPES:return True
    if UNCERTAIN_FLAGS.intersection(flags(row)):return True
    fields=' '.join(str(row.get(k) or '') for k in ['geographic_scope','entity_kind','scope_note','quality_flags'])
    return any(marker in fields for marker in UNCERTAIN_SCOPES)

def unit_conflict(row):return row.get('unit_status') in {'source_heading_conflict_unresolved','source_heading_body_counting_unit_conflict_unresolved'}

def edition(row):
    # Read edition labels/path evidence; never infer edition from the data year.
    for field in ['source_edition_roc','source_edition']:
        value=row.get(field)
        if str(value or '').isdigit():return int(value)
    for field in ['source_local_path','source_snapshot_path','source_id']:
        match=re.search(r'yearbook-(\d+)(?:-|\b)',str(row.get(field) or ''))
        if match:return int(match.group(1))
    return None

def years(rows):return sorted({as_int(r.get('data_year')) for r in rows if as_int(r.get('data_year')) is not None})

def display_numbers(values,suffix=''):
    vals=sorted(set(v for v in values if v is not None))
    if not vals:return '未列明'
    spans=[];start=previous=vals[0]
    for value in vals[1:]:
        if value==previous+1:previous=value;continue
        spans.append(str(start) if start==previous else f'{start}–{previous}');start=previous=value
    spans.append(str(start) if start==previous else f'{start}–{previous}')
    return '、'.join(spans)+suffix

def value_counts(rows):
    statuses=Counter();numeric=blank=missing=0
    for row in rows:
        status=row.get('value_status') or 'unspecified';statuses[status]+=1
        if row.get('value') not in (None,''):numeric+=1
        elif status in {'blank','source_blank','blank_in_source'}:blank+=1
        else:missing+=1
    return {'records':len(rows),'numeric_cells':numeric,'source_blank_cells':blank,'other_missing_cells':missing,'value_status_counts':dict(sorted(statuses.items()))}

def table_groups(rows):
    groups={}
    for row in rows:
        key=(row.get('source_id'),str(row.get('source_table') or ''),row.get('source_table_title') or row.get('table_title_raw') or '')
        item=groups.setdefault(key,{'source_id':key[0],'source_table':key[1],'source_table_title':key[2],'source_cells':0,'numeric_cells':0,'source_blank_cells':0,'other_missing_cells':0,'data_years':set(),'edition_roc':set(),'pdf_pages':set(),'printed_pages':set(),'source_sha256':set(),'uncertain_label_records':0,'unit_conflict_records':0})
        counts=value_counts([row]);item['source_cells']+=1
        for field in ['numeric_cells','source_blank_cells','other_missing_cells']:item[field]+=counts[field]
        item['data_years'].update(years([row]));ed=edition(row)
        if ed is not None:item['edition_roc'].add(ed)
        for source,target in [('source_pdf_page','pdf_pages'),('source_printed_page','printed_pages'),('source_sha256','source_sha256')]:
            if row.get(source) not in (None,''):item[target].add(str(row[source]))
        item['uncertain_label_records']+=uncertain_label(row);item['unit_conflict_records']+=unit_conflict(row)
    result=[]
    for key,item in sorted(groups.items(),key=lambda kv:tuple(str(v) for v in kv[0])):
        for field in ['data_years','edition_roc','pdf_pages','printed_pages','source_sha256']:item[field]=sorted(item[field],key=lambda v:(as_int(v) is None,as_int(v) if as_int(v) is not None else str(v)))
        result.append(item)
    return result

def load_context(root=R):
    summary=read_json(root/'data/combined/summary.json')
    rows=list(record_io.rows(root))
    if len(rows)!=summary['records']:raise ValueError('Canonical rows and summary.records differ; generate documentation after a complete data build.')
    registry=read_json(root/'data/reviewed_historical_cohorts.json',{'cohorts':[]});cohorts=[];registered_ids=set()
    for cohort in registry.get('cohorts',[]):
        csv_path=cohort.get('derived_csv');path=root/csv_path if csv_path else None
        csv_rows=list(csv.DictReader(path.open(encoding='utf-8-sig',newline=''))) if path and path.exists() else []
        ids=sorted({r['source_id'] for r in csv_rows if r.get('source_id')});registered_ids.update(ids)
        canonical=[r for r in rows if r.get('source_id') in ids]
        selected=canonical if canonical else csv_rows
        metadata_paths=[p for p in cohort.get('outputs',[]) if p.endswith('.json') and '.private.' not in p and any(s in Path(p).name for s in ['metadata','validation','documents'])]
        cohorts.append({'registry':cohort,'csv_rows':csv_rows,'canonical_rows':canonical,'selected_rows':selected,'id':cohort['id'],'derived_csv':csv_path,'source_csv_available':bool(path and path.exists()),'source_ids':ids,'review_status':cohort.get('review_status','unspecified'),'data_years':years(csv_rows or canonical),'edition_roc':sorted({edition(r) for r in csv_rows+canonical if edition(r) is not None}),'publication_dates':sorted({str(r['publication_date']) for r in csv_rows+canonical if r.get('publication_date')}),'source_csv_counts':value_counts(csv_rows),'canonical_counts':value_counts(canonical),'uncertain_label_records':sum(uncertain_label(r) for r in selected),'unit_conflict_records':sum(unit_conflict(r) for r in selected),'table_inventory':table_groups(csv_rows or canonical),'metadata_paths':metadata_paths,'scope':cohort.get('scope','僅指定表格／公共館子群；原件、逐表metadata與查核紀錄決定界線，不宣稱整冊完整。')})
    historical=[r for r in rows if r.get('source_family') in HISTORICAL]
    return {'root':root,'summary':summary,'rows':rows,'families':Counter(r['source_family'] for r in rows),'nulls':Counter(r.get('value_status') for r in rows if r.get('value') is None),'registry':registry,'cohorts':cohorts,'historical':historical,'legacy_historical':[r for r in historical if r.get('source_id') not in registered_ids]}

def prose_2012_scope(context):
    selected=context['historical']+[r for c in context['cohorts'] if not c['canonical_rows'] for r in c['csv_rows']]
    prose=[r for r in selected if str(r.get('source_table'))=='prose' and as_int(r.get('data_year'))==2012]
    geography={}
    for key in ['acquisition_per_capita','holdings_per_capita','loans_per_capita','service_population_per_staff']:
        geography[key]={r.get('geography') or r.get('entity_raw') for r in prose if str(r.get('series_id') or r.get('metric_id') or '').endswith(key) and str(r.get('geographic_scope') or r.get('entity_kind') or '').startswith('county')}
    known=set().union(*geography.values());staff=geography['service_population_per_staff']
    return {'records':len(prose),'ratio_counties':{k:len(v) for k,v in geography.items()},'staff_missing_printed_labels':sorted(known-staff)}


def historical_warning(context):
    selected=context['historical']+[r for c in context['cohorts'] if not c['canonical_rows'] for r in c['csv_rows']]
    ambiguous=sum(uncertain_label(r) for r in selected);conflicting=sum(unit_conflict(r) for r in selected);prose=prose_2012_scope(context)
    if prose['records']:
        n=prose['ratio_counties'];missing='、'.join(prose['staff_missing_printed_labels']) or '未另列缺標籤'
        text=f"2012年原文中每人購書／擁書／借閱比率分別列{n['acquisition_per_capita']}／{n['holdings_per_capita']}／{n['loans_per_capita']}縣市；館員服務人口只列{n['service_population_per_staff']}縣市，未列{missing}。"
    else:text='2012年已列原文比率的縣市覆蓋以歷史批次為準。'
    text+='22縣市核心原量表仍未取得，不能由比率反算。閱讀報告所列表只有全國彙總，不能冒充縣市表。'
    ambiguous_by_year=Counter(as_int(r.get('data_year')) for r in selected if uncertain_label(r))
    if ambiguous_by_year.get(2015) or any(105 in c['edition_roc'] for c in context['cohorts']):
        text+=f" 2015原刊部分縣市標籤未確認、兩列均印金門，保留{ambiguous_by_year.get(2015,0):,}筆標籤不確定觀測，不補成連江或硬接現行界線。"
    other_ambiguous={year:count for year,count in sorted(ambiguous_by_year.items(),key=lambda x:str(x[0])) if year!=2015}
    if other_ambiguous:
        text+=' 其他原刊地理標籤疑義按資料年分列：'+ '、'.join(f'{year}年{count}格' for year,count in other_ambiguous.items())+'；原印名稱與數字保留，這些格不計為已確認縣市覆蓋。'
    conflicts_by_year=Counter(as_int(r.get('data_year')) for r in selected if unit_conflict(r))
    if conflicts_by_year.get(2015):
        text+=f" 2015表17標題「場次」與正文「人次」衝突，{conflicts_by_year[2015]:,}格單位保留null及source_heading_conflict_unresolved；人次僅是unit_interpretation_candidate，不是已確認單位。"
    other_conflicts={y:n for y,n in conflicts_by_year.items() if y!=2015}
    if other_conflicts:text+=' 其他原欄頭與正文計量口徑衝突：'+ '、'.join(f'{y}年{n}格' for y,n in sorted(other_conflicts.items()))+'；unit留空，原單位與出處另存，不視為純圖書冊數。'
    counting_basis=Counter(as_int(r.get('data_year')) for r in selected if r.get('unit_status')=='source_heading_counting_basis_unresolved')
    if counting_basis:
        text+=' 原表人數／人次的計數口徑未釐清之格位保留unit=null：'+ '、'.join(f'{year}年{count}格' for year,count in sorted(counting_basis.items(),key=lambda x:str(x[0])))+'；unit_raw照原欄頭保留。'
    return text


def family_scope(name,subset):
    span=display_numbers(years(subset),'年')
    if name=='國資圖公開全國圖表':return f'{span}公開全國圖表；只有全國'
    if name=='國資圖2023開放資料（含縣市）':return f'{span}明確OGDL年度資源；全國、縣市與替代口徑分列，不相加'
    if name==YEARBOOK:return f'{display_numbers({edition(r) for r in subset},"卷")}指定核心表／公共館子群／原文數字；資料年{span}，保留不同出版版本'
    if name==READING:return f'{span}{len(table_groups(subset))}張全國閱讀報告表；包括跨年比較，不是縣市表'
    if name=='主計總處歷史全國統計':return f'{len({r["source_id"] for r in subset})}個來源版本；資料年{span}，重疊版本分開'
    if name=='主計總處縣市公共館數':return f'{span}官方重編地域；來源含國家圖書館，缺值不補0'
    if name=='地方政府開放歷史表':return f'{"、".join(sorted({r["geography"] for r in subset}))}已確認系列；保留原年／月期間與館藏地'
    if name=='地方官方出版統計事實':return f'{span}所列新北、臺南、桃園、彰化、高雄及臺北原刊；全國／縣市／行政區／分館與年／月分開，未明年另存'
    if name=='主計總處後續全國出版統計':return f'{span}113年統計年鑑表4-22；全國含國家圖書館，機關／縣市列未逐列年份保留未知'
    if name=='教育部歷史公共館統計':return f'{span}近16年統計社3表，含國家圖書館；單位千冊／千人次，不與重疊出版版本相加'
    return f'{span}所列來源；按口徑與版本選取'

def source_family_table(context,ai=False):
    groups=defaultdict(list)
    for row in context['rows']:groups[row['source_family']].append(row)
    ordered=[f for f in FAMILY_ORDER if f in groups]+sorted(set(groups)-set(FAMILY_ORDER))
    lines=['| `source_family` | 適用的來源選擇 |','|---|---|'] if ai else ['| 來源族群 | 已整理的範圍 | 紀錄數 |','|---|---|---:|']
    for name in ordered:
        selection=family_scope(name,groups[name]);ids=sorted({r['source_id'] for r in groups[name]})
        if ai and len(ids)<=3:selection+='；'+('、'.join('`'+v+'`' for v in ids))
        lines.append(f'| {name} | {selection} |'+('' if ai else f' {len(groups[name]):,} |'))
    return '\n'.join(lines)

def bounded_description(context):
    counts=context['nulls'];return f"目前 **{len(context['rows']):,} 筆來源觀測紀錄**，含 **{counts.get('not_available_in_source',0):,} 格明示缺值**、**{counts.get('source_blank',0):,} 格原印留白**、**{counts.get('source_marker',0):,} 格原印文字狀態**及不同出版版本。紀錄數不是圖書館間數，也不能整表相加。"

def replace_between(text,start,end,body):
    a=text.index(start)+len(start);b=text.index(end,a)
    return text[:a]+'\n\n'+body.strip()+'\n\n'+text[b:]

def generated_block(text,name,body):
    start=f'<!-- BEGIN {name} -->';end=f'<!-- END {name} -->';block=start+'\n'+body.strip()+'\n'+end
    if start in text:return text[:text.index(start)]+block+text[text.index(end)+len(end):]
    return text.rstrip()+'\n\n'+block+'\n'

def historical_batch_payload(context):
    batches=[]
    for c in context['cohorts']:
        batches.append({k:c[k] for k in ['id','review_status','derived_csv','source_csv_available','source_ids','data_years','edition_roc','publication_dates','source_csv_counts','canonical_counts','uncertain_label_records','unit_conflict_records','table_inventory','metadata_paths','scope']})
        batches[-1]['completion_scope']='All cells/spans of explicitly listed reviewed tables or prose only; not every table/chapter/year/county.'
        batches[-1]['canonical_status']='source_not_available_or_empty' if not c['source_csv_available'] or not c['csv_rows'] else 'all_source_count_present' if c['canonical_counts']['records']==c['source_csv_counts']['records'] else 'not_or_partly_in_current_canonical'
    return {'schema_version':'1.0.0','data_version':context['summary']['version'],'data_build':context['summary'].get('built_at'),'registry_path':'data/reviewed_historical_cohorts.json','registered_cohorts':batches,'registered_source_cells':sum(c['source_csv_counts']['records'] for c in context['cohorts']),'historical_canonical_records':len(context['historical']),'legacy_canonical_scope':{'records':len(context['legacy_historical']),'tables':table_groups(context['legacy_historical']),'statement':'既有正式來源觀測；未因出現在canonical就新增可執行批次。'},'warning':historical_warning(context),'all_county_years_complete':False}

def write_historical_batches(context):
    root=context['root'];payload=historical_batch_payload(context);write_json(root/'docs/historical-batches.json',payload)
    lines=['# 已覆核的歷史來源批次','',f"資料版本v{context['summary']['version']}。由[已覆核批次清單](../data/reviewed_historical_cohorts.json)、實際CSV及canonical產生；CSV格位與正式觀測數分列，不把不同來源版本相加成業務量。",'', '|批次|資料年|年鑑卷號|來源CSV格位／有值／留白／其他缺值|正式觀測|標籤待釐清|單位衝突|','|---|---|---|---|---:|---:|---:|']
    for c in payload['registered_cohorts']:
        n=c['source_csv_counts'];lines.append(f"|{c['id']}|{display_numbers(c['data_years'])}|{display_numbers(c['edition_roc'])}|{n['records']:,}／{n['numeric_cells']:,}／{n['source_blank_cells']:,}／{n['other_missing_cells']:,}|{c['canonical_counts']['records']:,}|{c['uncertain_label_records']:,}|{c['unit_conflict_records']:,}|")
    lines+=['',f"另有{len(context['legacy_historical']):,}筆既有正式歷史觀測未列入這組新增可執行批次；原表清單仍保存在JSON。完整性只及每批所列的表格、公共館子群或原文段落，不是整冊、整章所有表或全臺各縣市全部歷年。",'',historical_warning(context),'','2014及其他原表差異保留原值與旗標；標籤或單位未知不以推算值補正。成長率需讀完整比較期間，原印0、留白和明示缺值分開。原件PDF／完整正文不隨公開包散布。','', '|批次|原表／原文段|資料年|PDF頁|格位|','|---|---|---|---|---:|']
    for c in payload['registered_cohorts']:
        for table in c['table_inventory']:lines.append(f"|{c['id']}|{table['source_table']}：{table['source_table_title']}|{display_numbers(table['data_years'])}|{','.join(table['pdf_pages'])}|{table['source_cells']:,}|")
    lines+=['','逐表版次、SHA、值狀態及來源metadata路徑見[機器清單](historical-batches.json)。未取得只表示本輪查核範圍的缺口，不能解讀成官方不存在資料。','']
    (root/'docs/historical-batches.md').write_text('\n'.join(lines))

def update_backlog(context):
    root=context['root'];path=root/'docs/source-backlog.json';backlog=read_json(path)
    ncl=[r for r in context['rows'] if r['source_family']==YEARBOOK];editions=sorted({edition(r) for r in ncl if edition(r) is not None})
    span=display_numbers(editions,'卷');unknown=f'{max(editions)+1}卷以後及{min(editions)-1}卷以前' if editions else '其他已見目錄卷'
    claim=f'NCL{span}僅所列核心表、公共館子群及明列原文數字；2012縣市核心原量缺口仍存。'
    backlog['scope_claims']=[x for x in backlog.get('scope_claims',[]) if not x.startswith(('NCL3年','NCL96–103卷','NCL'))]+[claim]
    backlog['constraints']=[x for x in backlog.get('constraints',[]) if not x.startswith('本清單未新下載')]
    evidence=list(dict.fromkeys(p for c in context['cohorts'] for p in c['metadata_paths']))
    prose=prose_2012_scope(context)
    known_2012={'edition_roc':102,'data_year':2012,'scope':f"已完成公共館章一至八節{prose['records']}個明列原文數字及統計章公共館子群；各比率覆蓋見county_ratio_coverage。22縣市核心原量表仍未取得，不從比率反算。",'county_ratio_coverage':prose,'checked_sources':['102卷公共圖書館章與統計章','103卷〈102年全國公共圖書館評鑑工作紀要〉','國資圖舊年度連結及現行公開表單','101年閱讀習慣報告原附件及改版官網新附件'],'exclusions':['評鑑章的達標／未達標館數與受評／得獎館數不是2012營運原量；不納入核心表。'],'link_resolution':'舊nclfile下載逾時後，已從現行官方gallery取得新file_pool附件；閱讀五表另作全國批次，不冒充縣市表。','evidence':['research/ncl-2012-core-search.md','raw/ncl-2012/source-search-log.json','docs/historical-batches.json']}
    for family in backlog['families']:
        if family['family_id']=='ncl_yearbook_public_library_chapters':
            family['completed_scope']={'data_years':years(ncl),'edition_roc':editions,'long_rows':len(ncl),'tables':table_groups(ncl),'completion_statement':'只完整整理所列核心表、公共館子群與原文明列數字；不是整冊或所有縣市原量完整。'}
            family['known_not_ingested']=[known_2012]
            for cohort in context['cohorts']:
                for metadata_path in cohort['metadata_paths']:
                    meta=read_json(root/metadata_path,{})
                    if isinstance(meta,dict) and meta.get('known_not_ingested'):
                        family['known_not_ingested'].append({'cohort':cohort['id'],'scope':'Known original tables outside the explicitly completed core cohort; not unavailable.','tables':meta['known_not_ingested'],'evidence':metadata_path})
            family['unknown_scope']=[unknown+'仍待逐表查核；已處理卷的其他未列來源也可能有缺口。','官方目錄可見不等於全部欄位、縣市標籤或歷年可比性已確認。']
            family['evidence']=list(dict.fromkeys(family.get('evidence',[])+evidence+['docs/historical-batches.json']))
        if family['family_id']=='ncl_all_type_statistical_chapters':
            stats=[r for r in ncl if 'statistic' in r['source_id']]
            family['completed_scope']['selected_public_library_subsets']={'records':len(stats),'tables':table_groups(stats),'statement':'僅明列公共館子群；其他館型與跨型總計不併入公共館資料。'}
    reading=[r for r in context['rows'] if r['source_family']==READING]
    reading_family=next((f for f in backlog['families'] if f['family_id']=='ncl_reading_report_tables'),None)
    if reading_family is None:reading_family={'family_id':'ncl_reading_report_tables','owner':'國家圖書館'};backlog['families'].append(reading_family)
    reading_family.update(status='completed_bounded_scope' if reading else 'not_in_current_canonical',urls=sorted({r.get('source_page_url') for r in reading if r.get('source_page_url')}),completed_scope={'records':len(reading),'data_years':years(reading),'tables':table_groups(reading),'completion_statement':'所列全國閱讀報告五表；兩個成長率格為2011至2012比較，不能當年度業務量。'},known_not_ingested=['所列五表不提供22縣市分列，不能補縣市核心原量缺口。'],unknown_scope=['閱讀報告與年鑑母體、跨表類別合計不同；未認證相容性。'],license_scope='只整理公開統計事實；PDF全文及重製全圖未宣稱開放。',evidence=['docs/historical-batches.json','research/ncl-reading-2012-independent-review.json'])
    cohorts={c['id']:c for c in context['cohorts']}
    tasks=backlog.get('ordered_batches',backlog.get('backlog',[]))
    for task in tasks:
        if task['task_id']=='B01' and 'ncl_gap' in cohorts:
            n=cohorts['ncl_gap']['source_csv_counts'];task.update(status='completed_bounded_scope',completion=f"已列四張缺表全量{n['records']:,}格：{n['numeric_cells']:,}有值、{n['source_blank_cells']:,}留白；逐表與獨立回查見historical-batches。",known_not_ingested=[],unknowns=['原刊算術差異保留，未改官方原值。'])
        if task['task_id']=='B03':task.update(status='partially_completed_known_tables',completion=f'{span}已列核心表／子群／原文批次見docs/historical-batches.json；其他卷及2012核心原量缺口維持待查。')
        if task['task_id']=='B08':task['unknowns']=['歷年定義是否完全相容仍待逐年認證；實際表已取得。']
    inventory=backlog['official_yearbook_inventory']
    for item in inventory['items']:
        ed=as_int(item.get('edition_roc_raw'));subset=[r for r in ncl if edition(r)==ed]
        if not subset:continue
        data_years=years(subset);uncertain=sum(uncertain_label(r) for r in subset)
        item.update(data_year_verified=max(data_years) if data_years else None,data_years_verified=data_years,ingestion_status='specific_core_scope_completed_with_uncertain_source_labels' if uncertain else 'specific_operational_tables_public_subset_or_prose_completed_only',uncertain_label_records=uncertain,scope_evidence='docs/historical-batches.json；完整性只及列明原表／原文，標籤不確定不計為已確認縣市值。')
    inventory['checked_via']='官方目錄與canonical／reviewed registry所列原表原文批次核對；其他卷僅目錄。'
    catalogue_check=root/'raw/ncl-2022/catalog-metadata.json'
    if catalogue_check.exists():
        latest=read_json(catalogue_check)
        inventory['catalogue_front_page_check']={k:latest[k] for k in ('url','final_url','retrieved_at','sha256','entry_links')}
        inventory['catalogue_front_page_check']['scope']='本輪首頁可見12個入口，首項114卷；未見後續卷不代表官方不存在，也不把卷號當資料年。'
    write_json(path,backlog)
    lines=['# 來源分組待辦','','以[source-backlog.json](source-backlog.json)為機器主檔；[歷史批次](historical-batches.md)依registry與實際觀測產生。完成只及列明範圍，未查不表示無資料。','',f'B01與B08維持已完成指定範圍。年鑑{span}的已列核心表、公共館子群與原文數字已整理；{unknown}仍待查。', '',historical_warning(context),'','2012本輪已查公共館章、統計章、評鑑章、國資圖舊連結及閱讀報告；評鑑達標數排除，失敗舊附件已找到官網新網址。仍未取得的22縣市核心原量表不推稱不存在。其他來源的授權與更新政策維持各族群原記錄。','']
    (root/'docs/source-backlog.md').write_text('\n'.join(lines))

def write_discovered_summary(context):
    root=context['root'];path=root/'raw/discovered-20261028/extraction-metadata.json'
    if not path.exists():return
    batch=read_json(path);rows=[r for r in context['rows'] if str(r['source_id']).startswith('discovered-')]
    if len(rows)!=batch['canonical_observations_added']:raise ValueError('Documentation requires the complete new source batch')
    body=f"""## 本版新增官方原表整批入庫

v{context['summary']['version']}新增{len(rows):,}個原格，來自{batch['source_documents']}份官方原件的完整指定表及續頁。早期年鑑2001–2004、教育部1994–2009、主計2010–2024全國原表，以及新北、臺南、桃園、彰化、高雄和臺北所列原刊分開保存。高雄含表3-2全部52頁、各館年度及12個月；臺北本批僅2012年12月。

新增格包含{batch['value_statuses'].get('reported',0):,}個數值、{batch['value_statuses'].get('source_blank',0):,}個原刊留白、{batch['value_statuses'].get('source_marker',0):,}個原刊符號／複合格；{batch['unresolved_period_records']:,}格期間未確認。原格數不是館數，合計、分項、年合計與月值不得整表相加。原年份不明不填出版年；原件缺值不補0。新北館藏2010前後分段；高雄年度館藏／期刊彙計與借閱率口徑未明，不當年底庫存趨勢。

[完整來源／表格範圍](../raw/discovered-20261028/extraction-metadata.json)與[逐筆原格驗收](../scripts/validate_discovered_20261028.py)可重跑。各格保留原字串、單位、官方原件URL、SHA、原頁表列欄、版本及公式／分母；讀source_time_reference的JSON可取原表脈絡、合併格與公式等額外來源限定，source_cell_note_raw保留核對方法。369格掃描資料以Apple Vision及AI原圖核讀，沒有宣稱人類逐格雙校；重複OCR不是獨立引擎。

原始發現登錄及396格研究probe是v0.8歷史快照，不算額外觀測；正式映射見本批metadata與derived/discovered_20261028_observations.jsonl。臺北2012年刊權利衝突及三份跨館型統計章待核子群仍隔離。2012完整22縣市核心原量仍缺，不從比率推算，不跨來源拼成全臺面板。

16個複合／非單一量原格另逐格登錄於scripts/reviewed_non_scalar_literals.json（含原件SHA、原文及定位）。例如主館／括弧分館、各1人、每鄉各2不能任挑一個數字作總量；source_marker及selected_source_missing在這些格表示沒有單一可用純量，不表示原件沒有資料。必須同讀raw_value、原註與該登錄，不推算補值。

沿用每月維護；新增歷史固定原件每365天到期回查，來源與擷取器未變則沿用完整批次。原件更動暫存待覆核、失敗保留前版，不把新下載內容自動當作可公開授權。"""
    # Links from root documents are relative to the repository root.
    body=body.replace('(../raw/','(raw/').replace('(../scripts/','(scripts/')
    for name in ('README.md','COVERAGE.md','AI_USAGE.md'):
        p=root/name;p.write_text(generated_block(p.read_text(),'discovered-20261028',body))
    p=root/'llms.txt';p.write_text(generated_block(p.read_text(),'discovered-20261028',f"v{context['summary']['version']} complete selected new originals: {len(rows)} canonical cells / 12 documents; raw/discovered-20261028/extraction-metadata.json. Unknown year remains null ({batch['unresolved_period_records']}); source_time_reference JSON preserves source context/merged scope/formula; source_cell_note_raw preserves verification method. Historical discovery/probe v0.8 is not another observation layer. No aggregation, imputation or cross-source panel permission."))
    backlog=read_json(root/'docs/source-backlog.json')
    family={'family_id':'reviewed_official_discovery_20261028','owner':'所列中央與地方官方出版機關','status':'completed_selected_tables_only','completed_scope':batch,'known_not_ingested':['臺北2012年刊：權利衝突維持隔離。','三份早期跨館型統計章：公共館子群未覆核，維持候選。','各原刊未列入本批的其他原表／年度仍待查，不表示不存在。'],'unknown_scope':['未取得2012全22縣市核心原量表。','部分原刊年份、單位、年度彙計或分館涵蓋仍未明，逐格照實保存。'],'evidence':['docs/source-discovery-20261028.json','raw/discovered-20261028/extraction-metadata.json','docs/historical-batches.json']}
    backlog['families']=[f for f in backlog['families'] if f['family_id']!=family['family_id']]+[family]
    write_json(root/'docs/source-backlog.json',backlog)


def main():
    context=load_context();root=context['root'];summary=context['summary'];version=summary['version'];description=bounded_description(context);warning=historical_warning(context)
    write_historical_batches(context)
    p=root/'README.md';s=p.read_text();s=re.sub(r'版本 \*\*[^*]+\*\*',f'版本 **{version}**',s);s=re.sub(r'v[\d.]+下載',f'v{version}下載',s);s=re.sub(r'/releases/tag/v[\d.]+',f'/releases/tag/v{version}',s)
    if summary.get('built_at'):s=re.sub(r'資料建置日 \*\*\d{4}-\d{2}-\d{2}\*\*',f"資料建置日 **{summary['built_at'][:10]}**",s)
    body=description+'\n\n'+source_family_table(context)+'\n\n逐批格數、資料年、版次與指定表／原文範圍見[已覆核歷史批次](docs/historical-batches.md)及[COVERAGE.md](COVERAGE.md)。\n\n'+warning
    s=replace_between(s,'## 目前收錄什麼','**完整性指',body);p.write_text(s)
    p=root/'AI_USAGE.md';s=p.read_text();s=re.sub(r'^目前 [\d,]+ 筆[^\n]+',description.replace('**','')+'「所列來源全量」不等於所有縣市、所有年度或每間館完整。缺口不表示官方沒有公布。',s,flags=re.M)
    s=replace_between(s,'### 來源族群','### 數值與缺值',source_family_table(context,ai=True)+'\n\n'+warning+'\n\n原表、原文數字與閱讀五表的批次範圍見[歷史批次](docs/historical-batches.md)。')
    null_line=f"- `value IS NULL` 必須同讀 `value_status` 與 `raw_value`。本版 `{context['nulls'].get('not_available_in_source',0)}` 格 `not_available_in_source` 保留明示缺值符號，`{context['nulls'].get('source_blank',0)}` 格 `source_blank` 保留原刊留白，`{context['nulls'].get('source_marker',0)}` 格 `source_marker` 保留原印「無」「未新增」「未統計」等文字狀態；這些文字不自行改成0或推定不適用，均不推算補值。"
    s=re.sub(r'^- `value IS NULL` 必須同讀[^\n]+',null_line,s,flags=re.M);p.write_text(s)
    p=root/'llms.txt';s=p.read_text();s=re.sub(r'版本 [\d.]+；',f'版本 {version}；',s);s=re.sub(r'/releases/tag/v[\d.]+',f'/releases/tag/v{version}',s);s=re.sub(r'^(?:19,975 筆是觀測／來源版本紀錄|目前 [\d,]+ 筆來源觀測紀錄)[^\n]+',description.replace('**','')+' 批次完整性見docs/historical-batches.json；不宣稱全臺歷年皆完整。',s,flags=re.M)
    if summary.get('built_at'):s=re.sub(r'建置日 \d{4}-\d{2}-\d{2}',f"建置日 {summary['built_at'][:10]}",s)
    s=s.replace('第六族群 source_family=主計總處縣市公共館數','source_family=主計總處縣市公共館數')
    s=generated_block(s,'generated-historical-scope','來源族群包含source_family='+READING+'；與年鑑分開。\n'+warning+'\n歷史批次入口：docs/historical-batches.json及docs/historical-batches.md。');p.write_text(s)
    p=root/'CITATION.cff';s=p.read_text();s=re.sub(r'^version: .+$','version: '+version,s,flags=re.M)
    if summary.get('built_at'):s=re.sub(r'^date-released: .+$','date-released: '+summary['built_at'][:10],s,flags=re.M)
    p.write_text(s)
    update_backlog(context)
    write_discovered_summary(context)
    if record_io.compressed(root):
        for name in ('README.md','AI_USAGE.md','llms.txt','COVERAGE.md'):
            path=root/name
            text=path.read_text().replace('data/combined/observations.jsonl.gz','data/combined/observations.jsonl')
            path.write_text(text.replace('data/combined/observations.jsonl','data/combined/observations.jsonl.gz'))
    from build_phase1_documentation import main as phase1_docs
    phase1_docs()
    print('documentation',version,len(context['rows']),'reviewed cohorts',len(context['cohorts']))
if __name__=='__main__':main()
