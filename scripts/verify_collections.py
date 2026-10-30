#!/usr/bin/env python3
"""Offline verification of all new research collection packages."""
import argparse,json
from pathlib import Path
import duckdb
from build_historical import ROOT,digest
PACKAGES=['pathways-2026-10-28','pathways-116-117-2026-10-29','house-2024-pathway-votes','member-crosswalk-2026-10-28','text-survival-pilot-2026-10-28','pathway-research-2026-10-28']
def verify(root=ROOT,raw=False):
    c=duckdb.connect();total_tables=0
    for name in PACKAGES:
        base=root/'datasets'/name
        package=json.loads((base/'package.json').read_text())
        for f in package['files']:
            p=base/f['path']
            if not p.is_file() or p.stat().st_size!=f['bytes'] or digest(p)!=f['sha256']:raise ValueError('Damaged artifact: '+str(p))
        catalog=json.loads((base/'catalog.json').read_text())
        for source_package,expected in catalog.get('input_package_sha256',{}).items():
            if digest(root/'datasets'/source_package/'package.json')!=expected:raise ValueError('Input package version mismatch')
        for table in catalog['tables']:
            p=base/'tables'/(table['table']+'.parquet')
            if c.execute('SELECT count(*) FROM read_parquet(?)',[str(p)]).fetchone()[0]!=table['rows']:raise ValueError('Count mismatch')
            names=[d[0] for d in c.execute('SELECT * FROM read_parquet(?) LIMIT 0',[str(p)]).description]
            if names!=table['fields']:raise ValueError('Schema mismatch')
            total_tables+=1
        report=json.loads((base/'validation.json').read_text())
        if not all(report.get('checks',{}).values()):raise ValueError('Failed validation: '+name)
        if raw:
            for source in catalog.get('sources',[]):
                p=root/'warehouse/collection-cache/objects'/source['sha256']
                if not p.is_file() or digest(p)!=source['sha256']:raise ValueError('Missing/corrupt raw source '+source['url'])
        print(name+': hashes, rows, schemas and saved checks pass')
    c.close();print(total_tables,'new collection tables verified')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--raw',action='store_true');a=p.parse_args();verify(raw=a.raw)
