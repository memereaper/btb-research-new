#!/usr/bin/env python3
"""Produce small, versioned-ready JSON results from cleaned core data."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import duckdb

root = Path(__file__).resolve().parents[1]
p = argparse.ArgumentParser()
p.add_argument('investigation', choices=['where-bills-go-to-die'])
a = p.parse_args()
base = root / 'investigations' / a.investigation
con = duckdb.connect(':memory:')
# Empty schema files are NOT published as if they were real findings.
total = con.execute('SELECT COUNT(*) FROM read_parquet(?)',
                    [str(root / 'warehouse/core/bills.parquet')]).fetchone()[0]
if not total:
    p.error('Core bills.parquet is empty. Import + validate + map the real data first.')
query = (base / 'queries/02_outcomes.sql').read_text(encoding='utf-8')
# SQL filenames use project-relative paths.
import os
os.chdir(root)
result = con.execute(query)
cols = [d[0] for d in result.description]
records = [dict(zip(cols, row)) for row in result.fetchall()]
out = base / 'outputs'
out.mkdir(parents=True, exist_ok=True)
(out / 'overview.json').write_text(json.dumps({
    'generated_at': datetime.now(timezone.utc).isoformat(),
    'total_bills': total,
    'schema_version': 1,
}, indent=2) + '\n', encoding='utf-8')
(out / 'charts.json').write_text(json.dumps({'outcomes_by_congress': records},
                                        indent=2) + '\n', encoding='utf-8')
print(f'Wrote investigation JSON outputs for {total:,} bill records. NOT deployed.')
