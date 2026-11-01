#!/usr/bin/env python3
"""Package an allowlisted private audit with reader/evaluator separation."""
import argparse, hashlib, json, shutil, zipfile
from pathlib import Path

def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def sums(root):
    files=sorted(p for p in root.rglob('*') if p.is_file() and p.name!='SHA256SUMS')
    (root/'SHA256SUMS').write_text(''.join(f'{digest(p)}  {p.relative_to(root).as_posix()}\n' for p in files))
def zip_checked(root,path):
    with zipfile.ZipFile(path,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for p in sorted(root.rglob('*')):
            if p.is_file():
                info=zipfile.ZipInfo(p.relative_to(root).as_posix(),date_time=(2026,10,30,0,0,0))
                info.compress_type=zipfile.ZIP_DEFLATED; info.external_attr=0o100644<<16
                z.writestr(info,p.read_bytes())
    with zipfile.ZipFile(path) as z:
        assert z.testzip() is None
        for n in z.namelist(): assert z.read(n)==(root/n).read_bytes()
    return {'file':path.name,'bytes':path.stat().st_size,'sha256':digest(path),'members':len(z.namelist())}
def main():
    p=argparse.ArgumentParser();p.add_argument('--private',type=Path,required=True)
    p.add_argument('--task-root',type=Path,required=True);a=p.parse_args();task=a.task_root
    stage=task/'delivery-staging';stage.mkdir(exist_ok=False)
    shutil.copytree(task/'frozen-v1',stage/'controller')
    c=stage/'controller';(c/'code').mkdir()
    for name in ['prepare_manual_quality_sample.py','validate_manual_quality_sample.py','package_manual_quality_sample.py']:
        shutil.copy2(a.private/'scripts'/name,c/'code'/name)
    for name in ['交接核對與抽樣準備.md','validation-final.json']:
        shutil.copy2(task/name,c/name)
    (c/'重跑說明.md').write_text('''# 控制者包，請勿給盲讀者

資料庫比較鍵不是人工標準答案。真正盲讀者只取得 reader ZIP；原件選頁本來包含官方數值，與資料庫預期答案隔離。

使用固定版本公開 checkout 及已有原始檔的私人工作目錄，Python 需 pypdf；重跑時指定一個不存在的新輸出目錄：

```sh
python3 code/prepare_manual_quality_sample.py --private PRIVATE_DATASET --public PUBLIC_CHECKOUT --output NEW_OUTPUT
python3 code/validate_manual_quality_sample.py --private PRIVATE_DATASET --public PUBLIC_CHECKOUT --package NEW_OUTPUT
```

相同 seed、Python 3.12.14、固定 canonical SHA 與 observation_id 會重現同一120筆。輸出PDF封裝bytes可能受函式庫版本影響；比較原件SHA、頁內容流及抽樣清單，不宣稱其他版本重建PDF二進位必定相同。

檢查 PREPARATION_LOCK.json 及 SHA256SUMS，可偵測讀表、來源索引、程式或附件是否更動。這是私人凍結，不是公開註冊。人工讀值尚未開始；空白欄不等於0錯誤。
''',encoding='utf-8')
    # Seal reader first; key files remain outside that ZIP.
    sums(c/'reader')
    locked={p.relative_to(c).as_posix():digest(p) for p in sorted(c.rglob('*')) if p.is_file()}
    lock={'schema_version':'1.0.0','role':'private_pre_human_reading_preparation_lock',
          'human_readings_completed':0,'files':locked,
          'reader_package_excludes':['evaluator_DO_NOT_GIVE_TO_READER','selected-database-rows.json','database-comparator.json']}
    (c/'PREPARATION_LOCK.json').write_text(json.dumps(lock,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    sums(c)
    delivery=task/'deliverables';delivery.mkdir(exist_ok=False)
    reports=[zip_checked(c/'reader',delivery/'library-v091-manual-audit-reader-120-v1.zip'),
             zip_checked(c,delivery/'library-v091-manual-audit-controller-v1.zip')]
    shutil.copy2(task/'交接核對與抽樣準備.md',delivery/'交接核對與抽樣準備.md')
    reports.append({'file':'交接核對與抽樣準備.md','bytes':(delivery/'交接核對與抽樣準備.md').stat().st_size,'sha256':digest(delivery/'交接核對與抽樣準備.md')})
    (delivery/'交付檔案清單.json').write_text(json.dumps({'version':'manual-audit-preparation-1.0.0','artifacts':reports,'human_readings_completed':0,'accuracy_estimate':None},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(reports,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
