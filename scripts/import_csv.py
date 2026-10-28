#!/usr/bin/env python3
"""Archive and stage any future CSV as a content-addressed, text-first dataset."""
import argparse, json, os, shutil, tempfile
from datetime import datetime, timezone
from pathlib import Path
import duckdb
from build_historical import ROOT, digest, quote

def ingest(src, url, dataset):
    src = Path(src).expanduser().resolve()
    if not src.is_file() or src.suffix.lower() != '.csv': raise ValueError('An existing CSV is required')
    import re
    if not re.fullmatch(r'[a-z0-9][a-z0-9_-]*',dataset): raise ValueError('Use a lowercase dataset slug')
    sha = digest(src)
    parent = ROOT/'warehouse/datasets'/dataset; parent.mkdir(parents=True,exist_ok=True)
    target = parent/sha
    if target.exists():
        m = json.loads((target/'manifest.json').read_text())
        if digest(target/'original.csv') != sha or digest(target/'staging.parquet') != m['parquet_sha256']: raise ValueError('Existing dataset is damaged')
        print(target); return target
    temp = Path(tempfile.mkdtemp(prefix='.import-',dir=parent))
    try:
        shutil.copy2(src,temp/'original.csv')
        if b'__BTB_RESERVED_NULL__' in src.read_bytes(): raise ValueError('Reserved null marker in source')
        c = duckdb.connect()
        c.execute(f"CREATE TABLE staged AS SELECT *, row_number() OVER () AS _btb_source_row FROM read_csv({quote(temp/'original.csv')},header=true,all_varchar=true,nullstr='__BTB_RESERVED_NULL__')")
        c.execute(f"COPY staged TO {quote(temp/'staging.parquet')} (FORMAT PARQUET,COMPRESSION ZSTD)")
        manifest = {'dataset':dataset,'source_url':url,'original_filename':src.name,'sha256':sha,'retrieved_utc':datetime.now(timezone.utc).isoformat(),'rows':c.execute('SELECT count(*) FROM staged').fetchone()[0],'columns':[d[0] for d in c.execute('SELECT * FROM staged LIMIT 0').description],'parquet_sha256':digest(temp/'staging.parquet'),'status':'staged_only; source-specific mapping and validation required before analysis'}
        (temp/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
        c.close(); os.rename(temp,target)
    except BaseException:
        shutil.rmtree(temp,ignore_errors=True); raise
    print(target); return target
if __name__ == '__main__':
    p=argparse.ArgumentParser(); p.add_argument('csv'); p.add_argument('--source-url',required=True); p.add_argument('--dataset',required=True)
    a=p.parse_args(); ingest(a.csv,a.source_url,a.dataset)
