"""Reconcile current tasks against an already ingested, explicitly bounded batch.

Historical discovery/probe files remain immutable. Counts verify the complete
selected batch is present, not that a human has read its cells.
"""
from collections import Counter

EVIDENCE = ['raw/discovered-20261028/extraction-metadata.json',
            'docs/historical-batches.json', 'research/discovered-20261028-ingestion-review.json']
LOCAL_FAMILY = '地方官方出版統計事實'

def reconcile(backlog, rows, batch):
    expected = batch.get('source_counts', {})
    selected = [r for r in rows if r.get('component_source_id') in expected]
    actual = Counter(r.get('component_source_id') for r in selected)
    if not expected or dict(actual) != expected:
        raise ValueError('Cannot mark backlog complete: selected batch source counts differ')
    for sid, count in batch.get('table_counts', {}).items():
        if sum(r.get('source_id') == sid for r in selected) != count:
            raise ValueError('Cannot mark backlog complete: selected table differs: ' + sid)
    local = [r for r in selected if r.get('source_family') == LOCAL_FAMILY]
    local_sources = sorted({r['component_source_id'] for r in local})
    dgbas = [r for r in selected if r.get('component_source_id') == 'dgbas-yearbook-113']
    moe = [r for r in selected if r.get('component_source_id') == 'moe-16years-T403']
    early = {sid: n for sid,n in actual.items() if sid.startswith('ncl-ed')}
    scope = {'source_documents': len(local_sources), 'formal_observations': len(local),
             'source_ids': local_sources,
             'completion_statement': '只及所列地方原刊指定表與續頁；不是整冊、完整歷年或全臺同口徑面板。'}
    dgbas_scope = {'source_id': 'dgbas-yearbook-113', 'source_table': '4-22',
                   'formal_observations': len(dgbas),
                   'data_years': sorted({r['data_year'] for r in dgbas if r.get('data_year') is not None}),
                   'period_unresolved_records': sum(r.get('data_year') is None for r in dgbas),
                   'completion_statement': '全表已入庫；全國年度2010–2024，機關／縣市列未逐列明年者保留null，不一律當2024。'}
    for f in backlog['families']:
        fid = f['family_id']
        if fid == 'ncl_yearbook_public_library_chapters':
            # Core metadata can exclude tables that are complete in another layer.
            # Only remove an exact completed table set, never every table in a cohort.
            completed = f.get('completed_other_layer', [])
            f['known_not_ingested'] = [item for item in f.get('known_not_ingested', [])
                if not (isinstance(item,dict) and item.get('tables') is not None and any(
                    done.get('status') == 'completed_in_separate_programme_layer'
                    and item.get('cohort') == done.get('cohort')
                    and item['tables'] == done.get('tables') for done in completed))]
            continue
        if fid == 'dgbas_social_indicator_history':
            # Keep the historical 220-cell family separate from the newer family.
            f['related_ingested_publication'] = {**dgbas_scope, 'source_family': '主計總處後續全國出版統計'}
            f['known_not_ingested'] = [x for x in f['known_not_ingested'] if '113年統計年鑑表4-22' not in str(x)]
            f['unknown_scope'] = ['1991以前及113年表4-22以外的其他年報版本仍未系統盤點。',
                                  '各版同年修訂、國立館範圍與歷年可比性未完全釐清。']
        elif fid == 'local_publication_statistical_facts':
            f.update(status='completed_bounded_scope', completed_scope=scope,
                     historical_probe_scope={'research_probe_cells':396,
                         'evidence':'research/source-probes/20261028-original-cells.json',
                         'role':'v0.8 discovery snapshot; not additional formal observations'},
                     known_not_ingested=['各原刊未列入指定批次的其他表及年份仍待查。',
                         '臺北2012年刊權利衝突維持暫停；已入庫的2012年12月月表65格是另件來源。'])
        elif fid == 'moe_historical_public_library_versions':
            f.update(status='completed_bounded_scope',
                     completed_scope={'formal_observations':len(moe),'source_id':'moe-16years-T403',
                         'source_table':'社3','data_years':sorted({r['data_year'] for r in moe if r.get('data_year') is not None}),
                         'completion_statement':'所列1994–2009社3完整48格；含國家圖書館，重疊年份版本分列，不當新增16缺年。'},
                     known_not_ingested=['其他未列歷史表及不同出版版本未由本批完成。'])
        else: continue
        f['evidence'] = list(dict.fromkeys(f.get('evidence',[]) + EVIDENCE))
    for task in backlog.get('ordered_batches', backlog.get('backlog', [])):
        tid = task['task_id']
        if tid == 'B03':
            task.update(title='已列年鑑核心表入庫後，續查未列卷與其他原表',
                        status='partially_completed_known_tables',
                        scope='91–94卷指定表及續頁已整批入庫；93卷表16／17／19不再是待擷取項目。91–114卷只及列明範圍，其他未列表、卷次及2012核心原量仍待查。',
                        completed_scope={'source_counts':early,'formal_observations':sum(early.values())},
                        unknowns=['未列入指定批次的其他表、其他卷與2012全22縣市核心原量仍待查。',
                                  '已入庫掃描格仍未完成人工核讀與雙校，不把AI原圖核讀改標為人工完成。'])
        elif tid == 'B07':
            task.update(status='partially_completed_known_tables', completed_scope=dgbas_scope,
                        scope=f'113年統計年鑑表4-22完整{len(dgbas)}格已入庫；未逐列明年的機關／縣市列保留null。1991以前及其他版本仍待查。',
                        completion='113年表4-22指定全表已完成，並非全部歷史年報完成。')
        elif tid == 'B09':
            task.update(status='completed_bounded_scope', title='已取得地方官方原量指定表正式入庫',
                        batch_size='所列原件指定表已完成；後續新來源仍逐份完整處理',
                        completed_scope=scope,
                        scope=f'新北、臺南、桃園、彰化、高雄及臺北2012年12月共{len(local_sources)}份原件指定表／續頁，{len(local):,}格已正式入庫。2012完整22縣市核心原量表仍缺，不跨來源拼接。',
                        completion='v0.9.0完成指定表入庫，v0.9.1沿用；396格probe保留歷史身分，不額外計數。',
                        acceptance=['以完整指定表、續頁、原值與缺值驗收；逐格保留官方URL、原件SHA及頁表列欄。',
                                    '母體、單位、期間、斷點及版本限制隨值保留；未知不推算，人工核讀與雙校未完成。',
                                    '臺北年刊權利衝突仍隔離，下載成功不等於再公開授權。'])
            task['source_urls'] = list(dict.fromkeys(task.get('source_urls',[]) + [r['source_url'].split('#',1)[0] for r in local if r.get('component_source_id')=='tpml-2012-12']))
        else: continue
        task['evidence'] = list(dict.fromkeys(task.get('evidence',[]) + EVIDENCE))
    backlog['scope_claims'] = [
        '2026-10-28的16份原件發現登錄與396格probe是歷史快照；其中12份原件完整指定表20,358格已於v0.9.0正式入庫，v0.9.1沿用；不把probe重複計數。'
        if '16份' in x and '396' in x else x for x in backlog.get('scope_claims',[])]
    backlog.setdefault('status_reconciliation', {'reconciled_at':'2026-10-30',
        'dataset_version':'0.9.1','baseline_commit':'4c4e656d94598627c364a49beb967ec437dff037',
        'basis':'existing canonical and complete selected-table metadata; not a fresh agency website search',
        'historical_discovery_snapshot_modified':False,'statistical_values_modified':False,
        'human_reading_completed':False,'human_double_collation_completed':False,
        'human_accuracy_estimate':None})
    return backlog

def markdown_rows(backlog):
    lines=['## 已入庫與仍待辦的界線','',
           '|待辦|目前狀態|已完成範圍與後續|','|---|---|---|']
    for t in backlog.get('ordered_batches',backlog.get('backlog',[])):
        if t['task_id'] in ('B03','B07','B09'):
            label='限定範圍已完成' if t['status']=='completed_bounded_scope' else '部分表已完成，仍有待辦'
            lines.append(f"|{t['task_id']}|{label}|{t['scope']}|")
    lines += ['', '文件狀態對帳日2026-10-30；資料仍為v0.9.1，原官方查核日期與歷史probe保留。人工抽樣核讀與雙校尚未完成；沒有預填讀值或人工錯誤率。',
              '正式範圍見[入庫metadata](../raw/discovered-20261028/extraction-metadata.json)與[逐表清單](historical-batches.json)。年度467筆及單位1,690筆未解已覆核後保留，沒有新證據不推算；見[修訂說明](metadata-review-20261029.md)。','']
    return lines
