"""Shared helpers: paths, hashing, JSON IO, timestamps."""
import datetime as dt
import hashlib
import json
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
    return "%s-%s-%s" % (prefix, now().strftime("%Y%m%d-%H%M%S"), question_id)
