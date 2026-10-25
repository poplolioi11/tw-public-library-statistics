#!/usr/bin/env python3
"""Register only originals actually used by the new statistical cohorts."""
import csv,hashlib,json
from pathlib import Path
R=Path(__file__).resolve().parents[1]
from cohort_registry import csv_names
def main():
 sources={};versions={}
 for filename in csv_names(R,('ncl_gap_tables_long.csv','ncl_earlier_years_long.csv','ncl_additional_years_long.csv')):
  path=R/'derived'/filename
  if not path.exists():continue
  with path.open(encoding='utf-8-sig') as f:
   for row in csv.DictReader(f):
    versions.setdefault((row['source_id'],row['source_sha256']),{'source_id':row['source_id'],'sha256':row['source_sha256'],'source_url':row['source_download_url'],'source_page_url':row['source_url'],'source_local_path':row['source_local_path'],'first_observed_at':row['source_retrieved_at'],'review_scope':'exact selected statistical tables; see component metadata'})
    key=(row['source_local_path'],row['source_sha256'])
    sources.setdefault(key,{'local_path':key[0],'sha256':key[1],'download_url':row['source_download_url'],'source_url':row['source_url'],'source_title':row.get('source_title'),'publication_date':row.get('publication_date'),'source_edition_roc':row.get('source_edition_roc'),'source_ids':[]})
    if row['source_id'] not in sources[key]['source_ids']:sources[key]['source_ids'].append(row['source_id'])
 for (path,expected),entry in sources.items():
  if hashlib.sha256((R/path).read_bytes()).hexdigest()!=expected:raise ValueError('Reviewed source hash differs: '+path)
  entry['source_ids'].sort()
 body=json.dumps(sorted(sources.values(),key=lambda x:x['local_path']),ensure_ascii=False,indent=2)+'\n'
 target=R/'raw/ncl-extension-documents.json'
 if not target.exists() or target.read_text()!=body:target.write_text(body)
 history=R/'data/historical_source_history.jsonl'
 events=[json.loads(x) for x in history.read_text().splitlines()] if history.exists() else []
 known={(x['source_id'],x['sha256']) for x in events}
 with history.open('a') as f:
  for key,item in sorted(versions.items()):
   if key not in known:
    item['previous_sha256s']=sorted({x['sha256'] for x in events if x['source_id']==item['source_id']})
    f.write(json.dumps(item,ensure_ascii=False,separators=(',',':'))+'\n')
 print('registered historical originals',len(sources))
if __name__=='__main__':main()
