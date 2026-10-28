# Between the Bills Research Warehouse

A local-first research system built around DuckDB, Parquet, SQL, and Python. Read [CLAUDE.md](CLAUDE.md) before changing the data model or generating research outputs. It records the project mission, research standards, build sequence, and the rule that the live WordPress site stays untouched until Abhay reviews and approves a tested deployment.

## Current state

This repository is a starter scaffold. The `warehouse/core/*.parquet` files are valid typed schemas with zero rows. `imports/` and `warehouse/raw/` contain no source records. The SQL and methodology under `investigations/where-bills-go-to-die/` are placeholders, not the original investigation's validated methods or findings.

The first published investigation has been described as covering 76,867 bills and approximately 401,161 legislative actions from the 113th through 118th Congresses (2013–2024). Those are targets to reconcile against the original files, not verified totals in this warehouse. Do not publish the scaffold's outputs as research results.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python scripts/validate.py
```

To stage an original CSV without inferring or changing its values:

```bash
python scripts/import_csv.py /path/to/original.csv
python scripts/inspect_warehouse.py warehouse/staging/original.parquet
```

Staging preserves imported columns as text. It does not populate normalized core tables. Source-specific mappings, provenance, and checks must be implemented before core data or publication bundles are generated.

## Layout

- `imports/`: original downloaded files and exports, preserved as supplied
- `warehouse/raw/`: archived source files and metadata
- `warehouse/staging/`: lossless, text-first source copies in Parquet
- `warehouse/core/`: normalized, validated analytical tables in Parquet
- `sql/shared/`: reusable schema and transformation logic
- `investigations/<slug>/queries/`: versioned investigation SQL
- `investigations/<slug>/methodology.md`: definitions, sources, exclusions, checks, and caveats
- `investigations/<slug>/outputs/`: generated local outputs
- `releases/`: validated, versioned publication bundles with manifests

Preserve raw sources and existing work. Never commit credentials or publish data without checking terms and attribution. The research pipeline must run and validate locally before any separate website integration work.
