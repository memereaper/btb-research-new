#!/usr/bin/env python3
"""Create actual typed, zero-row Parquet files. Safe to rerun."""
from pathlib import Path
import duckdb

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / 'sql/shared/schema.sql'
CORE = ROOT / 'warehouse/core'
CORE.mkdir(parents=True, exist_ok=True)

con = duckdb.connect(':memory:')
con.execute(SCHEMA.read_text(encoding='utf-8'))
tables = [r[0] for r in con.execute('SHOW TABLES').fetchall()]
for name in tables:
    output = CORE / f'{name}.parquet'
    if output.exists():
        print(f'KEEP  {output.relative_to(ROOT)} (already exists)')
        continue
    # write_parquet creates a real, readable file, even for 0 rows.
    con.table(name).limit(0).write_parquet(str(output), compression='zstd')
    print(f'CREATE {output.relative_to(ROOT)} (0 records)')
print(f'\nInitialized {len(tables)} core Parquet schemas. No research data imported.')
