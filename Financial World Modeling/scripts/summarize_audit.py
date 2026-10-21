"""Retain a compact audit trail; verbose downloads/retries/XML stay Git-ignored."""
import hashlib
import json
import re
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def main():
    records = []
    environments = {}
    relevant = {"clone-tfwm", "clone-tfwm-network", "clone-market1t", "install-uv",
        "collect-evidence-full-access", "market1t-uv-sync", "tfwm-uv-sync",
        "tfwm-uv-sync-checkout-trust", "public-resources", "payload-access-and-size",
        "market1t-pytest-retry", "market1t-platform-diagnosis", "tfwm-sync-without-cuda",
        "install-cpu-torch", "tfwm-pytest", "tfwm-subset-pytest", "tfwm-import-smoke-isolated",
        "final-upstream-status", "tfwm-freeze"}
    for file in sorted((RESULTS / "runs" / "2026-10-22-stage1-2-r0").glob("*.json")):
        data = load(file)
        if data["label"] not in relevant:
            continue
        output = ROOT / data["output"]
        assert hashlib.sha256(output.read_bytes()).hexdigest() == data["output_sha256"]
        selected = {key: data[key] for key in ["label", "started_at", "elapsed_seconds", "cwd", "command", "exit_code", "output_sha256"]}
        if "environment_overrides" in data:
            if "cpu-torch" not in data["environment_overrides"].get("PYTHONPATH", ""):
                data["environment_overrides"].pop("PYTHONPATH", None)
            profile = hashlib.sha256(json.dumps(data["environment_overrides"], sort_keys=True).encode()).hexdigest()[:12]
            environments[profile] = data["environment_overrides"]
            selected["environment_profile"] = profile
        if data["label"].endswith("diagnosis") or "smoke" in data["label"]:
            parsed = json.loads(output.read_text(encoding="utf-8"))
            traces = [value for key, value in parsed.items() if key.endswith("_traceback")]
            selected["checks"] = {key: value for key, value in parsed.items() if not key.endswith("_traceback")}
            if traces:
                selected["representative_traceback"] = traces[0]
        records.append(selected)
    tests = {}
    for file in sorted(RESULTS.glob("*-pytest*.xml")):
        suites = ET.parse(file).getroot()
        cases = list(suites.iter("testcase"))
        failures = []
        representative = {}
        for case in cases:
            for status in ["failure", "error", "skipped"]:
                node = case.find(status)
                if node is not None:
                    message = node.get("message", "")
                    failures.append({"test": case.get("classname", "") + "::" + case.get("name", ""), "status": status, "message": message[:350]})
                    group = status + ":" + case.get("classname", "").split(".")[0]
                    if "OverflowError" in (node.text or ""):
                        group += ":OverflowError"
                    exception = re.findall(r"(?m)^(?:E\s+)?((?:ModuleNotFoundError|ImportError|NameError|OSError|ValueError|RuntimeError):[^\n]+)", node.text or "")
                    if exception:
                        group = status + ":" + exception[-1][:160]
                    if group not in representative:
                        representative[group] = (node.text or "")[-2500:]
        tests[file.stem] = {"total": len(cases),
            "count_note": "JUnit entries; collection errors may appear as placeholder cases and are not executed tests.",
            "passed": sum(all(case.find(tag) is None for tag in ["failure", "error", "skipped"]) for case in cases),
            **{tag: sum(case.find(tag) is not None for case in cases) for tag in ["failure", "error", "skipped"]},
            "failures_and_skips": failures,
            "representative_failure_tails": representative,
            "raw_xml_sha256": hashlib.sha256(file.read_bytes()).hexdigest()}
    source = load(RESULTS / "source_manifest.json")
    for repo in source["repositories"].values():
        if "files" in repo:
            files = repo.pop("files")
            repo["tracked_file_count"] = len(files)
            repo["tracked_inventory_sha256"] = hashlib.sha256(json.dumps(files, sort_keys=True).encode()).hexdigest()
            repo["dependency_file_hashes"] = [file for file in files if file["path"] in ["uv.lock", "pyproject.toml", ".gitmodules", ".python-version"]]
    source["stable_pretraining_commit"] = "e5c81f6cc800ad7cd726894f4d595f7956d06817"
    (RESULTS / "source_manifest.json").write_text(json.dumps(source, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    resources = load(RESULTS / "resource_manifest.json")
    if (RESULTS / "payload_checks.json").exists():
        resources["payload_checks"] = load(RESULTS / "payload_checks.json")
        (RESULTS / "resource_manifest.json").write_text(json.dumps(resources, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    summary = {"scope": "Stages 1, 2 and R0; no R1/R2/R3 or L3 replay",
        "retention": "Keep commands, versions, test counts and representative failures; verbose transient logs/XML and upstream snapshots are local-only.",
        "environment_profiles": environments, "commands": records, "tests": tests}
    (RESULTS / "run_manifest.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"command_count": len(records), "tests": {key: {k: value[k] for k in ["total", "passed", "failure", "error", "skipped"]} for key, value in tests.items()}}, indent=2))


if __name__ == "__main__":
    main()
