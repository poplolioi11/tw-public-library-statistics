"""Pure public publication statistics and lossless period partitions; no private inputs."""
import gzip,hashlib,io,json
from collections import Counter

def sha(body):return hashlib.sha256(body).hexdigest()

def gzip_bytes(body):
 buffer=io.BytesIO()
 with gzip.GzipFile(filename='',mode='wb',fileobj=buffer,mtime=0,compresslevel=9) as stream:stream.write(body)
 return buffer.getvalue()

def jb(value):return (json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode('utf-8')

def publication_counts(summary,rows):
 records=len(rows);nulls=Counter(r.get('value_status') for r in rows if r['value'] is None)
 if summary.get('records')!=records:raise ValueError('Archive summary.records differs from canonical observations')
 missing=sum(nulls.values())
 if 'missing_cells' in summary and summary['missing_cells']!=missing:raise ValueError('Archive summary.missing_cells differs from canonical observations')
 for row in rows:period_partition_key(row['data_year'])
 reference_years=sorted({r['data_year'] for r in rows if type(r['data_year']) is int});unresolved=sum(r['data_year'] is None for r in rows)
 if 'reference_years' in summary and summary['reference_years']!=reference_years:raise ValueError('Archive reference_years must contain confirmed integer years only')
 if summary.get('unresolved_period_records',0)!=unresolved:raise ValueError('Archive unresolved_period_records differs from canonical observations')
 labels={'source_blank':'原刊留白','not_available_in_source':'原刊明示缺值','source_null':'來源明列null','source_marker':'原印文字狀態（不自行解讀為0或不適用）','not_applicable':'原刊明示不適用'}
 if set(nulls)-set(labels):raise ValueError('Unreviewed null status in publication observations')
 parts=[f'原刊留白{nulls["source_blank"]:,}格',f'原刊明示缺值{nulls["not_available_in_source"]:,}格']
 parts.extend(f'{label}{nulls[status]:,}格' for status,label in labels.items() if status not in {'source_blank','not_available_in_source'} and nulls[status])
 return {'records':records,'missing_cells':missing,'reference_years':reference_years,'unresolved_period_records':unresolved,'null_status_counts':dict(sorted(nulls.items())),
         'null_description':'、'.join(parts),'value_status_counts':dict(sorted(Counter(r.get('value_status') for r in rows).items()))}

def period_partition_key(year):
 """Keep unresolved periods separate from confirmed calendar-year partitions."""
 if year is not None and type(year) is not int:raise ValueError('data_year must be a confirmed integer year or null')
 return (year is None,year)

def write_period_partitions(target,rows,canonical_path='data/combined/observations.jsonl.gz'):
 by_year={}
 for row in rows:period_partition_key(row['data_year']);by_year.setdefault(row['data_year'],[]).append(row)
 partitions=[]
 for year,records in sorted(by_year.items(),key=lambda item:period_partition_key(item[0])):
  path='data/by_year/unresolved_period.jsonl' if year is None else f'data/by_year/{year}.jsonl'
  body=''.join(json.dumps(r,ensure_ascii=False,separators=(',',':'))+'\n' for r in records).encode()
  output=target/path;output.parent.mkdir(parents=True,exist_ok=True);output.write_bytes(body)
  partitions.append({'data_year':year,'path':path,'records':len(records),'bytes':len(body),'sha256':sha(body)})
 index={'schema_version':'1.0.0','canonical_path':canonical_path,'records':len(rows),'unresolved_period_records':len(by_year.get(None,[])),'partitions':partitions,'partition_union_equals_canonical':True,'period_policy':'Integer years are confirmed reference years. Null years retain unresolved or multi-year original periods in unresolved_period.jsonl; never substitute zero or an edition/publication year.'}
 (target/'data/by_year/index.json').parent.mkdir(parents=True,exist_ok=True)
 (target/'data/by_year/index.json').write_bytes(jb(index))
 return index
