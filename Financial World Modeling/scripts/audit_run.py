"""Run an audit command and retain command, timestamps, exit code and output.

Usage: python scripts/audit_run.py LABEL --cwd DIRECTORY -- COMMAND [ARG ...]
Outputs are UTF-8 and paths in the manifest are relative to the TFWM directory.
"""
import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "results" / "runs" / "2026-10-22-stage1-2-r0"


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    split = sys.argv.index("--")
    parser = argparse.ArgumentParser()
    parser.add_argument("label")
    parser.add_argument("--cwd", default=str(ROOT))
    parser.add_argument("--cpu", action="store_true", help="Use isolated CPU torch overlay for R0 only")
    args = parser.parse_args(sys.argv[1:split])
    command = sys.argv[split + 1:]
    executable = Path(args.cwd).resolve() / command[0]
    if executable.is_file():
        command[0] = str(executable)
    RUN.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now(dt.timezone(dt.timedelta(hours=8)))
    name = f"{stamp:%Y%m%d-%H%M%S-%f}-{args.label}"
    output = RUN / f"{name}.txt"
    env = os.environ.copy()
    env.update({"PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8", "PYTHONPATH": str(Path(args.cwd).resolve()),
                "UV_CACHE_DIR": str(ROOT / ".cache" / "uv"),
                "UV_PYTHON_INSTALL_DIR": str(ROOT / ".tools" / "python"),
                "UV_NO_PROGRESS": "1", "HF_HUB_DISABLE_PROGRESS_BARS": "1"})
    if args.cpu:
        env.update({"PYTHONPATH": os.pathsep.join([str(ROOT / ".tools" / "cpu-torch"), str(Path(args.cwd).resolve())]),
                    "OMP_NUM_THREADS": "4", "MKL_NUM_THREADS": "4", "WANDB_MODE": "offline",
                    "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1"})
    # Trust only checkouts created for this audit; never change global Git config.
    trusted = [ROOT / "external" / "tfwm", ROOT / "external" / "market-1t",
               ROOT / "external" / "tfwm" / "stable-finance",
               ROOT / ".cache" / "uv" / "git-v1" / "db" / "2af222e2d9a1a028",
               ROOT / ".cache" / "uv" / "git-v1" / "db" / "2af222e2d9a1a028" / ".git",
               ROOT / ".cache" / "uv" / "git-v1" / "checkouts" / "2af222e2d9a1a028" / "e5c81f6",
               ROOT / ".cache" / "uv" / "git-v1" / "checkouts" / "2af222e2d9a1a028" / "e5c81f6" / ".git"]
    env["GIT_CONFIG_COUNT"] = str(len(trusted))
    for index, path in enumerate(trusted):
        env[f"GIT_CONFIG_KEY_{index}"] = "safe.directory"
        env[f"GIT_CONFIG_VALUE_{index}"] = path.as_posix()
    started = time.monotonic()
    with output.open("w", encoding="utf-8") as stream:
        try:
            code = subprocess.run(command, cwd=args.cwd, env=env, stdout=stream,
                                  stderr=subprocess.STDOUT, check=False).returncode
        except OSError as exc:
            stream.write(f"{type(exc).__name__}: {exc}\n")
            code = 127
    record = {"label": args.label, "started_at": stamp.isoformat(),
              "elapsed_seconds": round(time.monotonic() - started, 3),
              "cwd": str(Path(args.cwd).resolve()), "command": command,
              "exit_code": code, "output": output.relative_to(ROOT).as_posix(),
              "environment_overrides": {key: value for key, value in env.items()
                  if key.startswith(("UV_", "GIT_CONFIG_")) or key in ["PYTHONUTF8", "PYTHONIOENCODING", "HF_HUB_DISABLE_PROGRESS_BARS", "PYTHONPATH", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "WANDB_MODE", "HF_HUB_OFFLINE", "TRANSFORMERS_OFFLINE"]},
              "output_sha256": hashlib.sha256(output.read_bytes()).hexdigest()}
    (RUN / f"{name}.json").write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(record, ensure_ascii=False))
    print(output.read_text(encoding="utf-8", errors="replace"))
    return code


if __name__ == "__main__":
    sys.exit(main())
