#!/usr/bin/env python3
"""Build a source-presence matrix without certifying ambiguous county labels."""
from __future__ import annotations
import csv,json
from collections import Counter,defaultdict
from pathlib import Path
try:
    from build_documentation import (HISTORICAL,YEARBOOK,READING,display_numbers,flags,historical_warning,load_context,read_json,table_groups,uncertain_label,unit_conflict,write_json)
except ModuleNotFoundError:
    from scripts.build_documentation import (HISTORICAL,YEARBOOK,READING,display_numbers,flags,historical_warning,load_context,read_json,table_groups,uncertain_label,unit_conflict,write_json)
R=Path(__file__).resolve().parents[1]
COUNTIES=['基隆市','臺北市','新北市','桃園市','新竹縣','新竹市','苗栗縣','臺中市','彰化縣','南投縣','雲林縣','嘉義縣','嘉義市','臺南市','高雄市','屏東縣','臺東縣','花蓮縣','宜蘭縣','澎湖縣','金門縣','連江縣']
# Preserve a fixed current-name index, not a recoding of historical geography.
COUNTIES=list(dict.fromkeys(COUNTIES))

def coverage_entries(rows):
    index=defaultdict(list)
    for row in rows:
        # No prefix matching, inferred repairs, or historical-name conversion.
        if row.get('geography') in COUNTIES:index[(row['data_year'],row['geography'])].append(row)
    data_years=[r['data_year'] for r in rows if isinstance(r.get('data_year'),int)]
    years=range(min(data_years),max(data_years)+1) if data_years else []
    entries=[]
    for year in years:
        for geo in COUNTIES:
            subset=index.get((year,geo),[]);ambiguous=[r for r in subset if uncertain_label(r)];confirmed=[r for r in subset if not uncertain_label(r)]
            has_explicit=any(r['source_id']=='ogdl-api-2023' for r in confirmed)
            if ambiguous:
                status='complete_for_6425_explicit_resource_with_other_uncertain_labels' if has_explicit else 'partial_sources_with_uncertain_county_labels' if confirmed else 'uncertain_county_labels_only_not_confirmed_coverage'
            elif has_explicit:status='complete_for_6425_explicit_2023_resource'
            elif confirmed:status='source_null_cells_only_see_value_status' if all(r['value'] is None for r in confirmed) else 'partial_sources_obtained'
            else:status='not_obtained_or_not_yet_checked'
            entries.append({'data_year':year,'requested_county_current_name':geo,'status':status,'records':len(subset),'confirmed_label_records':len(confirmed),'confirmed_label_value_records':sum(r['value'] is not None for r in confirmed),'uncertain_label_records':len(ambiguous),'unit_conflict_records':sum(unit_conflict(r) for r in subset),'sources':'|'.join(sorted({r['source_id'] for r in subset})),'uncertain_label_sources':'|'.join(sorted({r['source_id'] for r in ambiguous})),'boundary_warning':'依現行名稱僅做原標籤缺口索引，未轉換歷史臺北縣／桃園縣或合併前縣市；標籤待釐清或原印重複不算已確認縣市值，不擅補連江。','label_warning':'confirmed_label只表示來源地理標籤可明確索引，不代表統計填報正確或該縣市所有指標完整。' if not ambiguous else '此列含原標籤不確定／原印重複；原值保留，uncertain_label_records不能當成已確認縣市覆蓋。','absence_meaning':'not_obtained_or_not_yet_checked不是無資料；不證明政府沒有公開。'})
    return entries

def metadata_paths(context):
    paths=['research/ncl-historical-validation.json']
    paths += [p for cohort in context['cohorts'] for p in cohort['metadata_paths']]
    return list(dict.fromkeys(paths))

def main():
    context=load_context(R);rows=context['rows'];summary=context['summary'];entries=coverage_entries(rows)
    with (R/'data/combined/coverage_matrix.csv').open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(entries[0]));writer.writeheader();writer.writerows(entries)
    local=read_json(R/'derived/local_historical_quality.json',{});component=read_json(R/'data/component_quality.json',{})
    historical=context['historical'];ambiguous=[r for r in historical if uncertain_label(r)];conflicting=[r for r in historical if unit_conflict(r)]
    write_json(R/'data/combined/quality_flags.json',{'source_internal_issues':component.get('issues',[]),'local_arithmetic_checks':local.get('hsinchu_arithmetic_checks',[]),'local_arithmetic_issues':local.get('hsinchu_arithmetic_errors',[]),'historical_table_checks':metadata_paths(context),'reviewed_cohort_registry':'data/reviewed_historical_cohorts.json','historical_batch_inventory':'docs/historical-batches.json','flagged_historical_cells':[{k:r.get(k) for k in ['observation_id','source_id','source_locator','quality_flags','geographic_scope','unit','unit_status']} for r in historical if flags(r)],'uncertain_label_records':len(ambiguous),'uncertain_label_source_counts':dict(sorted(Counter(r['source_id'] for r in ambiguous).items())),'uncertain_labels_not_indexable_by_current_name':[{k:r.get(k) for k in ['observation_id','source_id','data_year','geography','geographic_scope','source_locator']} for r in ambiguous if r['geography'] not in COUNTIES],'unit_conflict_records':len(conflicting),'source_faithfulness_is_not_statistical_certification':True})
    families=Counter(r['source_family'] for r in rows);nulls=context['nulls'];byyear=Counter(r['data_year'] for r in historical)
    ncl=[r for r in historical if r['source_family']==YEARBOOK];reading=[r for r in historical if r['source_family']==READING]
    # Edition numbers come from explicit record/path evidence via the helper.
    try:from build_documentation import edition,family_scope
    except ModuleNotFoundError:from scripts.build_documentation import edition,family_scope
    editions=sorted({edition(r) for r in ncl if edition(r) is not None});unknown=f'{max(editions)+1}卷以後及{min(editions)-1}卷以前' if editions else '其餘目錄卷'
    lines=['# 涵蓋範圍與完整度','',f"資料版本：v{summary['version']}；資料建置日{str(summary.get('built_at','未列明'))[:10]}。**下列所列來源已整批整理；全臺各縣市所有歷年尚未齊全。** 全部{len(rows):,}格，包含{nulls.get('not_available_in_source',0):,}個來源明示缺值、{nulls.get('source_blank',0):,}個原印留白及不同出版版本。紀錄數不是圖書館間數。",'', '|來源族群|已取得的範圍|正式觀測格|','|---|---|---:|']
    order=['國資圖公開全國圖表','國資圖2023開放資料（含縣市）',YEARBOOK,READING,'主計總處歷史全國統計','主計總處縣市公共館數','地方政府開放歷史表']
    for name in order+sorted(set(families)-set(order)):
        subset=[r for r in rows if r['source_family']==name]
        if subset:lines.append(f'|{name}|{family_scope(name,subset)}|{len(subset):,}|')
    lines+=['',f"已覆核的{len(context['cohorts'])}個可執行歷史批次、原CSV格數、正式觀測數、資料年及版次見[歷史批次清單](docs/historical-batches.md)與[JSON](docs/historical-batches.json)。完整性只及列明的表格、公共館子群或原文數字，不是整冊所有表。跨頁續表按同一表完整計數。",'',f"年鑑與閱讀報告各資料年格數（包含不同出版版本和重疊表）：{dict(sorted(byyear.items()))}。",'',historical_warning(context),'','`coverage_matrix.csv`是資料年×現行22縣市的原標籤缺口索引。歷史臺北縣、桃園縣等未硬轉現行界線，因此不能以矩陣作同界線比較。矩陣分列`confirmed_label_records`與`uncertain_label_records`；前者只表示地理標籤可索引，並非所有指標完整或填報已認證。只有明確2023資源的指定範圍另標完整，不擴充至整個縣市歷年。','', '## 尚未完成','', '- 尚未取得全臺各縣市所有年度、所有指標的同口徑資料。全國歷年表、比率敘述和縣市單一館數不能冒充完整面板。',f'- 國圖{unknown}等已見目錄版本仍待逐表查核。已處理卷的其他未列表／段也不自行算入完成。','- 2012本輪已查公共館章、統計章、評鑑章、國資圖舊年度連結與閱讀報告；原文比率不反算縣市原量，評鑑達標／未達標或得獎館數不納作營運量。舊附件失敗已找到改版官網新網址；仍未取得的縣市核心原量不等於官方沒有公開。','- 臺中、新竹以外地方來源未逐機關全盤核查；1991以前、實際填報率及歷史定義適用性仍待查。','- 各批影像、逐格、獨立比對與算術查核範圍列在metadata，不能統稱所有資料均有人類逐格雙校或官方認證。','', '## 原值、單位與口徑','', '0、原印留白與明示缺值分開保存；留白不推定不適用，0不逕認為真零。單位由上下文推得時保留`unit_basis`與推論狀態。標題與正文衝突時保留`unit=null`及`unit_status`，候選解讀不能當定論。2012閱讀表成長率是2011至2012比較；資料年欄位單獨不足以表達比較期間。','', '館數表可能另列國立館、閱覽室、未開放館與第二館；不補原刊不存在的欄位、不將省政府館擅併入南投縣。2014等原表內部差異均保留，2015疑似錯列及兩個金門原標籤不重新指定為連江。','',f"歷史來源有{len(ambiguous):,}筆地理標籤待釐清、{len(conflicting):,}筆單位衝突未決。原刊算術差異、地方合計差異及相關逐格旗標見`data/combined/quality_flags.json`、各批metadata與`research/source-verification.md`；可追溯性不替官方填報作零錯誤保證。",'', '主計縣市館數沿用官方改制後縣市別，母體含國家圖書館，與國資圖公共館數不同；年度參照不逕推為年底。地方月值不當全年值；重複來源版本、總計與分項均不可整表相加。','', '特定工程改造、個案評價與照片不納入；一般公共館營運統計中的面積、經費依原表保存。署名全文、PDF與原件重製全圖不隨公開包散布。','']
    (R/'COVERAGE.md').write_text('\n'.join(lines))
    print('coverage entries',len(entries),'uncertain labels',len(ambiguous),'unit conflicts',len(conflicting))
if __name__=='__main__':main()
