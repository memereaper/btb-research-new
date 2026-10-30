#!/usr/bin/env python3
"""Direct SQL over new collections, with explicit source prefixes."""
import argparse
from pathlib import Path
import duckdb
from build_historical import ROOT
from verify_collections import verify
p=argparse.ArgumentParser();p.add_argument('--sql');p.add_argument('--file',type=Path);a=p.parse_args()
verify();c=duckdb.connect()
for name,prefix in [('pathways-2026-10-28','status_'),('pathways-116-117-2026-10-29','status116_'),('house-2024-pathway-votes','house_'),('member-crosswalk-2026-10-28','roster_'),('text-survival-pilot-2026-10-28','text_'),('pathway-research-2026-10-28','research_')]:
    for f in (ROOT/'datasets'/name/'tables').glob('*.parquet'):c.read_parquet(str(f)).create_view(prefix+f.stem)
sql=a.file.read_text() if a.file else a.sql
if not sql:p.error('--sql or --file is required')
r=c.execute(sql);print([d[0] for d in r.description]);print(*r.fetchall(),sep='\n')
