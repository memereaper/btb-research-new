#!/usr/bin/env python3
"""Query the promoted local snapshot and supplied future staging directly."""
import argparse,json
from pathlib import Path
import duckdb
from build_historical import ROOT,verify
p=argparse.ArgumentParser();p.add_argument('--sql');p.add_argument('--file',type=Path);a=p.parse_args()
base=ROOT/'warehouse/snapshots'/json.loads((ROOT/'warehouse/current.json').read_text())['snapshot_id']
verify(base);c=duckdb.connect()
for folder,prefix in [(base/'core',''),(base/'staging','hist_'),(ROOT/'datasets/bipartisanship-v2/staging','future_')]:
    for f in folder.glob('*.parquet'): c.read_parquet(str(f)).create_view(prefix+f.stem.lower())
sql=a.file.read_text() if a.file else a.sql
if not sql:p.error('--sql or --file is required')
r=c.execute(sql);print([d[0] for d in r.description]);print(*r.fetchall(),sep='\n')
