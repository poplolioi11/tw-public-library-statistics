#!/usr/bin/env python3
"""Keep the public viewer entrance after the existing documentation builders."""
import argparse,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
URL='https://poplolioi11.github.io/tw-public-library-statistics/'
def write(path,body):
 if not path.is_file() or path.read_text()!=body:path.write_text(body)
def block(path,text):
 body=path.read_text();pattern=r'\n*<!-- BEGIN lightweight-site -->.*?<!-- END lightweight-site -->\n*'
 body=re.sub(pattern,'\n\n',body,flags=re.S).rstrip()
 write(path,body+'\n\n<!-- BEGIN lightweight-site -->\n'+text.strip()+'\n<!-- END lightweight-site -->\n')
def main():
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=ROOT);a=p.parse_args();r=a.root.resolve();s=json.loads((r/'docs/light-site-summary.json').read_text());quantitative=json.loads((r/'docs/phase2-summary.json').read_text())['total_quantitative_records']
 text='## 公開輕量圖表網站\n\n[直接開啟圖表]('+URL+')。不必下載整份HTML；先載入問題目錄，再按所選數列讀取小型JSON。手機刻度文字使用固定字級；每個點位及表格數值都能回官方原件或官方動態查詢入口，另附原件SHA、原表位置與版次。\n\n資料版本仍為 **v'+s['dataset_version']+'**，閱覽器另列 **v'+s['viewer_version']+'**。既有'+str(s['source_charts']['phase2'])+'組原刊數列、'+str(s['source_charts']['phase3'])+'組問題內數列與'+str(s['precomputed_interval_queries'])+'個預算區間完整轉出；相同原數列可出現在不同問題，這些數量不可相加成統計觀測。只改呈現與傳輸，原值、缺值、口徑、選源及准許線段不變。單期事實與沒有合格圖表的問題仍請查完整資料包；沒有圖不表示沒有資料。\n\n[網站範圍、重建與驗收](docs/LIGHTWEIGHT_SITE.md)。既有單檔閱覽頁仍作離線用途，GitHub Pages只部署 `site/light/`。'
 batches=s.get('source_batches',{})
 if batches.get('records'):
  text=text.replace('單期事實與沒有合格圖表的問題仍請查完整資料包；沒有圖不表示沒有資料。','明列的單期來源批次另以完整表格提供；其他沒有合格圖表的紀錄仍保留於正式資料包。')
  text+='\n\n[2004年公共館來源表：24筆統計量]('+URL+'?batch=ncl94-statistics)：94年卷表145、146、147的16個原表格子，主量16筆、填答館數8筆分列。這批只有單一年份，沒有新增跨年折線；未知單位、原母體、原值與原表定位照列，每個數值可點回官方PDF。人工抽樣核讀與雙校仍未完成。'
 block(r/'README.md',text)
 body=(r/'README.md').read_text();marker='## 從哪裡開始\n\n'
 if marker in body and '[公開輕量圖表網站]('+URL+')' not in body:write(r/'README.md',body.replace(marker,marker+'- [公開輕量圖表網站]('+URL+')：直接查閱、可分享查詢網址，逐筆回官方來源。\n',1))
 block(r/'AI_USAGE.md','## 輕量網站不是新的分析資料\n\n網站 '+URL+' 的JSON分檔只投影既有合格圖表，不代表全部'+f'{quantitative:,}'+'個量化紀錄。AI正式分析仍依本文件原讀取入口。畫點值可能沿用第二階段已核單位尺度；`original_value`、`raw_value`、`original_unit`與`facets`仍留原量及口徑。`source_url`／`source_sha256`／`source_locator`／`source_version_id`不改，動態查詢另附`official_url`與重現提示。不得把網站顯示值或內容雜湊檔名誤當官方原件SHA。')
 block(r/'COVERAGE.md','## 網站呈現範圍\n\n[公開輕量圖表網站]('+URL+')保留既有全部合格原刊圖表與問題內圖表，按需讀取。此項改版沒有補新年、推算2012原量或認證新的跨年口徑；完整度仍依本文件各來源批次。單期事實、未解與不可繪圖記錄留在原資料包。')
 block(r/'llms.txt','## Public lightweight chart viewer\n\n'+URL+'\nViewer version '+s['viewer_version']+'; dataset version '+s['dataset_version']+'. Presentation-only chart shards; use the canonical/phase1/phase2/phase3 files for complete analysis. Never infer missing observations from the chart catalog. Every numeric point retains official source URL, source SHA, locator and version. docs/LIGHTWEIGHT_SITE.md describes the projection.')
 if batches.get('records'):
  for name in ('AI_USAGE.md','COVERAGE.md','llms.txt'):
   path=r/name;body=path.read_text()
   if name=='AI_USAGE.md':
    body=body.replace('的JSON分檔只投影既有合格圖表','的JSON分檔投影既有合格圖表與明列的完整來源表批次')
    extra='\n\n國圖94年卷24筆單期統計另用 `?batch=ncl94-statistics` 按需讀取，與跨年數列分開。`mode=batch` 的 `records` 逐筆保留正式 `observation_id`、原值、單位狀態、主量／填答館數角色、期間及原母體；`lines=[]`。原件與網站投影各驗自己的SHA；不得由同年不同指標或子群畫時間折線。人工抽樣核讀與雙校尚未完成。'
   elif name=='COVERAGE.md':
    body=body.replace('單期事實、未解與不可繪圖記錄留在原資料包。','國圖94年卷2004年24筆單期觀測已以完整來源表呈現，原值、未知單位、主量與填答館數分列；未新增跨年線段。其他未解或尚未納入網站的記錄仍留在正式資料包。')
    extra='\n\n來源表固定入口：'+URL+'?batch=ncl94-statistics。人工核讀與雙校尚未完成，程式與AI核讀不算人工完成。'
   else:
    body=body.replace('Presentation-only chart shards;','Presentation-only chart and explicitly registered source-table shards;')
    extra='\n\nSource table batch: '+URL+'?batch=ncl94-statistics . All24observations/16physical cells from NCL94 tables145/146/147, data year2004, are preserved as a table. Primary quantities and answering-library counts are distinct. No new approved temporal edges. Human sample reading and independent double collation remain incomplete.'
   body=body.replace('<!-- END lightweight-site -->',extra+'\n<!-- END lightweight-site -->')
   write(path,body)
 path=r/'docs/publishing-channels.json';channels=json.loads(path.read_text());channels['channels']=[c for c in channels['channels'] if c.get('kind')!='public_lightweight_site'];channels['channels'].append({'kind':'public_lightweight_site','url':URL,'path':'site/light/index.html','viewer_version':s['viewer_version'],'dataset_version':s['dataset_version'],'update_policy':'validated main commit; deploy only site/light after public package CI succeeds; immutable dataset releases remain separate'})
 write(path,json.dumps(channels,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps({'public_url':URL,'viewer_version':s['viewer_version'],'dataset_version':s['dataset_version']},ensure_ascii=False))
if __name__=='__main__':main()
