#!/usr/bin/env python3
"""Verify scoped unit corrections and optionally compare a prior formal JSONL.

Pass v0.9.0 observations.jsonl(.gz) to --previous for an all-field comparison.
No downloading, data rewriting, inference or human review is performed.
"""
import argparse,collections,gzip,hashlib,json
from pathlib import Path
import metadata_corrections as metadata
import record_io

PUBLICATION={'snapshot_distribution','public_evidence_path','public_evidence_sha256','public_projection_policy'}
def previous_rows(path):
    with (gzip.open(path,'rt',encoding='utf-8') if path.suffix=='.gz' else path.open(encoding='utf-8')) as f:
        for line in f:
            if line.strip():yield json.loads(line)

def audit(root, previous=None):
    rows=list(record_io.rows(root));before_unit=[r.get('unit') for r in rows]
    ledger=[json.loads(x) for x in (root/'derived/metadata-corrections-20261029.jsonl').read_text().splitlines()]
    metadata.validated_overlays(rows,ledger)
    if [r.get('unit') for r in rows]!=before_unit:raise ValueError('Audit attempted a data correction')
    rules=metadata.rules();target_ids=set()
    for rule in rules:
        selected=[r for r in rows if r['source_id']==rule['source_id'] and r['source_sha256']==rule['source_sha256'] and r['source_field']==rule['source_field'] and (not rule.get('observation_id') or r['observation_id']==rule['observation_id'])]
        target_ids.update(r['observation_id'] for r in selected)
    result={'status':'PASS','records':len(rows),'reviewed_rules':len(rules),'reviewed_unit_records':len(target_ids),'unit_unresolved':sum(not r.get('unit') for r in rows),'reference_year_unresolved':sum(r['data_year'] is None for r in rows),'human_double_collation_completed':False,'numeric_values_source_correctness_certified':False}
    if previous:
        old={r['observation_id']:r for r in previous_rows(previous)}
        if set(old)!={r['observation_id'] for r in rows}:raise ValueError('Observation membership changed')
        changes=collections.Counter();changed_ids=set()
        for r in rows:
            prior=old[r['observation_id']]
            diff={k for k in set(r)|set(prior) if k not in PUBLICATION and r.get(k)!=prior.get(k)}
            if diff-set(metadata.CHANGED_FIELDS):raise ValueError('Non-unit-metadata field changed: '+r['observation_id']+'/'+','.join(sorted(diff)))
            if diff:
                changed_ids.add(r['observation_id']);changes.update(diff)
                if prior.get('unit') not in (None,''):raise ValueError('An established original unit was overwritten')
        if changed_ids!=target_ids:raise ValueError('Changed observations differ from the exact reviewed scope')
        result.update(previous_observations_compared=len(old),unit_metadata_records_changed=len(changed_ids),unchanged_records=len(rows)-len(changed_ids),changed_fields=dict(changes),all_numerical_raw_identity_period_and_source_fields_unchanged=True)
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--previous',type=Path);p.add_argument('--output',type=Path);a=p.parse_args();result=audit(a.root.resolve(),a.previous)
    text=json.dumps(result,ensure_ascii=False,indent=2)+'\n'
    if a.output:a.output.write_text(text)
    print(text)
