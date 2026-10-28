#!/usr/bin/env python3
"""Validate the promoted snapshot and its normalized tables; refuse empty research."""
import json
import duckdb
from build_historical import ROOT, quote, verify, check
pointer = ROOT/'warehouse/current.json'
if not pointer.exists(): raise SystemExit('No promoted snapshot. Run scripts/build_historical.py with the original archive extracted.')
path = ROOT/'warehouse/snapshots'/json.loads(pointer.read_text())['snapshot_id']
verify(path)
c = duckdb.connect()
for t in ['bills','actions']:
    c.execute(f'CREATE VIEW {t} AS SELECT * FROM read_parquet({quote(path/"core"/(t+".parquet"))})')
    print(t,c.execute(f'SELECT count(*) FROM {t}').fetchone()[0])
check(c,'SELECT count(*) FROM actions a LEFT JOIN bills b USING(bill_id) WHERE b.bill_id IS NULL','Orphan actions')
check(c,'SELECT count(*) FROM (SELECT action_id FROM actions GROUP BY action_id HAVING count(*)>1)','Duplicate action IDs')
print('Snapshot hashes and relational validation passed.')
