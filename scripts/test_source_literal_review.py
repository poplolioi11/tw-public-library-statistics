import copy,unittest
from source_literal_review import reviewed_literals,reviewed_non_scalar_literal
from validate_publication import validate_value_semantics,ValidationError

class OriginalNonScalarReview(unittest.TestCase):
    def test_all_sixteen_exact_originals_keep_null_and_complete_text(self):
        rows=reviewed_literals();self.assertEqual(len(rows),16)
        for identifier,row in rows.items():
            self.assertTrue(reviewed_non_scalar_literal(row));validate_value_semantics(row,identifier)

    def test_changed_raw_digits_source_sha_or_locator_are_rejected(self):
        original=next(iter(reviewed_literals().values()))
        for key,value in [('raw_value','149'),('source_sha256','f'*64),('source_locator','different row')]:
            row={**original,key:value}
            self.assertFalse(reviewed_non_scalar_literal(row))
            with self.assertRaises(ValidationError):validate_value_semantics(row,row['observation_id'])

    def test_review_does_not_permit_a_guessed_zero_or_scalar(self):
        original=next(iter(reviewed_literals().values()))
        for value in (0,1,49):
            row={**original,'value':value}
            with self.assertRaises(ValidationError):validate_value_semantics(row,row['observation_id'])

    def test_unregistered_unparsed_number_or_text_is_still_rejected(self):
        for raw in ('123','1(49)','每鄉各2'):
            with self.assertRaises(ValidationError):validate_value_semantics({'value':None,'raw_value':raw,'value_status':'source_marker'},'unreviewed')

if __name__=='__main__':unittest.main(verbosity=2)
