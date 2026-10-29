"""S3-compatible content-addressed archive with resumable uploads and restore verification."""

import json, mimetypes, os
from pathlib import Path
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
from .contracts import ROOT, canonical, digest, verify_bundle


class ObjectStore:
    def __init__(self, bucket=None, client=None):
        self.bucket = bucket or os.environ["BTB_ARCHIVE_BUCKET"]
        endpoint = os.getenv("BTB_S3_ENDPOINT")
        if (
            endpoint
            and not endpoint.startswith("https://")
            and os.getenv("BTB_ALLOW_LOCAL_S3") != "1"
        ):
            raise ValueError("Object storage requires HTTPS")
        self.client = client or boto3.client(
            "s3",
            endpoint_url=endpoint,
            region_name=os.getenv("AWS_DEFAULT_REGION", "auto"),
            config=Config(
                retries={"max_attempts": 5, "mode": "standard"},
                connect_timeout=10,
                read_timeout=60,
                request_checksum_calculation="when_required",
                response_checksum_validation="when_required",
            ),
        )

    def put(self, path, key, sha=None):
        path = Path(path)
        sha = sha or digest(path)
        try:
            head = self.client.head_object(Bucket=self.bucket, Key=key)
            if (
                head["ContentLength"] != path.stat().st_size
                or head.get("Metadata", {}).get("sha256") != sha
            ):
                raise ValueError("Remote immutable object conflicts: " + key)
            return "reused"
        except ClientError as e:
            if e.response["Error"]["Code"] not in ("404", "NoSuchKey", "NotFound"):
                raise
        self.client.upload_file(
            str(path),
            self.bucket,
            key,
            ExtraArgs={
                "Metadata": {"sha256": sha},
                "ContentType": mimetypes.guess_type(str(path))[0]
                or "application/octet-stream",
                "CacheControl": "public, max-age=31536000, immutable",
            },
        )
        head = self.client.head_object(Bucket=self.bucket, Key=key)
        if (
            head["ContentLength"] != path.stat().st_size
            or head.get("Metadata", {}).get("sha256") != sha
        ):
            raise ValueError("Upload verification failed")
        return "uploaded"

    def restore(self, key, path, sha):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_name(path.name + ".restore-part")
        if path.exists():
            if digest(path) == sha:
                return
            raise ValueError("Restore refuses to replace a different local file")
        try:
            self.client.download_file(self.bucket, key, str(temp))
            if digest(temp) != sha:
                raise ValueError("Restored bytes do not match SHA-256")
            temp.replace(path)
        finally:
            temp.unlink(missing_ok=True)


def archive_plan(bundle, include_raw=False):
    rid, m = verify_bundle(bundle)
    bundle = Path(bundle)
    objects = {}

    def add(p, expected=None):
        sha = digest(p)
        if expected and sha != expected:
            raise ValueError("Source changed after release build")
        objects[sha] = {
            "local": str(p),
            "key": "objects/sha256/" + sha,
            "sha256": sha,
            "bytes": p.stat().st_size,
        }

    for item in m["files"]:
        add(bundle / item["path"], item["sha256"])
    for item in m["source_files"]:
        p = ROOT / item["path"]
        if not p.is_file():
            raise ValueError("Source package is unavailable")
        add(p, item["sha256"])
    packages = json.loads((bundle / "catalog/research-packages.json").read_text())
    for package in packages:
        for item in package["files"]:
            add(ROOT / item["path"], item["sha256"])
    if include_raw:
        raw_roots = [
            ROOT / "warehouse/collection-cache",
            ROOT / "warehouse/snapshots" / m["source_snapshot"] / "raw",
        ]
        if not raw_roots[1].is_dir():
            raise ValueError(
                "Original historical raw snapshot is missing; refuse incomplete raw backup"
            )
        for p in sorted(p for root in raw_roots for p in root.rglob("*")):
            if p.is_file() and "pending" not in p.parts:
                add(p)
    add(bundle / "manifest.json")
    return {
        "release_id": rid,
        "object_count": len(objects),
        "bytes": sum(x["bytes"] for x in objects.values()),
        "objects": list(objects.values()),
    }


def upload(bundle, include_raw=False, store=None):
    plan = archive_plan(bundle, include_raw)
    store = store or ObjectStore()
    counts = {"uploaded": 0, "reused": 0}
    for item in plan["objects"]:
        counts[store.put(item["local"], item["key"], item["sha256"])] += 1
    # Upload a recoverable inventory without machine-local paths, then the immutable release manifest last.
    rid = plan["release_id"]
    receipt = {k: v for k, v in plan.items() if k != "objects"}
    receipt["objects"] = [
        {k: v for k, v in x.items() if k != "local"} for x in plan["objects"]
    ]
    receipt_path = Path(bundle) / "archive-receipt.json"
    receipt_path.write_bytes(canonical(receipt))
    store.put(
        receipt_path, "releases/" + rid + "/archives/" + digest(receipt_path) + ".json"
    )
    store.put(Path(bundle) / "manifest.json", "releases/" + rid + "/manifest.json")
    print(
        json.dumps(
            {
                "release_id": rid,
                **counts,
                "verified_objects": plan["object_count"],
                "bytes": plan["bytes"],
            }
        )
    )
    return receipt


def restore_archive(receipt_path, destination, store=None):
    receipt = json.loads(Path(receipt_path).read_text())
    store = store or ObjectStore()
    destination = Path(destination)
    for item in receipt["objects"]:
        if (
            item["key"] != "objects/sha256/" + item["sha256"]
            or len(item["sha256"]) != 64
            or any(x not in "0123456789abcdef" for x in item["sha256"])
        ):
            raise ValueError("Invalid archive receipt")
        store.restore(item["key"], destination / item["sha256"], item["sha256"])
    print("Restored and hashed", len(receipt["objects"]), "objects")


class LocalObjectStore:
    """Filesystem adapter for offline backup/restore drills; not an independent cloud backup."""

    def __init__(self, root):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, key):
        p = (self.root / key).resolve()
        if not p.is_relative_to(self.root):
            raise ValueError("Unsafe object key")
        return p

    def put(self, path, key, sha=None):
        import tempfile, shutil

        path = Path(path)
        sha = sha or digest(path)
        target = self._path(key)
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            if digest(target) != sha:
                raise ValueError("Immutable local object conflict")
            return "reused"
        fd, name = tempfile.mkstemp(dir=target.parent, prefix=".upload-")
        os.close(fd)
        temp = Path(name)
        try:
            shutil.copyfile(path, temp)
            if digest(temp) != sha:
                raise ValueError("Source changed during local upload")
            try:
                os.link(temp, target)
            except FileExistsError:
                if digest(target) != sha:
                    raise ValueError("Immutable local object conflict")
            return "uploaded"
        finally:
            temp.unlink(missing_ok=True)

    def restore(self, key, path, sha):
        import shutil

        source = self._path(key)
        if digest(source) != sha:
            raise ValueError("Archive corruption")
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            if digest(path) == sha:
                return
            raise ValueError("Restore conflict")
        shutil.copyfile(source, path)
        if digest(path) != sha:
            raise ValueError("Restore corruption")
