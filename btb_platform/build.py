"""Build serving data and a content-addressed archive from verified research inputs."""

import json, os, shutil, tempfile
from pathlib import Path
import duckdb
from .contracts import ROOT, canonical, digest, release_id
from . import VERSION


def build(output, source=None):
    source = Path(source or ROOT / "datasets/historical-v1").resolve()
    # Reuse the historical publication verifier; never silently substitute newer status.
    import sys

    sys.path.insert(0, str(ROOT / "scripts"))
    from verify_publication import verify_publication

    verify_publication(source)
    import runpy
    from verify_collections import verify as verify_collections

    runpy.run_path(str(ROOT / "scripts/verify_future.py"))
    verify_collections()
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix=".build-", dir=output))
    try:
        inputs = []
        for p in sorted(source.rglob("*")):
            if p.is_file():
                inputs.append(
                    {
                        "path": str(p.relative_to(ROOT))
                        if p.is_relative_to(ROOT)
                        else p.name,
                        "sha256": digest(p),
                        "bytes": p.stat().st_size,
                    }
                )
        c = duckdb.connect()
        c.execute("SET memory_limit='1GB'")
        c.execute("SET threads=1")
        c.execute("SET preserve_insertion_order=true")
        c.read_parquet(str(source / "core/bills.parquet")).create_view("raw_bills")
        c.read_parquet(str(source / "core/actions.parquet")).create_view("raw_actions")
        c.read_parquet(
            str(source / "core/historical_bill_features.parquet")
        ).create_view("features")
        if (
            c.execute("SELECT count(*) FROM features").fetchone()[0] != 76867
            or c.execute("SELECT count(DISTINCT measure_id) FROM features").fetchone()[
                0
            ]
            != 76867
        ):
            raise ValueError("Invalid features population")
        c.execute("""CREATE TABLE bills AS SELECT b.*, coalesce(f.policy_area,'') policy_area,
        CASE WHEN b.bill_type IN ('s','sjres') THEN 'senate' ELSE 'house' END chamber,
        CASE f.bipartisan_at_introduction WHEN 'yes' THEN true WHEN 'no' THEN false ELSE NULL END bipartisan,
        nullif(f.sponsor_party,'') sponsor_party, nullif(f.sponsor_state,'') sponsor_state
        FROM raw_bills b JOIN features f ON b.bill_id=f.measure_id""")
        if c.execute("SELECT count(*) FROM bills").fetchone()[0] != 76867:
            raise ValueError("Bill join lost records")
        serving = work / "serving"
        serving.mkdir()
        for table, sql in [
            ("bills", "SELECT * FROM bills ORDER BY congress,bill_id"),
            (
                "actions",
                "SELECT * FROM raw_actions ORDER BY bill_id,sequence_number,action_id",
            ),
            (
                "summary_cells",
                "SELECT congress,chamber,policy_area,outcome,CASE WHEN bipartisan THEN 'yes' WHEN NOT bipartisan THEN 'no' ELSE 'unknown' END bipartisan,count(*)::BIGINT bill_count FROM bills GROUP BY ALL ORDER BY ALL",
            ),
        ]:
            c.execute(
                f"COPY ({sql}) TO ? (FORMAT PARQUET,COMPRESSION ZSTD)",
                [str(serving / (table + ".parquet"))],
            )
        # Partition the complete research core by Congress; website requests never scan this archive.
        (work / "research").mkdir()
        for name in ["bills", "actions"]:
            if name == "bills":
                query = "SELECT * FROM bills ORDER BY congress,bill_id"
            else:
                query = "SELECT a.*,b.congress FROM raw_actions a JOIN bills b USING(bill_id) ORDER BY congress,bill_id,sequence_number,action_id"
            c.execute(
                f"COPY ({query}) TO ? (FORMAT PARQUET,COMPRESSION ZSTD,PARTITION_BY(congress),ROW_GROUP_SIZE 100000)",
                [str(work / "research" / name)],
            )
        c.close()
        # All other packages remain independently versioned, including their caveats and methods.
        packages = []
        archive = work / "catalog"
        archive.mkdir()
        for package in sorted((ROOT / "datasets").iterdir()):
            if not package.is_dir():
                continue
            entries = []
            for p in sorted(package.rglob("*")):
                if p.is_file():
                    entries.append(
                        {
                            "path": str(p.relative_to(ROOT)),
                            "sha256": digest(p),
                            "bytes": p.stat().st_size,
                        }
                    )
            packages.append({"package": package.name, "files": entries})
        (archive / "research-packages.json").write_bytes(canonical(packages))
        # Preserve the exact transformation/runtime sources, not just a Git branch name.
        code_roots = ["btb_platform", "scripts", "sql", "docs/platform"]
        code_files = [
            p
            for name in code_roots
            for p in (ROOT / name).rglob("*")
            if p.is_file() and p.suffix in (".py", ".sql", ".md")
        ]
        code_files += [
            ROOT / name
            for name in [
                "requirements.txt",
                "requirements-platform.txt",
                "requirements-platform.lock",
            ]
        ]
        for p in sorted(code_files):
            target = work / "reproducibility" / p.relative_to(ROOT)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(p, target)
        manifest = {
            "schema_version": 1,
            "builder_version": VERSION,
            "builder_sha256": digest(Path(__file__)),
            "investigation": "where-bills-go-to-die",
            "source_snapshot": json.loads((source / "package.json").read_text())[
                "snapshot_id"
            ],
            "coverage": {
                "congresses": [113, 114, 115, 116, 117, 118],
                "bills": 76867,
                "actions": 401161,
                "completed_only": True,
            },
            "source_files": inputs,
            "limits": [
                "Historical release is frozen; newer 118/119 data remains a separate collection.",
                "11 missing sponsor IDs; 568 pre-introduction actions retained.",
                "Candidate reintroductions and passage matches are not verified findings.",
            ],
            "files": [
                {
                    "path": str(p.relative_to(work)),
                    "sha256": digest(p),
                    "bytes": p.stat().st_size,
                }
                for p in sorted(work.rglob("*"))
                if p.is_file()
            ],
        }
        rid = release_id(manifest)
        (work / "manifest.json").write_bytes(canonical(manifest))
        target = output / rid
        if target.exists():
            from .contracts import verify_bundle

            verify_bundle(target)
            shutil.rmtree(work)
        else:
            os.rename(work, target)
        print(target)
        return target
    except BaseException:
        shutil.rmtree(work, ignore_errors=True)
        raise
