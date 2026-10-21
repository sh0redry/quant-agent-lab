"""Compact, standard-library-only evidence collector for the Linux R0 run."""
import collections
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import xml.etree.ElementTree as ET


def command(*args):
    return subprocess.check_output(args, text=True).strip()


def main():
    root = Path.home() / "projects/quant-agent-lab"
    paths = {"FinAutoRubric": root / "FinAutoRubric",
             "Market-1T": root / ".cache/upstream/market-1t",
             "TFWM": root / ".cache/upstream/tfwm"}
    result = {"distribution": "QuantLab", "storage": "D:/WSL/QuantLab/ext4.vhdx",
              "source_commit": command("git", "-C", str(root), "rev-parse", "HEAD"),
              "kernel": platform.release(), "linux_worktree": str(root),
              "scope": "R0 plus CUDA tensor forward/backward; no R1/R2/R3 or L3 replay",
              "retention": "Only final summaries and representative failures in Git; raw logs, XML, caches and upstream clones are ignored.",
              "projects": {}}
    packages = ["pytest", "numpy", "pandas", "torch", "torchvision", "stable-pretraining", "stable-finance"]
    probe = "import importlib.metadata as m,json,sys; print(json.dumps({'python':sys.version,'packages':{d.metadata['Name']:d.version for d in m.distributions() if d.metadata['Name'].lower() in " + repr(packages) + "}}))"
    for name, path in paths.items():
        data = {"path": str(path), "versions": json.loads(command(str(path / '.venv/bin/python'), '-c', probe)),
                "files": {}}
        for filename in ["pyproject.toml", "uv.lock"]:
            data["files"][filename + "_sha256"] = hashlib.sha256((path / filename).read_bytes()).hexdigest()
        if name != "FinAutoRubric":
            data["commit"] = command("git", "-C", str(path), "rev-parse", "HEAD")
            data["git_status"] = command("git", "-C", str(path), "status", "--porcelain")
        short = {"FinAutoRubric": "fin", "Market-1T": "market", "TFWM": "tfwm"}[name]
        cases = list(ET.parse(root / f'.cache/wsl/{short}-pytest.xml').iter('testcase'))
        counts = collections.Counter()
        skips = collections.Counter()
        problems = []
        for case in cases:
            status = next((tag for tag in ['error', 'failure', 'skipped'] if case.find(tag) is not None), 'passed')
            counts[status] += 1
            if status == 'skipped':
                skips[case.find(status).get('message', '')] += 1
            elif status in {'error', 'failure'}:
                problem = case.find(status)
                problems.append({"case": case.get('classname', '') + '::' + case.get('name', ''),
                                 "status": status, "message": problem.get('message', ''),
                                 "detail": (problem.text or '')[-5000:]})
        data['tests'] = {"xml_entries": len(cases), "counts": dict(counts),
                         "skip_reasons": dict(skips), "problems": problems}
        result['projects'][name] = data
    tfwm = paths['TFWM']
    result['stable_finance_commit'] = command('git', '-C', str(tfwm / 'stable-finance'), 'rev-parse', 'HEAD')
    result['stable_finance_git_status'] = command('git', '-C', str(tfwm / 'stable-finance'), 'status', '--porcelain')
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
