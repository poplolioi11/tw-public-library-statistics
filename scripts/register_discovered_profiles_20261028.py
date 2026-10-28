#!/usr/bin/env python3
"""Bind three explicitly reviewed questions to the newly ingested originals.

Only the twelve-source batch is added. Existing reviewed versions and profile
priorities are preserved. A later source/evidence change needs a new review;
this script is deliberately not a scheduled update hook.
"""
import argparse, hashlib, json
from pathlib import Path
import record_io
import phase2_engine as p2

ROOT=Path(__file__).resolve().parents[1]


def run(root):
    path=root/'docs/phase3-profiles.json';policy=json.loads(path.read_text())
    rows=[r for r in record_io.rows(root) if str(r['source_id']).startswith('discovered-')]
    cards=[json.loads(x) for x in (root/'derived/phase2/evidence_cards.jsonl').read_text().splitlines()]
    cards=[c for c in cards if c['source_id'] in {r['source_id'] for r in rows}]
    if {c['source_id'] for c in cards}!={r['source_id'] for r in rows}:raise ValueError('New source evidence is not complete')
    annotation=[json.loads(x) for x in __import__('gzip').open(root/'derived/phase2/annotations.jsonl.gz','rt')]
    annotation=[a for a in annotation if str(a['source_id']).startswith('discovered-')]
    sources={r['source_id']:r for r in rows}
    existing={(r['layer'],r['source_id'],r['source_sha256']):r for r in policy['reviewed_sources']}
    for c in cards:
        policy['evidence_bindings'][c['evidence_id']]=hashlib.sha256(p2.stable(c).encode()).hexdigest()
        r=sources[c['source_id']]
        key=('canonical',r['source_id'],r['source_sha256'])
        existing[key]={'layer':'canonical','source_id':r['source_id'],'source_sha256':r['source_sha256'],
                       'source_family':r['source_family'],'evidence_ids':[c['evidence_id']]}
    policy['reviewed_sources']=sorted(existing.values(),key=lambda r:(r['layer'],r['source_id'],r['source_sha256']))
    policy['reviewed_dataset_version']=(root/'VERSION').read_text().strip()
    policy['policy_version']='1.1.0'
    keys=set(policy.get('reviewed_panel_record_keys',[]))
    keys.difference_update('canonical:'+r['observation_id'] for r in rows)
    index=p2.card_index(cards)
    keys.update('canonical:'+r['observation_id'] for r in rows
                if p2.is_reviewed(index['canonical',r['observation_id']])
                and p2.policy_for(r,index['canonical',r['observation_id']])['status']=='published_panel_limited')
    policy['reviewed_panel_record_keys']=sorted(keys)
    definitions=[
        ('discovered-official-original-cells','新增官方原刊：全部原格與未確認期間','original',
         '十二份原件的完整指定表與續頁。包含原刊符號、共用格、每週量、參考均值及期間未確認格；原格數不是館數。'),
        ('discovered-official-annual-tables','新增官方原刊：年度原表','annual',
         '只選已確認年度的原刊事實；每張來源表及版次獨立，新北館藏2010前後分段，不跨來源補線。'),
        ('discovered-official-monthly-tables','新增官方原刊：分館月表','monthly',
         '高雄2012逐館月表與臺北2012年12月原表；年合計與月值分開，館藏參照與借閱流量保留原標示。'),
    ]
    ids={x[0] for x in definitions}
    policy['profiles']=[p for p in policy['profiles'] if p['id'] not in ids]
    for ident,title,period,description in definitions:
        policy['profiles'].append({'id':ident,'title':title,'description':description,
                                   'selection_mode':'fixed_original_rows','default_purpose':'source-facts',
                                   'period_requirement':period,'candidate_filter':{'layer':'canonical','source_ids':sorted(sources)},
                                   'supported_purposes':['source-facts'] if period=='original' else ['source-facts','trend'],
                                   'priority_rule':'All matched original cells retained; exact source/table/entity/period scope, no aggregation, fallback or cross-source splicing.',
                                   'curator_policy_not_official_correction':True})
    path.write_text(json.dumps(policy,ensure_ascii=False,indent=2)+'\n')
    cp=root/'docs/phase3-contract.json';contract=json.loads(cp.read_text());contract['profiles']=[p['id'] for p in policy['profiles']]
    current=json.loads((root/'docs/phase2-summary.json').read_text())
    if contract['baseline'].get('version')!=(root/'VERSION').read_text().strip():
        contract.setdefault('previous_baselines',[]).append(contract['baseline'])
    contract['baseline']={'version':(root/'VERSION').read_text().strip(),'layers':current['layers'],
                          'layer_raw_fingerprints':current['layer_raw_fingerprints']}
    cp.write_text(json.dumps(contract,ensure_ascii=False,indent=2)+'\n')
    return {'registered_profiles':len(policy['profiles']),'new_original_source_tables':len(cards),'new_records':len(rows)}


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=ROOT);a=p.parse_args()
    print(json.dumps(run(a.root.resolve()),ensure_ascii=False))
