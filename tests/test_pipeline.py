import hashlib, json, sys, tempfile, unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from build_historical import build, digest, verify
from import_csv import ingest

class PipelineTests(unittest.TestCase):
    def test_manifest_rejects_corruption(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d); (p/'data').write_bytes(b'original')
            (p/'manifest.json').write_text(json.dumps({'artifacts':[{'path':'data','bytes':8,'sha256':digest(p/'data')}]}))
            verify(p); (p/'data').write_bytes(b'modified')
            with self.assertRaises(ValueError): verify(p)

    def test_failed_build_preserves_current(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d); (p/'warehouse').mkdir(); current=p/'warehouse/current.json'
            current.write_text('{"snapshot_id":"last-good"}')
            (p/'source').mkdir(); (p/'source/invalid.csv').write_text('bad,input\n')
            with self.assertRaises(Exception): build(p/'source',p)
            self.assertEqual(current.read_text(),'{"snapshot_id":"last-good"}')
            self.assertFalse(list((p/'warehouse/snapshots').glob('.building-*')))

    def test_lossless_future_csv(self):
        import import_csv, duckdb
        with tempfile.TemporaryDirectory() as d:
            p=Path(d); src=p/'test.csv'; src.write_text('id,value\n001,""\n002,"a,b"\n003,NA\n')
            previous=import_csv.ROOT; import_csv.ROOT=p
            try:
                target=ingest(src,'https://example.org/source','fixture')
                self.assertEqual(target,ingest(src,'https://example.org/source','fixture'))
                self.assertEqual(duckdb.connect().execute('SELECT id,value FROM read_parquet(?) ORDER BY id',[str(target/'staging.parquet')]).fetchall(),[('001',''),('002','a,b'),('003','NA')])
                self.assertEqual(src.read_bytes(),(target/'original.csv').read_bytes())
            finally: import_csv.ROOT=previous
if __name__ == '__main__': unittest.main()
