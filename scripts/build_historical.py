#!/usr/bin/env python3
"""Build an immutable, content-addressed historical snapshot; promote only after checks."""
import argparse, hashlib, json, os, shutil, tempfile
from datetime import datetime, timezone
from pathlib import Path
import duckdb
ROOT = Path(__file__).resolve().parents[1]
VERSION = 'historical-v1'
SOURCE_URL = 'https://drive.google.com/file/d/1j3lqcLMBMg-HJN3at9YJlNqh1cyzzCmm/view'
def digest(p):
    h = hashlib.sha256()
    with p.open('rb') as f:
        for block in iter(lambda: f.read(1024*1024), b''): h.update(block)
    return h.hexdigest()
def quote(s): return "'" + str(s).replace("'", "''") + "'"
def check(c, sql, message):
    n = c.execute(sql).fetchone()[0]
    if n: raise ValueError(f'{message}: {n}')
def build(source, root=ROOT):
    source = Path(source).resolve()
    files = sorted(p for p in source.rglob('*') if p.is_file())
    if not files: raise ValueError('Source directory is empty')
    if any(b'__BTB_RESERVED_NULL__' in p.read_bytes() for p in files): raise ValueError('Reserved null marker in source')
    entries = [{'path':str(p.relative_to(source)), 'sha256':digest(p), 'bytes':p.stat().st_size} for p in files]
    # Include transformation code and SQL in identity so changed logic produces a new snapshot.
    code = [Path(__file__), ROOT/'sql/shared/historical.sql']
    identity = hashlib.sha256(json.dumps(entries, sort_keys=True).encode() + b''.join(p.read_bytes() for p in code)).hexdigest()
    snapshot_id = VERSION + '-' + identity[:16]
    parent = root/'warehouse/snapshots'; parent.mkdir(parents=True, exist_ok=True)
    target = parent/snapshot_id
    if target.exists():
        verify(target)
    else:
        temp = Path(tempfile.mkdtemp(prefix='.building-', dir=parent))
        try:
            for d in ['raw','staging','core','investigation']: (temp/d).mkdir()
            shutil.copytree(source, temp/'raw', dirs_exist_ok=True)
            c = duckdb.connect()
            counts = {}
            for kind in ['bills','actions']:
                tables = []
                for congress in range(113,119):
                    name = f'{kind}_{congress}'
                    p = temp/'raw/data'/f'{name}.csv'
                    c.execute(f"CREATE TABLE {name} AS SELECT *, row_number() OVER () AS source_row, {quote('data/'+name+'.csv')} AS source_file FROM read_csv({quote(p)}, header=true, all_varchar=true, nullstr='__BTB_RESERVED_NULL__')")
                    c.execute(f"COPY {name} TO {quote(temp/'staging'/f'{name}.parquet')} (FORMAT PARQUET, COMPRESSION ZSTD)")
                    tables.append(name)
                c.execute(f"CREATE TABLE raw_{kind} AS " + ' UNION ALL '.join('SELECT * FROM '+t for t in tables))
                counts[kind] = c.execute(f'SELECT count(*) FROM raw_{kind}').fetchone()[0]
            c.execute((ROOT/'sql/shared/historical.sql').read_text())
            check(c, "SELECT count(*) FROM (SELECT bill_id FROM bills GROUP BY bill_id HAVING count(*)<>1)", 'Duplicate bill IDs')
            check(c, "SELECT count(*) FROM bills WHERE bill_id IS NULL OR introduced_date IS NULL OR congress NOT BETWEEN 113 AND 118 OR bill_type NOT IN ('hr','s','hjres','sjres')", 'Invalid bill keys/dates/types')
            check(c, "SELECT count(*) FROM actions a LEFT JOIN bills b USING(bill_id) WHERE b.bill_id IS NULL OR a.action_date IS NULL", 'Invalid action dates or orphan actions')
            pre_introduction = c.execute("SELECT count(*) FROM actions a JOIN bills b USING(bill_id) WHERE a.action_date < b.introduced_date").fetchone()[0]
            check(c, "SELECT count(*) FROM raw_bills WHERE (introduced<>'' AND try_cast(introduced AS DATE) IS NULL) OR (became_law<>'' AND try_cast(became_law AS DATE) IS NULL)", 'Invalid source dates')
            date_columns = ['introduced','committee_action','reported','committee_discharged','ordered_reported','committee_hearing','committee_markup','subcommittee_reported','passed_house','passed_senate','vetoed','became_law']
            for column in date_columns:
                check(c, f"SELECT count(*) FROM raw_bills WHERE {column}<>'' AND try_cast({column} AS DATE) IS NULL", f'Invalid {column} date')
            check(c, "SELECT count(*) FROM raw_bills WHERE measure_id <> congress || '-' || lower(replace(measure,' ','')) OR try_cast(cosponsors AS INTEGER) IS NULL OR try_cast(original_cosponsors AS INTEGER) IS NULL", 'Invalid bill identity/counts')
            # The supplied combined file must exactly equal the per-Congress population, including all source columns.
            cols = [d[0] for d in c.execute('SELECT * FROM raw_bills LIMIT 0').description][:-2]
            selection = ','.join('"'+x+'"' for x in cols)
            c.execute(f"CREATE TABLE combined AS SELECT * FROM read_csv({quote(temp/'raw/data/bills_2013_2024.csv')},header=true,all_varchar=true,nullstr='__BTB_RESERVED_NULL__')")
            for left,right in [('raw_bills','combined'),('combined','raw_bills')]:
                check(c, f'SELECT count(*) FROM (SELECT {selection} FROM {left} EXCEPT ALL SELECT {selection} FROM {right})', 'Combined/per-Congress mismatch')
            if counts != {'bills':76867,'actions':401161}: raise ValueError(f'Reference count mismatch: {counts}')
            report = {'counts':counts, 'reference_counts_match':True, 'orphan_actions':0, 'pre_introduction_actions_retained':pre_introduction, 'missing_sponsor_ids':c.execute("SELECT count(*) FROM bills WHERE sponsor_id IS NULL").fetchone()[0]}
            for table in ['bills','actions','historical_bill_features','outcomes']:
                c.execute(f"COPY (SELECT * FROM {table} ORDER BY ALL) TO {quote(temp/'core'/f'{table}.parquet')} (FORMAT PARQUET, COMPRESSION ZSTD)")
            c.execute(f"COPY (SELECT * FROM outcomes ORDER BY congress,outcome) TO {quote(temp/'investigation/outcomes.csv')} (HEADER,FORMAT CSV)")
            result = c.execute('SELECT * FROM outcomes ORDER BY congress,outcome')
            names = [x[0] for x in result.description]
            (temp/'investigation/outcomes.json').write_text(json.dumps([dict(zip(names,r)) for r in result.fetchall()],indent=2)+'\n')
            c.execute(f"COPY (SELECT a.*, b.introduced_date FROM actions a JOIN bills b USING(bill_id) WHERE a.action_date < b.introduced_date ORDER BY bill_id,action_date,action_id) TO {quote(temp/'investigation/pre_introduction_actions.csv')} (HEADER, FORMAT CSV)")
            report['introduction_date_range'] = [str(x) for x in c.execute('SELECT min(introduced_date),max(introduced_date) FROM bills').fetchone()]
            report['action_date_range'] = [str(x) for x in c.execute('SELECT min(action_date),max(action_date) FROM actions').fetchone()]
            report['duplicate_action_payloads_retained'] = c.execute('SELECT coalesce(sum(n-1),0) FROM (SELECT count(*) n FROM raw_actions GROUP BY congress,measure,action_date,action_code,action_type,source_system,action_text)').fetchone()[0]
            c.close()
            (temp/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
            artifacts = [{'path':str(p.relative_to(temp)),'sha256':digest(p),'bytes':p.stat().st_size} for p in sorted(temp.rglob('*')) if p.is_file()]
            manifest = {'snapshot_id':snapshot_id,'pipeline_version':VERSION,'created_utc':datetime.now(timezone.utc).isoformat(),'source_url':SOURCE_URL,'source_files':entries,'artifacts':artifacts,'scope':'113–118 Congresses; HR, S, HJRES, SJRES; standardized historical reconstruction','limitations':['Source CSVs contain aggregate cosponsor counts, not individual cosponsorships; votes, amendments, committee membership and text versions are unavailable in this archive.','Rebuilt historical classification differs from original 118th publication: see raw/data/118_published_reconciliation.csv.','Raw GovInfo XML archives are referenced by upstream hashes but are not included in this source bundle.']}
            (temp/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
            verify(temp)
            os.rename(temp,target)
        except BaseException:
            shutil.rmtree(temp,ignore_errors=True)
            raise
    pointer = root/'warehouse/current.json'
    staging = pointer.with_suffix('.tmp')
    staging.write_text(json.dumps({'snapshot_id':snapshot_id},indent=2)+'\n'); os.replace(staging,pointer)
    print(target)
    return target

def verify(path):
    path = Path(path)
    m = json.loads((path/'manifest.json').read_text())
    for a in m['artifacts']:
        p = path/a['path']
        if not p.is_file() or p.stat().st_size != a['bytes'] or digest(p) != a['sha256']: raise ValueError(f'Artifact damaged: {p}')
    return m

if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('source',nargs='?',default=str(ROOT/'imports/original_historical')); p.add_argument('--verify',type=Path)
    a = p.parse_args()
    if a.verify: verify(a.verify); print('All artifact hashes verified')
    else: build(a.source)
