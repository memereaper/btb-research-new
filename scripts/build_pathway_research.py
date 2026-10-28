#!/usr/bin/env python3
"""Build checkable research leads from acquired records; no causal labels."""
import json,os,shutil,tempfile
from pathlib import Path
import duckdb
from build_historical import ROOT,digest,quote
from collect_pathways import atomic_json

def build():
    target=ROOT/'datasets/pathway-research-2026-10-28'
    if target.exists():raise ValueError('Choose a new immutable release name')
    work=Path(tempfile.mkdtemp(prefix='.research-',dir=target.parent));(work/'tables').mkdir()
    c=duckdb.connect();c.execute("SET memory_limit='1GB'")
    input_packages={}
    for folder,prefix in [('pathways-2026-10-28','status_'),('house-2024-pathway-votes','house_'),('member-crosswalk-2026-10-28','roster_')]:
        base=ROOT/'datasets'/folder;input_packages[folder]=digest(base/'package.json')
        for p in (base/'tables').glob('*.parquet'):c.read_parquet(str(p)).create_view(prefix+p.stem)
    c.read_parquet(str(ROOT/'datasets/historical-v1/core/historical_bill_features.parquet')).create_view('historical_features_source')
    c.execute('CREATE VIEW historical_features AS SELECT *,measure_id bill_id FROM historical_features_source')
    catalog=[]
    for name in ['reintroduction_candidates','cosponsor_vote_observations']:
        sql=ROOT/'sql/pathways'/(name+'.sql');c.execute(f'CREATE TABLE {name} AS '+sql.read_text())
        c.execute(f'COPY {name} TO {quote(work/"tables"/(name+".parquet"))} (FORMAT PARQUET,COMPRESSION ZSTD)')
        catalog.append({'table':name,'rows':c.execute(f'SELECT count(*) FROM {name}').fetchone()[0],'fields':[d[0] for d in c.execute(f'SELECT * FROM {name} LIMIT 0').description],'sql_sha256':digest(sql)})
    coverage={
      'unmatched_bill_sponsor_ids':c.execute("SELECT count(*) FROM status_bills b ANTI JOIN roster_members m ON b.sponsor_id=m.member_id").fetchone()[0],
      'unmatched_unique_cosponsor_ids':c.execute("SELECT count(*) FROM (SELECT DISTINCT sponsor_id FROM status_cosponsors) b ANTI JOIN roster_members m ON b.sponsor_id=m.member_id").fetchone()[0],
      'unmatched_unique_house_member_ids':c.execute("SELECT count(*) FROM (SELECT DISTINCT member_id FROM house_positions) p ANTI JOIN roster_members m USING(member_id)").fetchone()[0],
      'original_118_bill_ids_missing_from_new_snapshot':c.execute("SELECT count(*) FROM historical_features h ANTI JOIN status_bills b USING(bill_id) WHERE h.congress='118'").fetchone()[0],
      'new_118_bill_ids_absent_from_original':c.execute("SELECT count(*) FROM status_bills b ANTI JOIN historical_features h USING(bill_id) WHERE b.congress='118'").fetchone()[0],
      'original_vs_new_118_introduction_differences':c.execute("SELECT count(*) FROM status_bills b JOIN historical_features h USING(bill_id) WHERE b.congress='118' AND b.introduced_date<>h.introduced").fetchone()[0]
    }
    if any(coverage.values()):raise ValueError('Review uncovered joins/reconciliation before publishing: '+str(coverage))
    timings=dict(c.execute('SELECT timing_status,count(*) FROM cosponsor_vote_observations GROUP BY 1').fetchall())
    atomic_json(work/'catalog.json',{'tables':catalog,'input_package_sha256':input_packages,'original_historical_features_sha256':digest(ROOT/'datasets/historical-v1/core/historical_bill_features.parquet'),'limitations':['Recurrence candidates are title/sponsor rules; titles can be generic and similarity is not proof of policy identity.','Cosponsor observations cover only acquired 2024 House bill-linked votes, not every vote, every cosponsor or the Senate.','Date-only same-day order is ambiguous; source party labels are retained, not backfilled as historical affiliations.','Committee activity and text matches do not identify causation.']})
    atomic_json(work/'validation.json',{'join_coverage':coverage,'timing_categories':timings,'checks':{'all_identity_joins_matched':True,'original_118_population_and_introductions_preserved':True}})
    c.close();atomic_json(work/'package.json',{'files':[{'path':str(p.relative_to(work)),'bytes':p.stat().st_size,'sha256':digest(p)} for p in sorted(work.rglob('*')) if p.is_file()]});os.rename(work,target)
    print('Built research leads',catalog,coverage,timings)
if __name__=='__main__':build()
