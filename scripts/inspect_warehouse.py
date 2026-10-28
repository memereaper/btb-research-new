#!/usr/bin/env python3
"""Inspect a Parquet file without loading the whole dataset into Python."""
import argparse
from pathlib import Path
import duckdb

p = argparse.ArgumentParser()
p.add_argument('file', help='Path to .parquet')
a = p.parse_args()
f = Path(a.file).expanduser().resolve()
if not f.is_file():
    p.error(f'File does not exist: {f}')
con = duckdb.connect(':memory:')
print(f'Rows: {con.execute("SELECT COUNT(*) FROM read_parquet(?)", [str(f)]).fetchone()[0]:,}')
for name, kind, *_ in con.execute('DESCRIBE SELECT * FROM read_parquet(?)', [str(f)]).fetchall():
    print(f'  {name}: {kind}')
