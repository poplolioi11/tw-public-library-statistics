"""Unit evidence replay must not exempt numerical facts or unknown sources."""
import copy
import csv
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import verify_release as verifier


def identity_hash(ids):
    return hashlib.sha256(('\n'.join(sorted(ids))+'\n').encode()).hexdigest()


class MetadataVerifierGuards(unittest.TestCase):
    def setUp(self):
        self.row = {'observation_id':'one','source_id':'fixed','source_sha256':'a'*64,
                    'source_field':'借閱冊數','source_locator':'JSON array[0]; metric=借閱冊數',
                    'source_url':'https://example.gov.tw/source.json','raw_value':'10',
                    'value':10,'value_status':'reported','data_year':2023,'unit_raw':None,
                    'unit':'冊','unit_status':'explicit_original_field_name_unit',
                    'unit_basis':'Exact original JSON field 借閱冊數; source-version and complete observation set reviewed; see docs/metadata-review-20261029.json',
                    'source_unit_context_locator':'JSON array[0]; metric=借閱冊數; literal original JSON field-name suffix 冊數'}
        self.rule = {'source_id':'fixed','source_sha256':'a'*64,'source_field':'借閱冊數',
                     'unit':'冊','canonical_null_unit_observations':1,
                     'complete_observation_id_set_sha256':identity_hash(['one'])}
        self.ledger = {'observation_id':'one','source_id':'fixed','source_sha256':'a'*64,
                       'source_url':self.row['source_url'],'source_locator':self.row['source_locator'],
                       'original_field_name':'借閱冊數',
                       'old':{'unit':None,'unit_status':'unconfirmed','unit_basis':None,'source_unit_context_locator':None},
                       'new':{key:self.row[key] for key in verifier.METADATA_FIELDS}}

    def replay(self, row=None, rule=None, ledger=None):
        return verifier.metadata_before_review([row or self.row],[rule or self.rule],[ledger or self.ledger])

    def test_only_unit_metadata_is_reversed_without_mutation(self):
        before=copy.deepcopy(self.row)
        old=self.replay()[0]
        self.assertEqual(self.row,before)
        self.assertIsNone(old['unit'])
        for key in set(before)-verifier.METADATA_FIELDS:
            self.assertEqual(old[key],before[key],key)

    def test_wrong_unit_or_context_is_rejected(self):
        for change in [{'unit':'人次'},{'unit_basis':'guessed'},{'source_unit_context_locator':'elsewhere'}]:
            with self.subTest(change=change),self.assertRaises(ValueError):
                self.replay({**self.row,**change})

    def test_changed_source_and_expanded_ids_require_review(self):
        with self.assertRaises(ValueError):
            self.replay({**self.row,'source_sha256':'b'*64})
        with self.assertRaises(ValueError):
            verifier.metadata_before_review([self.row,{**self.row,'observation_id':'two'}],[self.rule],[self.ledger])

    def test_ledger_cannot_revert_raw_values_or_previously_known_units(self):
        for change in [{'value':999},{'unit':'元'}]:
            bad=copy.deepcopy(self.ledger);bad['old'].update(change)
            with self.subTest(change=change),self.assertRaises(ValueError):self.replay(ledger=bad)

    def test_unsupported_field_suffix_is_rejected(self):
        row={**self.row,'source_field':'借閱量'}
        rule={**self.rule,'source_field':'借閱量'}
        with self.assertRaises(ValueError):self.replay(row,rule)

    def test_same_document_aggregate_cannot_change_its_raw_number_or_period(self):
        row={**self.row,'source_field':'合計','unit':'種','unit_status':'same_source_body_explicit_matching_aggregate',
             'unit_basis':'explicit same-document aggregate','source_unit_context_locator':'PDF page 2; collection paragraph'}
        rule={**self.rule,'kind':'same_document_explicit_aggregate_unit','source_field':'合計','unit':'種',
              'observation_id':'one','supporting_original_text':'電子資源10種',
              'unit_basis':row['unit_basis'],'source_unit_context_locator':row['source_unit_context_locator'],
              'exact_original_binding':{'raw_value':'10','value':10,'data_year':2023}}
        ledger={**self.ledger,'original_field_name':'合計','new':{key:row[key] for key in verifier.METADATA_FIELDS}}
        self.assertIsNone(self.replay(row,rule,ledger)[0]['unit'])
        for change in [{'raw_value':'11'},{'value':11},{'data_year':2024}]:
            with self.subTest(change=change),self.assertRaises(ValueError):
                self.replay({**row,**change},rule,ledger)

    def component_fixture(self, root, mutate_value=False):
        for folder in ['scripts','derived','data','raw/official-local/catalog-fixture']:
            (root/folder).mkdir(parents=True,exist_ok=True)
        raw_row={'統計年月':'11201','借閱冊數':'10'}
        raw=root/'raw/source.json';raw.write_text(json.dumps([raw_row],ensure_ascii=False))
        raw_sha=verifier.digest(raw.read_bytes())
        url=self.row['source_url'];catalogue_url='https://data.gov.tw/dataset/fixture'
        catalog=root/'raw/catalog.html'
        catalog.write_text('<script type="application/ld+json">'+json.dumps({'@type':'Dataset','license':'https://data.gov.tw/license','distribution':[{'contentUrl':url}]})+'</script>政府資料開放授權條款')
        folder=root/'raw/official-local/catalog-fixture'
        (folder/'catalog-record.json').write_text(json.dumps({'catalog_path':'raw/catalog.html','catalog_sha256':verifier.digest(catalog.read_bytes())}))
        (folder/'resource-1.metadata.json').write_text(json.dumps({'source_download_url':url,'source_sha256':raw_sha,'raw_path':'raw/source.json','status':'downloaded','format':'json','dataset_id':'fixture'}))
        source={'source_download_url':url,'source_sha256':raw_sha,'source_locator':'JSON array[0]',
                'original_fields':json.dumps(raw_row,ensure_ascii=False),'metric_raw':'借閱冊數',
                'value_raw':'10','period_raw':'11201','facility_raw':'','period_effective':'11201',
                'period_effective_basis':'observation_field','periodicity_raw':'月','duplicate_of':'',
                'record_id':'first','county':'新竹市','geography_code_raw':'','district_code_raw':'',
                'metric_group_raw':'','unit_raw':'','source_url':catalogue_url}
        with (root/'derived/local_historical_long.csv').open('w',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=list(source));writer.writeheader();writer.writerow(source)
        for name in ['ncl_historical_long.csv','dgbas_historical_long.csv']:
            (root/'derived'/name).write_text('source_id,data_year,entity_raw,metric_raw\n')
        row={**self.row,'source_sha256':raw_sha,'source_record_id':'first','source_family':'地方政府開放歷史表',
             'source_page_url':catalogue_url,'period_raw':'11201','period_effective':'11201',
             'periodicity_raw':'月','geography':'新竹市','source_snapshot_path':'raw/source.json',
             'period_start':None,'period_end':None,'facility':None,'geographic_scope':'county_official_table',
             'value_parse_rule':'standard_numeric_or_marker'}
        if mutate_value:row.update(raw_value='11',value=11)
        (root/'data/component_records.jsonl').write_text(json.dumps(row,ensure_ascii=False)+'\n')
        rule={**self.rule,'source_sha256':raw_sha}
        ledger={**self.ledger,'source_sha256':raw_sha}
        register=root/'scripts/reviewed_metadata_corrections.json'
        register.write_text(json.dumps({'review_status':'pinned_original_fields_replayed_not_human_double_collation','rules':[rule]},ensure_ascii=False))
        history=root/'derived/metadata-corrections-20261029.jsonl';history.write_text(json.dumps(ledger,ensure_ascii=False)+'\n')
        return verifier.digest(register.read_bytes()),verifier.digest(history.read_bytes())

    def test_original_json_verification_accepts_only_the_scoped_unit_change(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);rule_sha,ledger_sha=self.component_fixture(root)
            with patch.object(verifier,'METADATA_RULE_SHA',rule_sha),patch.object(verifier,'METADATA_LEDGER_SHA',ledger_sha):
                check=verifier.Verification(root);check.components()
            self.assertEqual(check.failures,[])
            self.assertEqual(check.result['reviewed_unit_metadata']['observations_checked'],1)

    def test_unit_evidence_does_not_hide_changed_original_number(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);rule_sha,ledger_sha=self.component_fixture(root,mutate_value=True)
            with patch.object(verifier,'METADATA_RULE_SHA',rule_sha),patch.object(verifier,'METADATA_LEDGER_SHA',ledger_sha):
                check=verifier.Verification(root);check.components()
            self.assertIn('local_adapter_field',{item['code'] for item in check.failures})
            self.assertIn('local_value_and_unit',{item['code'] for item in check.failures})

    def test_changed_frozen_evidence_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);self.component_fixture(root)
            with self.assertRaisesRegex(ValueError,'evidence changed'):
                verifier.Verification(root).components()


if __name__=='__main__':unittest.main()
