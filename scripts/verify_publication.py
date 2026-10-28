#!/usr/bin/env python3
"""Verify published checksums, row totals, keys and outcome aggregation offline."""
import argparse, json
from pathlib import Path
import duckdb
from build_historical import digest, quote, check

def verify_publication(path):
    path=Path(path)
    package=json.loads((path/'package.json').read_text())
    for item in package['files']:
        p=path/item['path']
        if not p.is_file() or p.stat().st_size!=item['bytes'] or digest(p)!=item['sha256']: raise ValueError('Damaged publication: '+str(p))
    c=duckdb.connect()
    for t in ['bills','actions','outcomes']:
        c.execute(f'CREATE VIEW {t} AS SELECT * FROM read_parquet({quote(path/"core"/(t+".parquet"))})')
    for t,n in [('bills',76867),('actions',401161)]:
        actual=c.execute(f'SELECT count(*) FROM {t}').fetchone()[0]
        if actual!=n: raise ValueError(f'{t}: {actual} != {n}')
    check(c,'SELECT count(*) FROM actions a LEFT JOIN bills b USING(bill_id) WHERE b.bill_id IS NULL','Orphan actions')
    for t,key in [('bills','bill_id'),('actions','action_id')]:
        check(c,f'SELECT count(*) FROM (SELECT {key} FROM {t} GROUP BY {key} HAVING count(*)>1)','Duplicate IDs')
    for left,right in [('SELECT congress,outcome,count(*) bill_count FROM bills GROUP BY congress,outcome','SELECT congress,outcome,bill_count FROM outcomes'),('SELECT congress,outcome,bill_count FROM outcomes','SELECT congress,outcome,count(*) bill_count FROM bills GROUP BY congress,outcome')]:
        check(c,f'SELECT count(*) FROM ({left} EXCEPT ALL {right})','Outcome mismatch')
    c.close()
    print('Publication verified: 76,867 bills; 401,161 actions; checksums, keys, joins and outcomes pass.')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('directory');verify_publication(p.parse_args().directory)
