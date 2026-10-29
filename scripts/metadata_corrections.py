"""Source-version-bound metadata corrections, never numerical imputation.

Rules require an exact original hash, field and complete observation-ID set.
They cannot silently cover a changed source version or new observations.
"""
import hashlib,json
from pathlib import Path

REGISTER_SHA256 = '1b100b28f24940a2b9bb5fa0a54a74722f8aa456163459a18492e71f71c2e9f7'
STATUS = 'explicit_original_field_name_unit'
CHANGED_FIELDS = ('unit','unit_status','unit_basis','source_unit_context_locator')

def identity_hash(ids):
    return hashlib.sha256(('\n'.join(sorted(ids))+'\n').encode()).hexdigest()

def rules():
    body=Path(__file__).with_name('reviewed_metadata_corrections.json').read_bytes()
    if hashlib.sha256(body).hexdigest()!=REGISTER_SHA256:
        raise ValueError('Metadata review register changed; original-source review required')
    data=json.loads(body)
    if data['review_status']!='pinned_original_fields_replayed_not_human_double_collation':
        raise ValueError('Unknown metadata review status')
    return data['rules']

def apply(rows, register=None):
    register=rules() if register is None else register
    index={};source_versions={}
    for row in rows:
        key=(row['source_id'],row['source_sha256'],row.get('source_field'))
        index.setdefault(key,[]).append(row)
        source_versions.setdefault(row['source_id'],set()).add(row['source_sha256'])
    changes=[];seen=set()
    for rule in register:
        key=(rule['source_id'],rule['source_sha256'],rule['source_field'])
        if key in seen:raise ValueError('Duplicate metadata rule')
        seen.add(key)
        selected=index.get(key,[])
        if rule.get('observation_id'):
            selected=[r for r in selected if r['observation_id']==rule['observation_id']]
        if not selected and rule['source_id'] in source_versions:
            raise ValueError('Reviewed original source version/field changed; retain previous release')
        if not selected:continue
        ids=[r['observation_id'] for r in selected]
        if len(ids)!=len(set(ids)) or len(ids)!=rule['canonical_null_unit_observations'] or identity_hash(ids)!=rule['complete_observation_id_set_sha256']:
            raise ValueError('Metadata rule does not cover the exact reviewed observation set')
        field=rule['source_field'];unit=rule['unit']
        kind=rule.get('kind','literal_field_suffix')
        if kind=='literal_field_suffix':
            if not ((field.endswith('冊數') and unit=='冊') or (field.endswith('人次') and unit=='人次')):
                raise ValueError('Unit is not explicitly supported by the pinned original field suffix')
            status=STATUS
        elif kind=='same_document_explicit_aggregate_unit':
            if not rule.get('observation_id') or unit!='種' or not rule.get('supporting_original_text','').endswith('種') or not rule.get('source_unit_context_locator'):
                raise ValueError('Same-document unit requires a single scoped original aggregate and direct prose evidence')
            status='same_source_body_explicit_matching_aggregate'
        else:raise ValueError('Unknown reviewed metadata correction kind')
        for r in selected:
            if r.get('unit') not in (None,'') and not (r['unit']==unit and r.get('unit_status')==status):
                raise ValueError('Metadata correction cannot overwrite another established unit')
            if kind=='same_document_explicit_aggregate_unit' and any(r.get(k)!=v for k,v in rule['exact_original_binding'].items()):
                raise ValueError('Aggregate no longer matches its exact original scope/value binding')
            old={k:r.get(k) for k in CHANGED_FIELDS}
            new={'unit':unit,'unit_status':status,
                 'unit_basis':'Exact original JSON field '+field+'; source-version and complete observation set reviewed; see docs/metadata-review-20261029.json',
                 'source_unit_context_locator':r['source_locator']+'; literal original JSON field-name suffix '+('冊數' if unit=='冊' else '人次')}
            if kind=='same_document_explicit_aggregate_unit':
                new.update(unit_basis=rule['unit_basis'],source_unit_context_locator=rule['source_unit_context_locator'])
            if old==new:continue
            r.update(new)
            changes.append({'observation_id':r['observation_id'],'source_id':r['source_id'],
                'source_sha256':r['source_sha256'],'source_url':r['source_url'],
                'source_locator':r['source_locator'],'original_field_name':field,'old':old,'new':new,
                'raw_value_value_status_unit_raw_identity_and_period_unchanged':True})
    return changes

def validated_overlays(rows, changes, register=None):
    """Validate an exact unit-only version ledger before reversing old metadata.

    This permits historic checks to retain their original frozen hashes without
    exempting unrelated records, numerical facts, periods or source identities.
    """
    register=rules() if register is None else register
    if apply(rows,register):raise ValueError('Current metadata differs from reviewed rules')
    expected=set()
    for rule in register:
        expected.update(r['observation_id'] for r in rows if r['source_id']==rule['source_id'] and r['source_sha256']==rule['source_sha256'] and r.get('source_field')==rule['source_field'] and (not rule.get('observation_id') or r['observation_id']==rule['observation_id']))
    result={c['observation_id']:c for c in changes}
    if len(result)!=len(changes) or set(result)!=expected or len(expected)!=sum(r['canonical_null_unit_observations'] for r in register):
        raise ValueError('Metadata version ledger differs from the complete reviewed scope')
    current={r['observation_id']:r for r in rows}
    for oid,c in result.items():
        r=current[oid]
        if set(c['old'])!=set(CHANGED_FIELDS) or set(c['new'])!=set(CHANGED_FIELDS):raise ValueError('Version ledger contains non-unit metadata fields')
        if c['old']['unit'] not in (None,''):raise ValueError('Version ledger overwrites an established unit')
        if any(c.get(k)!=r.get(k) for k in ('source_id','source_sha256','source_url','source_locator')) or any(c['new'][k]!=r.get(k) for k in CHANGED_FIELDS):
            raise ValueError('Version ledger does not match the exact current original-source record')
    return result
