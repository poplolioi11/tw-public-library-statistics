import copy,hashlib,unittest
import metadata_corrections as m

class MetadataCorrectionGuards(unittest.TestCase):
    def setUp(self):
        self.row={'observation_id':'one','series_id':'unchanged','source_id':'fixed','source_sha256':'a'*64,'source_field':'借閱冊數','source_locator':'JSON array[0]; metric=借閱冊數','source_url':'https://example.org/original.json','raw_value':'0','value':0,'value_status':'reported','unit':None,'unit_raw':None,'unit_status':'unconfirmed','data_year':2020}
        self.rule={'source_id':'fixed','source_sha256':'a'*64,'source_field':'借閱冊數','unit':'冊','canonical_null_unit_observations':1,'complete_observation_id_set_sha256':m.identity_hash(['one'])}
    def test_source_literal_changes_metadata_only_and_replays_idempotently(self):
        before=copy.deepcopy(self.row);changes=m.apply([self.row],[self.rule]);self.assertEqual(len(changes),1)
        self.assertEqual(self.row['unit'],'冊');self.assertIsNone(self.row['unit_raw'])
        for key in set(before)-set(m.CHANGED_FIELDS):self.assertEqual(before[key],self.row[key],key)
        self.assertEqual(m.apply([self.row],[self.rule]),[])
    def test_new_source_version_requires_review(self):
        self.row['source_sha256']='b'*64
        with self.assertRaises(ValueError):m.apply([self.row],[self.rule])
    def test_additional_observation_is_not_silently_promoted(self):
        second={**self.row,'observation_id':'two'}
        with self.assertRaises(ValueError):m.apply([self.row,second],[self.rule])
    def test_conflicting_unit_and_unsupported_literal_are_rejected(self):
        self.row['unit']='人次'
        with self.assertRaises(ValueError):m.apply([self.row],[self.rule])
    def test_prose_aggregate_unit_stays_on_its_exact_original_cell(self):
        self.row.update(source_field='電子資源／小計',unit_raw='',unit=None)
        self.rule.update(source_field='電子資源／小計',kind='same_document_explicit_aggregate_unit',unit='種',observation_id='one',supporting_original_text='電子資源0種',source_unit_context_locator='same original PDF page 2; collection paragraph',unit_basis='Direct original statement for only this national aggregate',exact_original_binding={'data_year':2020,'raw_value':'0','value':0})
        second={**self.row,'observation_id':'two'}
        self.assertEqual(len(m.apply([self.row,second],[self.rule])),1)
        self.assertEqual(self.row['unit'],'種');self.assertIsNone(second['unit'])
        self.row['raw_value']='1'
        with self.assertRaises(ValueError):m.apply([self.row],[self.rule])
    def test_version_ledger_cannot_exempt_unreviewed_or_numerical_changes(self):
        changes=m.apply([self.row],[self.rule])
        self.assertEqual(set(m.validated_overlays([self.row],changes,[self.rule])),{'one'})
        bad=copy.deepcopy(changes);bad[0]['old']['value']=42
        with self.assertRaises(ValueError):m.validated_overlays([self.row],bad,[self.rule])
        bad=copy.deepcopy(changes);bad.append({**changes[0],'observation_id':'unreviewed'})
        with self.assertRaises(ValueError):m.validated_overlays([self.row],bad,[self.rule])
        self.row['unit']=None;self.rule['unit']='元'
        with self.assertRaises(ValueError):m.apply([self.row],[self.rule])

if __name__=='__main__':unittest.main()
