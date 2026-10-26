#!/usr/bin/env python3
"""Check only reviewed public entry URLs; keep full HTML in the private Drive workspace.

This is a source-entry check, not statistical ingestion or redistribution approval.
No browser, login, credential output or guessed endpoint is used.
"""
from __future__ import annotations
import argparse,datetime,hashlib,json,re,urllib.error,urllib.parse,urllib.request
from html.parser import HTMLParser
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class EntryHTML(HTMLParser):
 def __init__(self):super().__init__(convert_charrefs=True);self.title=[];self.text=[];self.links=[];self.hidden=[];self.in_title=False;self.anchor=None
 def handle_starttag(self,tag,attrs):
  if tag in {'script','style','noscript','header','footer'}:self.hidden.append(tag)
  if tag=='title':self.in_title=True
  if not self.hidden and tag=='a':self.anchor=[dict(attrs).get('href'),[]]
 def handle_endtag(self,tag):
  if tag=='title':self.in_title=False
  if tag=='a' and self.anchor:self.links.append((self.anchor[0],' '.join(self.anchor[1])));self.anchor=None
  if self.hidden and tag==self.hidden[-1]:self.hidden.pop()
 def handle_data(self,value):
  value=' '.join(value.split())
  if not value:return
  if self.in_title:self.title.append(value)
  if not self.hidden:self.text.append(value)
  if self.anchor:self.anchor[1].append(value)
def sha(body):return hashlib.sha256(body).hexdigest()
def now():return datetime.datetime.now(datetime.timezone.utc)
def dump(path,value):path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
def checked_entry(spec,body,final_url,checked_at,status):
 parsed=EntryHTML();parsed.feed(body.decode('utf-8-sig',errors='replace'));title=' '.join(parsed.title)
 text=' '.join(parsed.text);links=[];seen=set()
 for href,label in parsed.links:
  if not href:continue
  if not label or not any(x in label for x in ('圖書館','統計','年鑑','資料','授權')) or any(x in label for x in ('聯絡','信箱','個資')):continue
  url=urllib.parse.urljoin(final_url,href)
  if urllib.parse.urlsplit(url).scheme not in ('http','https') or url in seen:continue
  seen.add(url);links.append({'label':label[:140],'url':url,'locator':'HTML anchor visible text: '+label[:100]})
 hits=[]
 for term in spec['terms']:
  p=text.find(term)
  if p>=0:
   excerpt=text[max(0,p-20):p+100]
   # A public evidence excerpt must not capture unrelated contact values.
   if not re.search(r'\b0\d[-\d() ]{6,}|[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}',excerpt):hits.append({'term':term,'excerpt':excerpt,'locator':'visible HTML text containing '+term})
 return {'id':spec['id'],'agency_name':spec['agency_name'],'role':spec['role'],'checked_url':spec['url'],'final_url':final_url,'page_title':title,'checked_at':checked_at,'method':'public_http_get','http_status':status,'body_sha256':sha(body),'evidence':hits,'relevant_links':links,'check_status':'checked_relevant_source_found' if hits else 'checked_entry_only','check_scope':'Only this exact public entry response and its listed links; linked tables are not thereby ingested or fully checked.','rights_status':'source_entry_metadata_only_not_redistribution_approval'}
def main():
 p=argparse.ArgumentParser();p.add_argument('--refresh',action='store_true');p.add_argument('--private-evidence-dir',type=Path);p.add_argument('--workspace-root',type=Path);p.add_argument('--expected-workspace-id');a=p.parse_args()
 specs=json.loads((ROOT/'scripts/phase1_central_sources.json').read_text())['sources'];out=ROOT/'raw/phase1-inventory/central.json'
 old=json.loads(out.read_text()) if out.exists() else {'sources':[]};previous={x['id']:x for x in old['sources']};rows=[];changed=[]
 if a.private_evidence_dir:
  if not a.workspace_root or not a.expected_workspace_id:raise ValueError('Saving full private evidence requires an explicitly configured workspace root and identity')
  evidence=a.private_evidence_dir.expanduser().resolve();drive=a.workspace_root.expanduser().resolve()
  if not drive.is_dir() or not evidence.is_relative_to(drive):raise ValueError('Private evidence must be inside the verified mounted AI workspace')
  markers=list(drive.glob('*'))
  if not any(a.expected_workspace_id in f.read_text(errors='ignore') for f in markers if f.is_file() and f.stat().st_size<100000):raise ValueError('Mounted workspace identity marker does not match the approved Drive folder ID')
  evidence.mkdir(parents=True,exist_ok=True)
 for spec in specs:
  prior=previous.get(spec['id']);timestamp=now()
  if prior and not a.refresh:
   last=datetime.datetime.fromisoformat(prior['checked_at'])
   if (timestamp-last).total_seconds()<spec['check_interval_days']*86400:rows.append(prior);continue
  try:
   req=urllib.request.Request(spec['url'],headers={'User-Agent':'tw-public-library-statistics/0.6.0 source-entry-check'})
   with urllib.request.urlopen(req,timeout=30) as response:
    body=response.read(8*1024*1024+1);final=response.url;status=response.status
   if len(body)>8*1024*1024:raise ValueError('Entry exceeds reviewed 8 MiB limit')
   row=checked_entry(spec,body,final,timestamp.isoformat(),status)
   if a.private_evidence_dir:
    file=evidence/(spec['id']+'-'+row['body_sha256'][:16]+'.html')
    if not file.exists():file.write_bytes(body)
    elif sha(file.read_bytes())!=row['body_sha256']:raise ValueError('Immutable private evidence path collision')
   if prior and prior.get('body_sha256')!=row['body_sha256']:changed.append({'source_id':spec['id'],'previous_sha256':prior.get('body_sha256'),'current_sha256':row['body_sha256'],'requires_scope_review':True})
  except Exception as exc:
   row={'id':spec['id'],'agency_name':spec['agency_name'],'role':spec['role'],'checked_url':spec['url'],'checked_at':timestamp.isoformat(),'method':'public_http_get','check_status':'request_failed','http_status':getattr(exc,'code',None),'body_sha256':None,'error_type':type(exc).__name__,'error_message':str(exc)[:200],'check_scope':'Request failed; this is not evidence of no published data.'}
   if prior:row['previous_successful_entry']=prior.get('previous_successful_entry',prior)
  rows.append(row)
 result={'schema_version':'1.0.0','scope':'Reviewed central public entries; statistical payloads and rights require separate review.','sources':rows,'source_changes_requiring_review':changed}
 if result!=old:dump(out,result)
 print(json.dumps({'entries':len(rows),'requests_failed':sum(x['check_status']=='request_failed' for x in rows),'changed_sources':changed},ensure_ascii=False))
if __name__=='__main__':main()
