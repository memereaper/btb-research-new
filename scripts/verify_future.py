#!/usr/bin/env python3
"""Verify the staged future package offline, without claiming analytical certification."""
import json
import duckdb
from build_historical import ROOT,digest
base=ROOT/'datasets/bipartisanship-v2'
for f in json.loads((base/'package.json').read_text())['files']:
    p=base/f['path']
    if not p.is_file() or digest(p)!=f['sha256'] or p.stat().st_size!=f['bytes']: raise ValueError('Damaged future package: '+str(p))
c=duckdb.connect();catalog=json.loads((base/'catalog.json').read_text())
if len(catalog['tables'])!=33:raise ValueError('Expected 33 tables')
for t in catalog['tables']:
    p=base/t['path']
    if digest(p)!=t['parquet_sha256']: raise ValueError('Parquet hash mismatch')
    n=c.execute('SELECT count(*) FROM read_parquet(?)',[str(p)]).fetchone()[0]
    if n!=t['rows']:raise ValueError('Row count mismatch: '+t['table'])
print('33 future tables: hashes and row counts verified. Analytical certification remains separate.')
