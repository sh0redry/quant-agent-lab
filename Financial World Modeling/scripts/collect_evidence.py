"""Capture immutable source identities, file inventory and paper text for review."""
import ctypes
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
REF = ROOT / "references"
RESULTS = ROOT / "results"


def git(path, *args):
    return subprocess.check_output(["git", "-c", f"safe.directory={path.resolve().as_posix()}", "-C", str(path), *args], encoding="utf-8").strip()


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    REF.mkdir(exist_ok=True)
    RESULTS.mkdir(exist_ok=True)
    repos = {}
    for name, relative in [("tfwm", "tfwm"), ("market-1t", "market-1t"),
                           ("stable-finance", "tfwm/stable-finance")]:
        path = ROOT / "external" / relative
        files = git(path, "ls-files").splitlines()
        repos[name] = {"url": git(path, "remote", "get-url", "origin"),
                       "commit": git(path, "rev-parse", "HEAD"),
                       "commit_date": git(path, "show", "-s", "--format=%cI", "HEAD"),
                       "submodules": git(path, "submodule", "status", "--recursive"),
                       "status": git(path, "status", "--short"), "files": []}
        for file in files:
            full = path / file
            if full.is_file():
                repos[name]["files"].append({"path": file, "size": full.stat().st_size,
                    "sha256": hashlib.sha256(full.read_bytes()).hexdigest()})
        snap = REF / "upstream" / name
        snap.mkdir(parents=True, exist_ok=True)
        for filename in ["README.md", "LICENSE", "pyproject.toml", ".python-version", ".gitmodules"]:
            if (path / filename).is_file():
                shutil.copyfile(path / filename, snap / filename)
    paper = ROOT / "2610.09048v2.pdf"
    from pypdf import PdfReader
    reader = PdfReader(paper)
    pages = [{"page": i + 1, "text": page.extract_text()} for i, page in enumerate(reader.pages)]
    (REF / "paper-pages.json").write_text(json.dumps(pages, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (REF / "paper-extracted.txt").write_text("\n\n".join(f"=== PAGE {p['page']} ===\n{p['text']}" for p in pages), encoding="utf-8")
    class Memory(ctypes.Structure):
        _fields_ = [("length", ctypes.c_ulong), ("load", ctypes.c_ulong)] + [
            (key, ctypes.c_ulonglong) for key in ["total", "available", "page_total", "page_available", "virtual_total", "virtual_available", "extended"]]
    memory = Memory()
    memory.length = ctypes.sizeof(memory)
    ok = ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(memory))
    hardware = {"platform": platform.platform(), "logical_cpus": os.cpu_count(),
                "memory_query_ok": bool(ok), "memory_total_bytes": memory.total,
                "memory_available_bytes": memory.available,
                "disk": {drive: dict(zip(["total", "used", "free"], shutil.disk_usage(drive))) for drive in ["C:/", "D:/"]},
                "gpu": subprocess.check_output(["nvidia-smi", "--query-gpu=name,memory.total,driver_version", "--format=csv"], encoding="utf-8").strip()}
    manifest = {"recorded_at": dt.datetime.now(dt.timezone(dt.timedelta(hours=8))).isoformat(),
                "baseline_commit": git(ROOT.parent, "rev-parse", "HEAD"),
                "paper": {"file": paper.name, "version": "arXiv:2610.09048v2", "pages": len(pages),
                    "sha256": hashlib.sha256(paper.read_bytes()).hexdigest()},
                "repositories": repos, "hardware": hardware}
    (RESULTS / "source_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"paper": manifest["paper"], "hardware": hardware,
          "repositories": {k: {x: v[x] for x in ["commit", "status", "submodules"]} for k, v in repos.items()}}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
