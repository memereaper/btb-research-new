#!/usr/bin/env python3
"""Reproduce text-first staging of the cloud handoff's future research CSVs."""
import argparse,csv,json,os,shutil,tempfile
from pathlib import Path
import duckdb
from build_historical import ROOT,digest,quote
from import_csv import ingest
SOURCE='https://drive.google.com/file/d/1IA4azUl7_Scy4_zt7yjT7-DtAeQcZ9bn/view'
def stage(source,cloud=None):
    source=Path(source).resolve()
    tables=sorted((source/'data').glob('*.csv'))
    if len(tables)!=33: raise ValueError(f'Expected 33 supplied future tables, found {len(tables)}')
    target=ROOT/'datasets/bipartisanship-v2'
    if target.exists(): raise ValueError('Publication exists; verify it or choose a new version before replacing')
    target.parent.mkdir(exist_ok=True)
    temp=Path(tempfile.mkdtemp(prefix='.future-',dir=target.parent))
    c=duckdb.connect();catalog=[]
    try:
        (temp/'staging').mkdir();(temp/'methods').mkdir()
        for p in tables:
            staged=ingest(p,SOURCE,'future-'+p.stem.lower())
            parquet=staged/'staging.parquet'
            with p.open(encoding='utf-8-sig',newline='') as f:
                reader=csv.reader(f);header=next(reader);n=sum(1 for _ in reader)
            actual=c.execute('SELECT count(*) FROM read_parquet(?)',[str(parquet)]).fetchone()[0]
            if n!=actual: raise ValueError('CSV count mismatch: '+p.name)
            if cloud:
                cp=Path(cloud)/('future_'+p.stem.lower()+'.parquet')
                # Local adds a source row; compare all original values as multisets to the completed cloud staging.
                columns=','.join('"'+x.replace('"','""')+'"' for x in header)
                a=f'SELECT {columns} FROM read_parquet({quote(parquet)})'
                b=f'SELECT {columns} FROM read_parquet({quote(cp)})'
                for left,right in [(a,b),(b,a)]:
                    if c.execute(f'SELECT count(*) FROM ({left} EXCEPT ALL {right})').fetchone()[0]: raise ValueError('Cloud/local mismatch: '+p.name)
            dest=temp/'staging'/(p.stem+'.parquet');shutil.copy2(parquet,dest)
            catalog.append({'table':p.stem,'rows':n,'columns':header,'source_sha256':digest(p),'parquet_sha256':digest(dest),'path':str(dest.relative_to(temp))})
        for p in source.glob('*.md'): shutil.copy2(p,temp/'methods'/p.name)
        manifest={'version':'bipartisanship-v2','source_url':SOURCE,'tables':catalog,'validation':'33 CSV row counts reconciled independently; cloud Parquet values matched' if cloud else '33 CSV row counts reconciled independently','analytical_status':'staged source extracts; substantive findings not independently recertified','limitations':'No automatic normalization into votes/cosponsorship entity tables; see original source methods and license.'}
        (temp/'catalog.json').write_text(json.dumps(manifest,indent=2)+'\n')
        package={'files':[{'path':str(p.relative_to(temp)),'sha256':digest(p),'bytes':p.stat().st_size} for p in sorted(temp.rglob('*')) if p.is_file()]}
        (temp/'package.json').write_text(json.dumps(package,indent=2)+'\n');os.rename(temp,target)
    except BaseException:
        shutil.rmtree(temp,ignore_errors=True);raise
    finally:c.close()
    print('Staged and reconciled 33 future tables:',target)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('source');p.add_argument('--cloud-staging');a=p.parse_args();stage(a.source,a.cloud_staging)
