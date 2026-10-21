"""Run a command in QuantLab and retain only compact evidence in Git.

Verbose output is local-only under .cache/wsl. Use --root for distro setup.
"""
import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
RESULT = ROOT / "Financial World Modeling" / "results" / "wsl_r0.json"


def storage_observation():
    import winreg
    base = r"Software\Microsoft\Windows\CurrentVersion\Lxss"
    distributions = []
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, base) as key:
        default_id = winreg.QueryValueEx(key, "DefaultDistribution")[0]
        for index in range(winreg.QueryInfoKey(key)[0]):
            identifier = winreg.EnumKey(key, index)
            with winreg.OpenKey(key, identifier) as distro:
                name = winreg.QueryValueEx(distro, "DistributionName")[0]
                path = winreg.QueryValueEx(distro, "BasePath")[0]
                distributions.append({"name": name, "base_path": path,
                                      "is_default": identifier == default_id})
    return {"distributions": distributions,
            "quantlab_vhdx_file_bytes": Path('D:/WSL/QuantLab/ext4.vhdx').stat().st_size,
            "d_drive_free_bytes": shutil.disk_usage('D:/').free,
            "note": "VHDX logical capacity differs from physical disk free space; shared WSL swap/config unchanged."}


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    split = sys.argv.index("--")
    parser = argparse.ArgumentParser()
    parser.add_argument("label")
    parser.add_argument("--root", action="store_true")
    parser.add_argument("--windows", action="store_true")
    args = parser.parse_args(sys.argv[1:split])
    command = sys.argv[split + 1:]
    if not args.windows:
        command = ["wsl", "--distribution", "QuantLab", "--user",
                   "root" if args.root else "quantlab", "--exec", *command]
    logs = ROOT / ".cache" / "wsl"
    logs.mkdir(parents=True, exist_ok=True)
    timestamp = dt.datetime.now(dt.timezone(dt.timedelta(hours=8)))
    logfile = logs / f"{timestamp:%Y%m%d-%H%M%S}-{args.label}.txt"
    execution_command = command.copy()
    # Bash reads scripts incrementally: snapshot before execution so editing the
    # source harness during a long install/test cannot alter its unread suffix.
    if not args.windows and len(command) > 7 and command[6] == "/bin/bash" and command[7].startswith("/mnt/d/"):
        source = Path("D:/" + command[7][7:])
        snapshot = logs / f"{timestamp:%Y%m%d-%H%M%S-%f}-{args.label}.sh"
        snapshot.write_bytes(source.read_bytes())
        execution_command[7] = "/mnt/d/" + snapshot.as_posix()[3:]
    started = time.monotonic()
    with logfile.open("wb") as stream:
        process = subprocess.run(execution_command, stdout=stream, stderr=subprocess.STDOUT, check=False)
    raw = logfile.read_bytes()
    if not args.windows and b"\x00" in raw:
        # wsl.exe may prefix UTF-8 Linux output with a UTF-16 host warning.
        output = raw[raw.rfind(b"\x00") + 1:].decode("utf-8", errors="replace")
    elif raw.count(b"\x00") > len(raw) * 0.2:
        output = raw.decode("utf-16-le", errors="replace")
    else:
        output = raw.decode("utf-8", errors="replace")
    record = {"label": args.label, "started_at": timestamp.isoformat(),
        "elapsed_seconds": round(time.monotonic() - started, 3), "command": command,
        "exit_code": process.returncode, "output_sha256": hashlib.sha256(raw).hexdigest()}
    # Install chatter remains local. Diagnostics and final summaries are retained.
    if args.label in {"environment", "gpu", "imports", "git-state", "external-cache"}:
        record["output"] = output[-16000:]
    else:
        record["summary_tail"] = output[-1800:]
    (logs / f"{timestamp:%Y%m%d-%H%M%S}-{args.label}.json").write_text(
        json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.label == "summary" and process.returncode == 0:
        data = json.loads(output.strip())
        data["storage_observation"] = storage_observation()
        keep = {"sync-fin", "sync-market", "sync-tfwm", "test-fin", "test-market",
                "test-tfwm", "environment", "imports", "gpu", "git-state", "external-cache"}
        latest = {}
        for path in sorted(logs.glob("*.json")):
            item = json.loads(path.read_text(encoding="utf-8"))
            if item["label"] in keep:
                latest[item["label"]] = item
        data["commands"] = list(latest.values())
        data["generated_at"] = timestamp.isoformat()
        RESULT.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(record, ensure_ascii=False, indent=2))
    if args.label not in {"environment", "gpu", "imports", "git-state", "external-cache"}:
        print(output[-6000:])
    return process.returncode


if __name__ == "__main__":
    sys.exit(main())
