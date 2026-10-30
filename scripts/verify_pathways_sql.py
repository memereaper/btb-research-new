#!/usr/bin/env python3
"""Check the 116-119 SQL database against its inputs and its build receipt."""
import json
import duckdb
from build_historical import ROOT, digest
from build_pathways_sql import PACKAGES, TABLES

def verify(db=ROOT/'warehouse/sql/pathways-116-119.duckdb'):
    receipt = json.loads((ROOT/'docs/collections/pathways-116-119-sql.json').read_text())
    if digest(db) != receipt['database_sha256']: raise ValueError('Database does not match its build receipt')
    for p, h in receipt['inputs'].items():
        if digest(ROOT/'datasets'/p/'package.json') != h: raise ValueError('Input package changed since build: ' + p)
    c = duckdb.connect(str(db), read_only=True)
    expected = {}
    for p in PACKAGES:
        for t in json.loads((ROOT/'datasets'/p/'catalog.json').read_text())['tables']:
            expected[t['table']] = expected.get(t['table'], 0) + t['rows']
    for t in TABLES:
        n = c.execute(f'SELECT count(*) FROM {t}').fetchone()[0]
        if n != expected[t]: raise ValueError(f'{t}: {n} rows, inputs have {expected[t]}')
    checks = {
        'bill ids unique': "SELECT count(*) - count(DISTINCT bill_id) FROM bills",
        'action ids unique': "SELECT count(*) - count(DISTINCT action_id) FROM actions",
        'orphan actions': "SELECT count(*) FROM actions a ANTI JOIN bills b USING (bill_id)",
        'orphan cosponsors': "SELECT count(*) FROM cosponsors x ANTI JOIN bills b USING (bill_id)",
        'orphan subjects': "SELECT count(*) FROM subjects x ANTI JOIN bills b USING (bill_id)",
        'unparsed intro dates': "SELECT count(*) FROM bills WHERE introduced_on IS NULL",
        'congress coverage overlap': "SELECT count(*) FROM (SELECT congress_n FROM bills GROUP BY 1 HAVING count(DISTINCT source_collection) > 1)",
    }
    for name, sql in checks.items():
        if c.execute(sql).fetchone()[0] != 0: raise ValueError('Failed: ' + name)
    total = sum(expected[t] for t in TABLES)
    print(f'pathways-116-119.duckdb: {total:,} rows match inputs; {len(checks)} integrity checks pass')

if __name__ == '__main__':
    verify()
