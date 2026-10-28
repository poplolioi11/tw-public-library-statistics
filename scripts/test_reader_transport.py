import json,unittest
import reader_transport

class PortableTransport(unittest.TestCase):
    def test_complete_values_null_zero_empty_and_missing_survive(self):
        value={'rows':[{'value':0,'period':None,'raw':''},{'value':12.3,'raw':'12.30'},{}],'label':'原刊繁體中文'}
        packed=reader_transport.encode(value,threshold=1)
        self.assertEqual(reader_transport.decode(packed),value)

    def test_existing_plain_reader_is_unchanged(self):
        value={'dataset_version':'0.8.0','rows':[0,None,'']}
        self.assertEqual(reader_transport.encode(value),json.dumps(value,ensure_ascii=False,separators=(',',':')))
        self.assertEqual(reader_transport.decode(reader_transport.encode(value)),value)

    def test_changed_declared_sha_or_length_is_rejected(self):
        original=json.loads(reader_transport.encode({'rows':list(range(20))},threshold=1))
        for key,value in [('uncompressed_sha256','f'*64),('uncompressed_bytes',3)]:
            damaged={**original,key:value}
            with self.assertRaises(ValueError):reader_transport.decode(json.dumps(damaged))

if __name__=='__main__':unittest.main(verbosity=2)
