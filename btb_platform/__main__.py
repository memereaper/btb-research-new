import argparse, json
from pathlib import Path


def main():
    p = argparse.ArgumentParser(description="Between the Bills data platform")
    s = p.add_subparsers(dest="command", required=True)
    b = s.add_parser("build")
    b.add_argument("--output", type=Path, default=Path("work/platform/releases"))
    s.add_parser("migrate")
    q = s.add_parser("monitor")
    q.add_argument("base_url")
    q.add_argument("--expected-release")
    q = s.add_parser("backup-db")
    q.add_argument("output", type=Path)
    q = s.add_parser("collect")
    q.add_argument("plan", type=Path)
    q.add_argument(
        "--state-dir", type=Path, default=Path("work/platform/collection-jobs")
    )
    for name in ["load", "archive-plan", "archive-upload"]:
        q = s.add_parser(name)
        q.add_argument("bundle", type=Path)
        if name == "load":
            q.add_argument("--insert-batches", action="store_true")
        if name.startswith("archive-"):
            q.add_argument("--include-raw", action="store_true")
            q.add_argument("--local-dir", type=Path)
    q = s.add_parser("restore-archive")
    q.add_argument("receipt", type=Path)
    q.add_argument("destination", type=Path)
    q.add_argument("--local-dir", type=Path)
    q = s.add_parser("promote")
    q.add_argument("release")
    q.add_argument("--reason", required=True)
    q = s.add_parser("serve")
    q.add_argument("--host", default="127.0.0.1")
    q.add_argument("--port", type=int, default=8787)
    a = p.parse_args()
    if a.command == "build":
        from .build import build

        build(a.output)
    elif a.command == "monitor":
        from .operations import monitor

        monitor(a.base_url, a.expected_release)
    elif a.command == "backup-db":
        from .operations import backup_database

        backup_database(a.output)
    elif a.command == "collect":
        from .collect import run

        run(a.plan, a.state_dir)
    elif a.command in ["migrate", "load", "promote"]:
        from . import db

        if a.command == "migrate":
            db.migrate()
        elif a.command == "load":
            db.load(a.bundle, insert_batches=a.insert_batches)
        else:
            db.promote(a.release, a.reason)
    elif a.command.startswith("archive-"):
        from .storage import archive_plan, upload, LocalObjectStore

        if a.command == "archive-plan":
            plan = archive_plan(a.bundle, a.include_raw)
            print(
                json.dumps({k: v for k, v in plan.items() if k != "objects"}, indent=2)
            )
        else:
            upload(
                a.bundle,
                a.include_raw,
                LocalObjectStore(a.local_dir) if a.local_dir else None,
            )
    elif a.command == "restore-archive":
        from .storage import restore_archive, LocalObjectStore

        restore_archive(
            a.receipt,
            a.destination,
            LocalObjectStore(a.local_dir) if a.local_dir else None,
        )
    else:
        import logging
        import uvicorn

        logging.basicConfig(
            level=logging.INFO, format="%(levelname)s %(name)s %(message)s"
        )
        uvicorn.run(
            "btb_platform.api:create_app",
            factory=True,
            host=a.host,
            port=a.port,
            proxy_headers=False,
            access_log=False,
            log_level="info",
        )


if __name__ == "__main__":
    main()
