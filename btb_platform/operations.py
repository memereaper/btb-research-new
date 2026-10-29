"""On-demand checks and database backup jobs; no notification transmission."""

import json, os, subprocess, time
from pathlib import Path
import httpx
from .contracts import digest


def monitor(base, expected_release=None):
    if not base.startswith("https://") and not base.startswith("http://127.0.0.1:"):
        raise ValueError("Production checks require HTTPS")
    results = {}
    with httpx.Client(timeout=10, follow_redirects=False) as c:
        for name, path in [
            ("readiness", "/health/ready"),
            ("investigation", "/v1/investigations/where-bills-go-to-die"),
        ]:
            start = time.perf_counter()
            r = c.get(base.rstrip("/") + path)
            r.raise_for_status()
            data = r.json()
            if (
                name == "investigation"
                and expected_release
                and data["release_id"] != expected_release
            ):
                raise ValueError("Unexpected published release")
            results[name] = {
                "status": r.status_code,
                "milliseconds": round((time.perf_counter() - start) * 1000, 2),
                "response_bytes": len(r.content),
            }
    print(json.dumps(results, indent=2))
    return results


def backup_database(output, store=None):
    from .storage import ObjectStore

    path = Path(output)
    if path.exists():
        raise ValueError("Choose a new backup filename")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".part")
    env = dict(os.environ)
    env["PGDATABASE"] = env["BTB_ADMIN_DATABASE_URL"]
    # URL is supplied in the environment, never printed or embedded in the process argument list.
    try:
        subprocess.run(
            ["pg_dump", "--format=custom", "--no-owner", "--file", str(temporary)],
            env=env,
            check=True,
            capture_output=True,
        )
        temporary.chmod(0o600)
        temporary.replace(path)
        sha = digest(path)
        (store or ObjectStore()).put(path, "database-backups/sha256/" + sha, sha)
        print(
            json.dumps(
                {"backup": path.name, "sha256": sha, "bytes": path.stat().st_size}
            )
        )
    finally:
        temporary.unlink(missing_ok=True)
