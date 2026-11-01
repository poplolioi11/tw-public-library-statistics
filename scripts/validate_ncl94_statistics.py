#!/usr/bin/env python3
"""Bounded literal/role verification of NCL94 public-library statistical facts.

The expectations were read from the original table images by AI reviewers;
they are not a human reference, accuracy benchmark, or cross-year certification.
"""
import argparse, collections, gzip, hashlib, json
from pathlib import Path

SHA = '2db33efbce20154623b6ba7398e2cfa40af8116578264889d380ab41520c44cf'
SOURCE = 'raw/ncl94-statistics/yearbook-94-statistics.pdf'
COUNTS = [3,53,40,413,3,124,636]
PUBLIC = [23071122,71588,10329679,30498418]
PRIVATE = [743056,8265,188701,659228]
UNITS = ['冊','席位','人次','冊']


def check_rows(rows):
    if len(rows)!=24 or len({r['observation_id'] for r in rows})!=24:
        raise ValueError('Incomplete or duplicate NCL94 quantity set')
    seen=set();physical=set();roles=collections.Counter()
    for row in rows:
        context=json.loads(row['source_time_reference'])['physical_source_context']
        table=row['source_table'];r=int(row['source_row']);c=int(row['source_column'])
        role=context['quantity_role'];key=(table,r,c,role)
        if key in seen:raise ValueError('Duplicate original quantity')
        seen.add(key);roles[role]+=1;physical.add(context['physical_cell_id'])
        if table=='145' and 1<=r<=7 and c==1 and role=='primary':
            value=COUNTS[r-1];unit=None;page=5;printed='440'
        elif table=='146' and r in (2,3) and 1<=c<=4:
            if role=='primary':value=(PUBLIC if r==2 else PRIVATE)[c-1];unit=UNITS[c-1]
            elif role=='responding_libraries':value=509 if r==2 else 58;unit='館'
            else:raise ValueError('Unexpected table146 quantity role')
            page=6;printed='441'
            answering=context['parenthesized_responding_libraries']
            if answering['value']!=(509 if r==2 else 58) or answering['is_total_library_count'] is not False:
                raise ValueError('Response counts must not become total library counts')
            if role=='responding_libraries' and row['aggregation_role']!='responding_libraries_not_total_libraries':
                raise ValueError('Incorrect response population role')
        elif table=='147' and r==1 and c==2 and role=='primary':
            value=37;unit=None;page=11;printed='446'
            if row['geographic_scope']!='cooperation_membership_public_category':
                raise ValueError('Membership must not become a national library total')
        else:raise ValueError('Unreviewed original position')
        if type(row['value']) is not int or row['value']!=value or row['value_status']!='reported':
            raise ValueError('Reported value differs from image-reviewed literal')
        if str(row['raw_value']).replace(',','')!=str(value):
            raise ValueError('Original numeric token differs')
        if row['unit']!=unit or (unit is None and row['unit_raw'] is not None):
            raise ValueError('Unprinted units must remain null')
        if row['data_year']!=2004 or row['period_start'] is not None or row['period_end'] is not None:
            raise ValueError('Only printed reference year is verified; exact dates unknown')
        if row['source_sha256']!=SHA or row['source_pdf_page']!=page or row['source_printed_page']!=printed:
            raise ValueError('Original lineage/page differs')
        if '#page='+str(page) not in row['source_url'] or not row['source_locator']:
            raise ValueError('Missing official page locator')
        if context['human_review_completed'] is not False or context['human_double_collation_completed'] is not False:
            raise ValueError('AI review cannot be labelled human completion')
    if len(physical)!=16 or roles!={'primary':16,'responding_libraries':8}:
        raise ValueError('Physical-cell/quantity distinction changed')
    return {'formal_observations':24,'physical_cells':16,'quantity_roles':dict(roles),'unit_null':8}


def validate(root, require_originals=False):
    root=Path(root);path=root/'derived/ncl94_statistics_observations.jsonl'
    if not path.exists():path=path.with_suffix(path.suffix+'.gz')
    body=gzip.decompress(path.read_bytes()) if path.suffix=='.gz' else path.read_bytes()
    rows=[json.loads(line) for line in body.splitlines()]
    result=check_rows(rows)
    source=root/SOURCE;original_checked=False
    if source.is_file():
        if hashlib.sha256(source.read_bytes()).hexdigest()!=SHA:
            raise ValueError('Pinned original has changed')
        original_checked=True
    elif require_originals:raise FileNotFoundError('Restore exact official NCL94 original before source verification')
    result.update(status='pass',original_sha_checked=original_checked,
                  numeric_reference='complete bounded AI image reading, not a human gold standard',
                  human_review_completed=False, human_double_collation_completed=False,
                  cross_source_comparability_certified=False)
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--require-originals',action='store_true');a=p.parse_args()
    print(json.dumps(validate(a.root,a.require_originals),ensure_ascii=False))
