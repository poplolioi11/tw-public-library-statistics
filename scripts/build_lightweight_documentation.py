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
 block(r/'README.md',text)
 body=(r/'README.md').read_text();marker='## 從哪裡開始\n\n'
 if marker in body and '[公開輕量圖表網站]('+URL+')' not in body:write(r/'README.md',body.replace(marker,marker+'- [公開輕量圖表網站]('+URL+')：直接查閱、可分享查詢網址，逐筆回官方來源。\n',1))
 block(r/'AI_USAGE.md','## 輕量網站不是新的分析資料\n\n網站 '+URL+' 的JSON分檔只投影既有合格圖表，不代表全部'+f'{quantitative:,}'+'個量化紀錄。AI正式分析仍依本文件原讀取入口。畫點值可能沿用第二階段已核單位尺度；`original_value`、`raw_value`、`original_unit`與`facets`仍留原量及口徑。`source_url`／`source_sha256`／`source_locator`／`source_version_id`不改，動態查詢另附`official_url`與重現提示。不得把網站顯示值或內容雜湊檔名誤當官方原件SHA。')
 block(r/'COVERAGE.md','## 網站呈現範圍\n\n[公開輕量圖表網站]('+URL+')保留既有全部合格原刊圖表與問題內圖表，按需讀取。此項改版沒有補新年、推算2012原量或認證新的跨年口徑；完整度仍依本文件各來源批次。單期事實、未解與不可繪圖記錄留在原資料包。')
 block(r/'llms.txt','## Public lightweight chart viewer\n\n'+URL+'\nViewer version '+s['viewer_version']+'; dataset version '+s['dataset_version']+'. Presentation-only chart shards; use the canonical/phase1/phase2/phase3 files for complete analysis. Never infer missing observations from the chart catalog. Every numeric point retains official source URL, source SHA, locator and version. docs/LIGHTWEIGHT_SITE.md describes the projection.')
 path=r/'docs/publishing-channels.json';channels=json.loads(path.read_text());channels['channels']=[c for c in channels['channels'] if c.get('kind')!='public_lightweight_site'];channels['channels'].append({'kind':'public_lightweight_site','url':URL,'path':'site/light/index.html','viewer_version':s['viewer_version'],'dataset_version':s['dataset_version'],'update_policy':'validated main commit; deploy only site/light after public package CI succeeds; immutable dataset releases remain separate'})
 write(path,json.dumps(channels,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps({'public_url':URL,'viewer_version':s['viewer_version'],'dataset_version':s['dataset_version']},ensure_ascii=False))
if __name__=='__main__':main()
