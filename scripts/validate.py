#!/usr/bin/env python3
"""Validate that the core warehouse is readable; print real row counts."""
from pathlib import Path
import sys
import duckdb

root = Path(__file__).resolve().parents[1]
files = sorted((root / 'warehouse/core').glob('*.parquet'))
if not files:
    sys.exit('ERROR: no Parquet files found. Run scripts/init_warehouse.py.')
con = duckdb.connect(':memory:')
rows = 0
for path in files:
    try:
        n = con.execute('SELECT COUNT(*) FROM read_parquet(?)', [str(path)]).fetchone()[0]
    except Exception as exc:
        sys.exit(f'ERROR: cannot read {path}: {exc}')
    rows += n
    print(f'{path.stem:24s} {n:>12,} rows')
print(f'\n{len(files)} valid Parquet files, {rows:,} total rows.')
if rows == 0:
    print('SCHEMAS ONLY: Empty starter files; no actual government records imported.')
