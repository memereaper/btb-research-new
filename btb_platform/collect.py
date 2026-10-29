"""Durable orchestration of existing rate-limited public collectors; never promotes website data."""

import fcntl, hashlib, json, re, subprocess, sys, time
from pathlib import Path
from .contracts import ROOT, canonical, digest

SCRIPTS = {
    "billstatus": "collect_pathways.py",
    "house-2024": "collect_house_votes.py",
    "members": "collect_members.py",
    "text-pilot": "collect_text_pilot.py",
}


def atomic(path, value):
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(value, indent=2) + "\n")
    temp.replace(path)


def package_ok(output):
    package = json.loads((output / "package.json").read_text())
    for item in package["files"]:
        p = (output / item["path"]).resolve()
        if (
            not p.is_relative_to(output.resolve())
            or not p.is_file()
            or p.stat().st_size != item["bytes"]
            or digest(p) != item["sha256"]
        ):
            raise ValueError("Collector package failed integrity checks")
    report = json.loads((output / "validation.json").read_text())
    if not all(report.get("checks", {}).values()):
        raise ValueError("Collector validation failed")


def run(plan, state_dir):
    config = json.loads(Path(plan).read_text())
    state_dir = Path(state_dir)
    state_dir.mkdir(parents=True, exist_ok=True)
    with (state_dir / "collection.lock").open("w") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ValueError("Another collection run is active")
        state_path = state_dir / "state.json"
        state = json.loads(state_path.read_text()) if state_path.exists() else {}
        ids = [job["id"] for job in config["jobs"]]
        if len(ids) != len(set(ids)) or any(
            not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,79}", x) for x in ids
        ):
            raise ValueError("Job IDs must be unique safe names")
        for job in config["jobs"]:
            ident = job["id"]
            kind = job["kind"]
            output = (ROOT / job["output"]).resolve()
            if (
                not output.is_relative_to(ROOT / "datasets")
                or output == ROOT / "datasets"
            ):
                raise ValueError("Choose a separate datasets/<release> directory")
            if kind not in SCRIPTS:
                raise ValueError("Unsupported collector")
            fingerprint = hashlib.sha256(canonical(job)).hexdigest()
            if ident in state and state[ident].get("plan_sha256") != fingerprint:
                raise ValueError(
                    "A completed/running job definition changed; use a new job ID and output"
                )
            if output.exists():
                package_ok(output)
                state[ident] = {
                    "status": "complete",
                    "output": str(output.relative_to(ROOT)),
                    "checked_unix": time.time(),
                    "plan_sha256": fingerprint,
                }
                atomic(state_path, state)
                continue
            command = [
                sys.executable,
                str(ROOT / "scripts" / SCRIPTS[kind]),
                "--output",
                str(output),
            ]
            if kind == "billstatus":
                command += ["--congress"] + [str(int(x)) for x in job["congresses"]]
            if kind in ("house-2024", "text-pilot"):
                source = (ROOT / job["status"]).resolve()
                if not source.is_relative_to(ROOT / "datasets"):
                    raise ValueError("Status input must be a versioned dataset")
                package_ok(source)
                command += ["--status", str(source)]
            if job.get("refresh"):
                command += ["--refresh"]
            state[ident] = {
                "status": "running",
                "started_unix": time.time(),
                "plan_sha256": fingerprint,
                "output": str(output.relative_to(ROOT)),
            }
            atomic(state_path, state)
            try:
                with (state_dir / (ident + ".log")).open("w") as log:
                    subprocess.run(
                        command,
                        cwd=ROOT,
                        check=True,
                        stdout=log,
                        stderr=subprocess.STDOUT,
                        timeout=7200,
                    )
                package_ok(output)
                state[ident]["status"] = "complete"
                state[ident]["finished_unix"] = time.time()
                atomic(state_path, state)
            except BaseException:
                state[ident]["status"] = "failed"
                state[ident]["finished_unix"] = time.time()
                atomic(state_path, state)
                raise
        print(json.dumps(state, indent=2))
