#!/usr/bin/env python3
"""Generate row/field inventory and missingness from published collection packages."""
import csv,json
from pathlib import Path
import duckdb
from build_historical import ROOT,quote
from verify_collections import PACKAGES,verify
verify();out=ROOT/'docs/collections';out.mkdir(exist_ok=True,parents=True)
c=duckdb.connect();inventory=[];quality=[];sources=[]
for package in PACKAGES:
    base=ROOT/'datasets'/package;catalog=json.loads((base/'catalog.json').read_text())
    sources.extend([{'package':package,**s} for s in catalog.get('sources',[])])
    for table in catalog['tables']:
        p=base/'tables'/(table['table']+'.parquet')
        inventory.append({'package':package,'table':table['table'],'rows':table['rows'],'fields':len(table['fields']),'path':str(p.relative_to(ROOT))})
        c.execute(f'CREATE OR REPLACE VIEW q AS SELECT * FROM read_parquet({quote(p)})')
        for field in table['fields']:
            column='"'+field.replace('"','""')+'"'
            nulls,blanks=c.execute(f"SELECT count(*) FILTER(WHERE {column} IS NULL),count(*) FILTER(WHERE CAST({column} AS VARCHAR)='') FROM q").fetchall()[0]
            quality.append({'package':package,'table':table['table'],'field':field,'rows':table['rows'],'nulls':nulls,'empty_strings':blanks})
for name,rows in [('inventory.csv',inventory),('field-completeness.csv',quality)]:
    with (out/name).open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
(out/'sources.json').write_text(json.dumps(sources,indent=2)+'\n')
lines=['# Acquired collection inventory — October 28, 2026','','Counts overlap across relational tables. Do not add them as independent people, bills or events. Source fields retain strings; research SQL casts dates/numbers explicitly.','','| Package / table | Rows | Fields |','|---|---:|---:|']
lines += [f"| {x['package']} / {x['table']} | {x['rows']:,} | {x['fields']} |" for x in inventory]
lines += ['','Per-field missingness: field-completeness.csv. Exact URLs, retrieval timestamps, SHA-256 and HTTP response headers: sources.json. Methods, source scope and join limits: methods.md. Each dataset package includes its own checksums, catalog and validation report. Raw source bytes remain local under warehouse/collection-cache/objects/<sha256>. Sources were retrieved across a time window, not as a transactionally simultaneous extract.','',f'{len(inventory)} acquired/derived collection tables; {len(quality)} field-level completeness checks; {len(sources)} raw source snapshots referenced.']
(out/'inventory.md').write_text('\n'.join(lines)+'\n');c.close()
