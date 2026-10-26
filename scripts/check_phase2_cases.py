#!/usr/bin/env python3
"""Independent frozen source cases and full-record readback for phase two.

This checker never calls the builder or edits source/annotation data. A source
adjudication is explicit and separate from the unchanged pre-engine fixtures.
"""
from __future__ import annotations
import argparse,collections,copy,gzip,hashlib,importlib.util,json,re,sys
from decimal import Decimal
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
FROZEN='f2e968150db64ac338543f5371a5d962d9d01301672f07430bdb3d941f22aff9'
LAYER_ALIASES={'canonical':'canonical','phase1_local_statistical_cells':'local_statistical_cells','phase1_programme_quantities':'programme_quantities'}
LAYERS={'canonical':'data/combined/observations.jsonl','local_statistical_cells':'derived/phase1_local_sources_long.jsonl','programme_quantities':'derived/ncl_2005_programmes_long.jsonl'}
PUBLICATION_FIELDS={'snapshot_distribution','public_evidence_path','public_evidence_sha256','public_projection_policy','original_fields'}
# These frozen cases concern another operation. Calling compare() alone cannot
# prove a sum, source rewrite, imputation, recoding, or unique-person guard.
NON_JOIN={'P2-C004','P2-C007','P2-C008','P2-C010','P2-C011','P2-C013','P2-C017','P2-C018','P2-C022','P2-C023','P2-C024','P2-C025','P2-C027','P2-C029','P2-C030','P2-C031','P2-C033','P2-C037'}

def stable(x):return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':'))
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def read_rows(path):
    path=path if path.exists() else Path(str(path)+'.gz')
    with (gzip.open(path,'rt') if path.suffix=='.gz' else path.open()) as stream:
        for line in stream:
            if line.strip():yield json.loads(line)
def decoded_flags(value):
    if isinstance(value,list):return value
    if not value:return []
    try:parsed=json.loads(value)
    except (ValueError,TypeError):return [str(value)]
    return parsed if isinstance(parsed,list) else [str(parsed)]
def load_engine(root):
    sys.path.insert(0,str(root/'scripts'))
    spec=importlib.util.spec_from_file_location('phase2_under_independent_review',root/'scripts/phase2_engine.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module

def review(root,cases_only=False,case_ids=None,skip_cli=False):
    engine=load_engine(root);engine_start=sha(root/'scripts/phase2_engine.py')
    fixture_path=root/'research/phase2-independent-cases.json';fixtures=json.loads(fixture_path.read_text())
    payload={k:fixtures[k] for k in ('real_cases','synthetic_cases','record_evidence','refusal_conditions')}
    actual_fixture_hash=hashlib.sha256(stable(payload).encode()).hexdigest()
    report={'status':'pending','execution':'Checker authored by the independent source-case reviewer; controller completed CLI/public-projection adapters and ran it after reviewer capacity failure. Frozen pre-engine expectations are unchanged.','scope':'fresh engine methods only' if cases_only else 'fresh methods and full materialized quantitative layer','assertions':0,'blockers':[],'notes':[],'frozen_cases_content_sha256':actual_fixture_hash,'frozen_cases_file_sha256':sha(fixture_path),'engine_sha256':engine_start,'source_adjudications':[],'cases':[],'synthetic':[]}
    def check(ok,reason,detail=None):
        report['assertions']+=1
        if not ok and len(report['blockers'])<80:report['blockers'].append({'reason':reason,'detail':detail})
    check(actual_fixture_hash==FROZEN==fixtures['initial_frozen_cases_sha256'],'Frozen pre-engine cases changed')
    cards=engine.evidence_cards(root);by_card={c['evidence_id']:c for c in cards};index=engine.card_index(cards)
    raw={};fingerprints={};source_paths={}
    for layer,relative in LAYERS.items():
        path=root/relative;path=path if path.exists() else Path(str(path)+'.gz');source_paths[layer]=str(path.relative_to(root))
        h=hashlib.sha256();h.update(b'[');n=0
        for row in read_rows(path):
            key=layer+':'+row['observation_id'];check(key not in raw,'Duplicate source-layer record key',key)
            raw[key]=row
            if n:h.update(b',')
            h.update(stable({k:v for k,v in row.items() if k not in PUBLICATION_FIELDS}).encode());n+=1
        h.update(b']');fingerprints[layer]={'records':n,'semantic_sha256':h.hexdigest(),'file_sha256':sha(path),'path':str(path.relative_to(root))}
    check(len(raw)==56496,'Quantitative scope count changed',len(raw))
    # Fresh selected records; no cached annotation can conceal a method defect.
    selected={}
    for ref in fixtures['record_evidence']:
        key=LAYER_ALIASES[ref['layer']]+':'+ref['observation_id'];row=raw[key]
        for field,want in ref.items():
            if field in row:check(stable(row[field])==stable(want),'Frozen source record field changed',{'record_key':key,'field':field})
        selected[key]=engine.annotate(key.split(':',1)[0],row,index[key.split(':',1)[0],row['observation_id']])
    refs={r['observation_id']:r for r in fixtures['record_evidence']}
    def case_keys(case):return [LAYER_ALIASES[refs[x]['layer']]+':'+x for x in case['record_ids']]
    # Original English note has now been independently image-read, separately
    # from implementation. Keep the original expectation in fixtures untouched.
    pdf=root/'raw/ncl-historical/dgbas-social-indicators-2005.pdf'
    expected_pdf_sha='066ffff121ccc2d86280002cf4aa4432d8ef0ada0f4ab6dfe4d6615d0efa8f69'
    if pdf.exists():check(sha(pdf)==expected_pdf_sha,'DGBAS source-adjudication PDF changed')
    else:report['notes'].append('Original PDF absent in public projection; source adjudication relies on the recorded prepublication original-page review, not a fresh full-original audit.')
    adjudication={'case_id':'P2-C005','original_expected_decision':'unresolved','source_qualified_decision':'limited_published_panel','source_sha256':expected_pdf_sha,'source_url':'https://ws.dgbas.gov.tw/public/data/331311404571.pdf#page=107','source_locator':'PDF107; printed123; English note5; Chinese note5 on PDF106/print122','original_note_short':'Since 2000, number of readers only included those who borrowed books out of libraries.','basis':'Direct PDFium text and rendered original page read after the new evidence card; explicitly supports <=1999 / >=2000 boundary in this edition. Parent confirmed source adjudication. Does not apply to 2011 edition with opposing English/Chinese direction.','frozen_fixture_not_modified':True}
    report['source_adjudications'].append(adjudication)
    for case in fixtures['real_cases']:
        if case_ids and case['case_id'] not in case_ids:continue
        keys=case_keys(case);anns=[selected[k] for k in keys];row={'case_id':case['case_id'],'frozen_expected_decision':case['expected_decision'],'requested_operation':case['requested_operation'],'record_keys':keys,'compare_applicable':len(anns)>1 and case['case_id'] not in NON_JOIN,'annotation_statuses':[a['comparison_status'] for a in anns]}
        if row['compare_applicable']:
            results=[engine.compare(anns[0],a) for a in anns[1:]];row['compare_results']=results
            expected=adjudication['source_qualified_decision'] if case['case_id']=='P2-C005' else case['expected_decision']
            if expected=='limited_published_panel':check(all(x['status']=='published_panel_limited' for x in results),'Required limited-published-panel case not supported',case['case_id'])
            else:check(all(x['status']!='published_panel_limited' for x in results),'Unsafe positive against frozen source case',{'case_id':case['case_id'],'results':results})
            row['source_adjudication_applies']=case['case_id']=='P2-C005'
            row['stricter_rejection_not_treated_as_error']=expected=='unresolved' and any(x['status']=='incompatible' for x in results)
        else:row['compare_not_substitute_for_operation_guard']=True
        for key,ann in zip(keys,anns):
            r=raw[key]
            if r.get('value') is None:check(ann['original_value'] is None and ann['comparison_value'] is None,'Missing/marker/conflict value imputed',key)
            if r.get('period_status') in ('catalog_title_year_only_attachment_undated','source_sheet_name_header_period_conflict_unresolved'):check(ann['comparison_year'] is None and ann['comparison_month'] is None,'Unresolved original period assigned',key)
            if r.get('unit_status')=='source_heading_conflict_unresolved':check(ann['comparison_unit'] is None,'Candidate unit promoted to confirmed',key)
            if r.get('geographic_scope') in ('county_source_label_uncertain','county_source_label_duplicate_unresolved'):check(ann['comparison_status']=='unresolved','Uncertain original geography certified',key)
        report['cases'].append(row)
    # Replay six frozen synthetic intentions by changing one facet at a time
    # on real reviewed table208 prototypes, without changing any source file.
    prototype_case=next(c for c in fixtures['real_cases'] if c['case_id']=='P2-C034');pk=case_keys(prototype_case);layer='canonical'
    left_raw,right_raw=raw[pk[0]],raw[pk[1]]
    def ann(r):return engine.annotate(layer,r,index[layer,r['observation_id']])
    def synthetic(id,description,ok,detail=None):
        check(ok,'Synthetic/defensive regression failed',{'case_id':id,'description':description,'detail':detail});report['synthetic'].append({'case_id':id,'description':description,'pass':bool(ok),'detail':detail})
    a,b=copy.deepcopy(left_raw),copy.deepcopy(right_raw);a.update(unit=None,unit_raw=None,unit_status='source_unit_unconfirmed_or_not_printed');b.update(unit=None,unit_raw=None,unit_status='source_unit_unconfirmed_or_not_printed');aa,bb=ann(a),ann(b)
    synthetic('P2-S001','Unknown units do not become an equivalent known unit',aa['comparison_unit'] is None and bb['comparison_unit'] is None and engine.compare(aa,bb)['status']!='published_panel_limited')
    a,b=copy.deepcopy(left_raw),copy.deepcopy(right_raw);a.update(indicator='資料費預算',unit='元');b.update(indicator='資料費決算',unit='元');synthetic('P2-S002','Budget and actual conflict despite matching label family/value/unit',engine.compare(ann(a),ann(b))['status']=='incompatible')
    a=copy.deepcopy(left_raw);a.update(value=None,raw_value='-',value_status='source_display_typed_value_conflict_unresolved');aa=ann(a);synthetic('P2-S003','Typed-zero conflict remains null and cannot be positive',aa['comparison_value'] is None and aa['original_value'] is None and engine.compare(aa,ann(right_raw))['status']!='published_panel_limited')
    b=copy.deepcopy(right_raw);b['source_table']='synthetic_other_table';synthetic('P2-S004','Same file different table cannot be one published panel',engine.compare(ann(left_raw),ann(b))['status']!='published_panel_limited')
    b=copy.deepcopy(right_raw);b['source_edition']='synthetic_other_edition';synthetic('P2-S005','Different editions do not silently merge',engine.compare(ann(left_raw),ann(b))['status']!='published_panel_limited')
    b=copy.deepcopy(right_raw);b['aggregation_role']='reported_component';synthetic('P2-S006','A total/component distinction is retained in join facets',engine.compare(ann(left_raw),ann(b))['status']!='published_panel_limited',{'sum_operation_still_requires_separate_guard':True})
    for value in [None,True,'2018',0,10000]:
        a=copy.deepcopy(left_raw);a['data_year']=value;aa=ann(a);result=engine.compare(aa,ann(right_raw));synthetic('P2-D-year-'+repr(value),'Necessary year must be a valid non-Boolean integer',aa['comparison_status']!='published_panel_limited' and result['status']!='published_panel_limited',{'input_year':value,'annotation_status':aa['comparison_status'],'compare_status':result['status']})
    monthly_key='local_statistical_cells:south-hualien-library-lending-409-reader:114年8月:F10';mr=raw[monthly_key];mc=index['local_statistical_cells',mr['observation_id']]
    for value in [None,0,13,True,'8']:
        r=copy.deepcopy(mr);r['period_month']=value;aa=engine.annotate('local_statistical_cells',r,mc);synthetic('P2-D-month-'+repr(value),'Monthly record requires an actual valid month integer',aa['comparison_status']!='published_panel_limited',{'input_month':value,'status':aa['comparison_status']})
    # Source-series-only remains unqualified even if every visible facet matches.
    ss_case=next(c for c in fixtures['real_cases'] if c['case_id']=='P2-C009');ss=[selected[k] for k in case_keys(ss_case)];synthetic('P2-D-source-series-only','Source-labelled series must not become a certified join',engine.compare(*ss)['status']!='published_panel_limited')
    # Unsupported operations need their own guard, never infer it from compare.
    report['cli_operation_guard']={'status':'not_checked_yet','note':'compare() is exclusively a same-original-entity time-series join. Non-join cases remain explicitly out of scope until the CLI operation guard is exercised.'}
    if not skip_cli:
        guard=getattr(engine,'guard_operation',None)
        if guard is None:check(False,'CLI/non-join operation guard has not been provided')
        else:
            import subprocess
            operations=['sum','impute','infer-unique-people','recode-geography','coerce-zero','cross-source-splice']
            checked=[]
            for operation in operations:
                result=json.loads(subprocess.check_output([sys.executable,str(root/'scripts/compare_definitions.py'),'--root',str(root),'--operation',operation],text=True))
                check(result['status']=='incompatible' and result.get('data_modified') is False,'CLI operation guard did not refuse unsupported inference',operation);checked.append(operation)
            report['cli_operation_guard']={'status':'PASS','function':'phase2_engine.guard_operation; actual compare_definitions.py CLI subprocess replay','operations_checked':checked}
    if not cases_only:
        summary=json.loads((root/'docs/phase2-summary.json').read_text());annotations=list(read_rows(root/'derived/phase2/annotations.jsonl.gz'));amap={a['record_key']:a for a in annotations}
        check(len(annotations)==len(amap)==len(raw)==summary['total_quantitative_records']==56496,'Materialized annotation scope/identity differs')
        check(set(amap)==set(raw),'Original quantitative layer IDs lost or added')
        for layer,data in fingerprints.items():check(data['semantic_sha256']==summary['layer_raw_fingerprints'][layer],'Independent raw layer fingerprint differs',layer)
        check(summary['inputs']['scripts/phase2_engine.py']==engine_start,'Materialized output is stale relative to engine')
        ups=[];grid_rows=collections.defaultdict(list);positive_groups=collections.defaultdict(list);source_cache={}
        for key,a in amap.items():
            r=raw[key];layer=a['layer'];card=by_card[a['evidence_id']]
            for field,want in [('observation_id',r['observation_id']),('source_id',r['source_id']),('source_sha256',r['source_sha256']),('source_locator',r['source_locator']),('original_value',r.get('value')),('raw_value',r.get('raw_value',r.get('value_raw'))),('value_status',r.get('value_status')),('quality_flags_original',decoded_flags(r.get('quality_flags')))]:check(stable(a[field])==stable(want),'Materialized source value/provenance changed',{'key':key,'field':field})
            check(card['source_id']==r['source_id'] and card['source_sha256']==r['source_sha256'] and r['observation_id'] in card.get('observation_ids',[]),'Primary evidence not linked to exact source record',key)
            support_ids=a.get('supporting_evidence_ids',[]);check(len(support_ids)==len(set(support_ids)) and a['evidence_id'] not in support_ids,'Duplicate evidence ID',key)
            for eid in support_ids:
                c=by_card[eid];check(c['source_id']==r['source_id'] and c['source_sha256']==r['source_sha256'] and r['observation_id'] in c.get('observation_ids',[]),'Supporting evidence not linked',key)
            if a['comparison_value'] is not None:
                check(r.get('value') is not None and a['comparison_unit'] is not None,'Comparison value inferred without known original value/unit',key)
                check(Decimal(a['comparison_value'])==Decimal(str(r['value']))*Decimal(a['unit_scale']),'Exact numeric scale differs',key)
            elif r.get('value') is None:check(a['comparison_value'] is None,'Null became number',key)
            if r.get('period_status') in ('catalog_title_year_only_attachment_undated','source_sheet_name_header_period_conflict_unresolved'):check(a['comparison_year'] is None and a['comparison_month'] is None and a['comparison_status']=='unresolved','Unresolved period certified',key)
            if r.get('value_status')=='source_display_typed_value_conflict_unresolved':check(a['comparison_value'] is None and a['comparison_status']=='unresolved','Typed-zero display conflict certified/imputed',key)
            if layer=='programme_quantities':check(a['comparison_year'] is None and a['comparison_status']=='unresolved','Programme made an annual source observation',key)
            if r.get('temporal_kind')=='survey_response_count':check(a['period_kind']!='partial_year_source','Bracketed response count confused with partial-year period',key)
            if a['unit_audit_status']=='literal_suffix_verified':
                field=r.get('source_field') or r.get('indicator');expected='冊' if field.endswith('冊數') else '人次' if field.endswith('人次') else None
                check(layer=='canonical' and r.get('source_family')=='地方政府開放歷史表' and r.get('unit') in (None,'') and expected==a['comparison_unit'],'Unjustified unit suffix promotion',key)
                check(field in card.get('source_fields',[]),'Promoted unit field absent from reviewed source card',key)
                rel=r['source_snapshot_path']
                if rel not in source_cache:
                    path=root/rel;expected=r['source_sha256']
                    if not path.exists() and r.get('public_evidence_path'):
                        path=root/r['public_evidence_path'];expected=r['public_evidence_sha256'];report['notes'].append('Suffix field verified on the separately hashed public statistical projection; original document SHA remains unchanged: '+rel)
                    source_cache[rel]=(sha(path),json.loads(path.read_text()),expected)
                source_sha,original,expected=source_cache[rel];m=re.fullmatch(r'JSON array\[([0-9]+)\]; metric=(.+)',r['source_locator']);check(source_sha==expected and m is not None,'Unit suffix original/projection source/locator differs',key)
                if m:check(m.group(2)==field and isinstance(original,list) and field in original[int(m.group(1))],'Literal promoted suffix is not an original JSON field',key)
                ups.append(key)
            if layer=='local_statistical_cells':grid_rows[(r['source_id'],r['source_sheet'])].append(r)
            if a['comparison_status']=='published_panel_limited':
                positive_groups[a['comparison_group_id']].append(a)
                check(not a['reasons'] and type(a['comparison_year']) is int and 1000<=a['comparison_year']<=9999 and a['comparison_unit'] is not None and r.get('value') is not None,'Positive missing required source fact',key)
                if a['period_kind']=='monthly_source_statistic':check(type(a['comparison_month']) is int and 1<=a['comparison_month']<=12,'Positive month unknown',key)
                if card.get('supported_comparison_scope',{}).get('within_same_national_published_panel'):check(r.get('geography')=='全國' and r.get('geographic_scope')=='national_total','National-only source card applied outside national panel',key)
        # Independently reconstruct original row/column grid, not card hashes.
        grids={}
        for key,rows in grid_rows.items():
            shape={'row_labels':sorted({r['source_row_label_raw'] for r in rows}),'column_paths':sorted({stable(r['source_column_path']) for r in rows}),'metric_units':sorted({(r['metric_raw'],r.get('unit_raw')) for r in rows})}
            grids[key]=hashlib.sha256(stable(shape).encode()).hexdigest()
        multiple=0;group_pair_checks=0
        for gid,items in positive_groups.items():
            check(len({a['source_sha256'] for a in items})==1,'Positive panel crosses original document SHA',gid)
            check(len({stable(a['facets']) for a in items})==1,'Group facets differ',gid)
            local_grids={grids[(raw[a['record_key']]['source_id'],raw[a['record_key']]['source_sheet'])] for a in items if a['layer']=='local_statistical_cells'}
            check(len(local_grids)<=1,'Positive group crosses original Hualien grid',gid)
            period_rows={}
            for a in items:period_rows.setdefault((a['comparison_year'],a['comparison_month']),a)
            values=[a for key,a in sorted(period_rows.items(),key=lambda x:(x[0][0],x[0][1] or 0))]
            if len(values)>1:multiple+=1
            for aa,bb in zip(values,values[1:]):check(engine.compare(aa,bb)['status']=='published_panel_limited','Eligible group pair unexpectedly blocked',gid);group_pair_checks+=1
        check(multiple==summary['groups_with_multiple_eligible_periods'],'Independent eligible-period group count differs')
        check(len(ups)==summary['literal_unit_suffix_upgrades']==14584,'Literal-unit suffix upgrade count changed')
        # Full DGBAS published-edition segment checks; no fuzzy source selectors.
        dgbas=collections.defaultdict(list)
        for key,r in raw.items():
            if key.startswith('canonical:') and r.get('source_id','').startswith('dgbas-social-indicators-'):dgbas[(r['source_id'],r['indicator'])].append(amap[key])
        cross_tests=0;unresolved_2011=0
        for (source,indicator),items in dgbas.items():
            if source.endswith('2011') and indicator=='圖書借閱人數':
                for a in items:check(a['comparison_status']=='unresolved','2011 opposing reader definitions were certified',a['record_key']);unresolved_2011+=1
            if indicator not in ('家數','每10萬人圖書館數','圖書借閱人數'):continue
            if indicator=='圖書借閱人數' and source.endswith('2011'):continue
            def segment(a):
                y=a['comparison_year'];return (0 if y<=1999 else 1) if indicator=='圖書借閱人數' else (0 if y<1998 else 1 if y<=1999 else 2)
            for i,a in enumerate(items):
                for b in items[i+1:]:
                    if a['comparison_year'] is not None and b['comparison_year'] is not None and segment(a)!=segment(b):check(engine.compare(a,b)['status']!='published_panel_limited','DGBAS source-segment boundary leaked',{'left':a['record_key'],'right':b['record_key']});cross_tests+=1
        report['full_quantitative_audit']={'records':len(amap),'layer_fingerprints':fingerprints,'status_counts':dict(collections.Counter(a['comparison_status'] for a in annotations)),'source_definition_cards':len(cards),'multiple_supporting_evidence_records':sum(bool(a['supporting_evidence_ids']) for a in annotations),'unit_suffix_original_field_checks':len(ups),'raw_original_JSON_documents_checked_for_suffixes':len(source_cache),'eligible_groups_with_multiple_periods':multiple,'eligible_adjacent_period_pairs_checked':group_pair_checks,'DGBAS_cross_segment_pairs_checked':cross_tests,'DGBAS_2011_reader_records_required_unresolved':unresolved_2011,'materialized_engine_hash_matches':summary['inputs']['scripts/phase2_engine.py']==engine_start,'annotation_file_sha256':sha(root/'derived/phase2/annotations.jsonl.gz')}
    check(sha(root/'scripts/phase2_engine.py')==engine_start,'Engine changed during this review; rerun affected methods')
    report['status']='PASS' if not report['blockers'] else 'BLOCKED';return report

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,default=ROOT);p.add_argument('--cases-only',action='store_true');p.add_argument('--case-id',action='append');p.add_argument('--skip-cli',action='store_true');p.add_argument('--report',type=Path);a=p.parse_args();root=a.root.resolve();r=review(root,a.cases_only,set(a.case_id) if a.case_id else None,a.skip_cli)
    if a.report:
        path=a.report if a.report.is_absolute() else root/a.report;body=json.dumps(r,ensure_ascii=False,indent=2)+'\n';path.parent.mkdir(parents=True,exist_ok=True);path.write_text(body)
        md=path.with_suffix('.md');md.write_text('# 第二階段獨立引擎驗收\n\n結果：'+r['status']+'。凍結source cases未改；source-adjudication另列。\n\n'+f"本輪{r['assertions']:,}項檢查，{len(r['cases'])}個真實案例與{len(r['synthetic'])}項合成／防禦測試。\n\n"+'非join操作不以compare結果冒充加總／補值／去重人數防線。原件影像／全文與私有路徑未寫入facts報告。\n\n'+json.dumps({'blockers':r['blockers'],'source_adjudications':r['source_adjudications'],'full_quantitative_audit':r.get('full_quantitative_audit'),'cli_operation_guard':r['cli_operation_guard']},ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'status':r['status'],'assertions':r['assertions'],'cases':len(r['cases']),'synthetic':len(r['synthetic']),'blockers':r['blockers'],'full_quantitative_audit':r.get('full_quantitative_audit'),'engine_sha256':r['engine_sha256']},ensure_ascii=False))
    if r['blockers']:raise SystemExit(1)
if __name__=='__main__':main()
