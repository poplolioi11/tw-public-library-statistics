"""Exact reviewed original non-scalar literals; never a general numeric fallback."""
import hashlib,json
from functools import lru_cache
from pathlib import Path

REGISTRY_SHA256='4ef873c292c62df8c77d5f63b21348856176c85de6e64a6c43645ae25f47447d'
FIELDS=('observation_id','source_id','component_source_id','source_record_id','source_sha256',
        'source_locator','source_location_kind','raw_value','value','value_status')


@lru_cache(maxsize=1)
def reviewed_literals():
    body=Path(__file__).with_name('reviewed_non_scalar_literals.json').read_bytes()
    if hashlib.sha256(body).hexdigest()!=REGISTRY_SHA256:raise ValueError('Reviewed original-literal registry changed; source review required')
    register=json.loads(body)
    if register['schema_version']!='1.0.0' or register['review_status']!='original_source_cells_reviewed':raise ValueError('Unknown original-literal review')
    rows=register['records'];result={r['observation_id']:r for r in rows}
    if len(rows)!=len(result) or len(rows)!=16:raise ValueError('Complete unique reviewed original-literal set required')
    for row in rows:
        if row['value'] is not None or row['value_status']!='source_marker' or not row.get('reason'):
            raise ValueError('Literal review cannot create a scalar quantity or an unreasoned exception')
    return result


def reviewed_non_scalar_literal(record):
    original=reviewed_literals().get(record.get('observation_id'))
    return bool(original and all(record.get(key)==original[key] for key in FIELDS))
