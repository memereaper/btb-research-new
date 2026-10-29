"""Identifiers and immutable publication contracts; no credentials in manifests."""

import hashlib, json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RELEASE_RE = re.compile(r"^btb-v1-[0-9a-f]{24}$")
BILL_RE = re.compile(r"^\d{3}-(?:hr|s|hjres|sjres)\d+$")


def canonical(value):
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode()


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def release_id(manifest):
    return "btb-v1-" + hashlib.sha256(canonical(manifest)).hexdigest()[:24]


def checked_release(value):
    if not RELEASE_RE.fullmatch(value):
        raise ValueError("Invalid release identifier")
    return value


def verify_bundle(path):
    path = Path(path)
    manifest = json.loads((path / "manifest.json").read_text())
    rid = release_id(manifest)
    if path.name != rid:
        raise ValueError("Bundle directory and content identity disagree")
    for item in manifest["files"]:
        p = (path / item["path"]).resolve()
        if not p.is_relative_to(path.resolve()) or not p.is_file():
            raise ValueError("Missing or unsafe bundle path")
        if p.stat().st_size != item["bytes"] or digest(p) != item["sha256"]:
            raise ValueError("Bundle integrity failed: " + item["path"])
    return rid, manifest
