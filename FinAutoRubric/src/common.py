"""Shared helpers: paths, hashing, JSON IO, timestamps, manifests."""
import datetime as dt
import hashlib
import json
import secrets
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def sha256_path(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def write_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def now():
    return dt.datetime.now().astimezone()


def iso(moment):
    return moment.isoformat(timespec="seconds")


def new_run_id(prefix, question_id):
    """Include microseconds so two runs in the same second cannot collide."""
    moment = now()
    return "%s-%s-%06d-%s-%s" % (
        prefix,
        moment.strftime("%Y%m%d-%H%M%S"),
        moment.microsecond,
        secrets.token_hex(3),
        question_id,
    )


def file_manifest(root):
    """Size and hash of every file under `root`, relative and sorted."""
    root = Path(root)
    rows = []
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        rows.append(
            {
                "path": path.relative_to(root).as_posix(),
                "bytes": path.stat().st_size,
                "sha256": sha256_path(path),
            }
        )
    return rows
