# 資料更正與新增來源

請以官方原始網址、資料年、原表位置與可核對的值提出更正。保留原始回報、缺值與口徑，推算或猜測值不能覆寫官方原值。新增來源須先確認取得方式及再利用依據，一次完成可界定的整表或來源批次。

原件與公開欄位投影使用不同的雜湊。與統計無關的聯絡欄、憑證、私人路徑、完整未確認授權的PDF或網頁原碼，不應加入提交。若需要從原件重新驗收，請依README還原到本地，再產生不含這些欄位的公開副本。

提交前執行：

```sh
python -m unittest discover -s scripts -p 'test_*.py'
python -m unittest discover -s tests -p 'test_*.py'
python scripts/validate_publication.py --self-test
python scripts/validate_publication.py
```

資料或程式有變更時，請重新產生公開檔案manifest並保留舊版發布，不直接改寫已發布標籤。原始資料的錯誤或定義疑義應明示，不能把測試通過當成官方統計必然正確。
