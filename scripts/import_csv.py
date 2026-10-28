#!/usr/bin/env python3
"""Losslessly stage CSV fields as strings; never infer bill IDs/dates."""
import argparse
from pathlib import Path
import duckdb

root = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument('csv', help='Path to original CSV file')
parser.add_argument('--force', action='store_true', help='Replace staging copy (never source)')
args = parser.parse_args()
src = Path(args.csv).expanduser().resolve()
if not src.is_file() or src.suffix.lower() != '.csv':
    parser.error('Input must be an existing .csv file')
out = root / 'warehouse/staging' / f'{src.stem}.parquet'
out.parent.mkdir(parents=True, exist_ok=True)
if out.exists() and not args.force:
    parser.error(f'{out} exists. Remove it or use --force to rebuild staging only.')
con = duckdb.connect(':memory:')
rel = con.read_csv(str(src), header=True, all_varchar=True)
rel.write_parquet(str(out), compression='zstd')
count = con.execute('SELECT COUNT(*) FROM read_parquet(?)', [str(out)]).fetchone()[0]
print(f'Imported {count:,} rows into {out}')
print('Next: inspect column names and write a source-specific mapping into core tables.')
