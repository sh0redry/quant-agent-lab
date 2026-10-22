"""Run the frozen protocol over the fixture questions.

Usage: python scripts/run_eval.py [--config configs/mock_run.yaml] [--only fc-01]
"""
import argparse
from pathlib import Path
import sys

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.common import sha256_path
from src.eval.runner import run_question


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/mock_run.yaml")
    parser.add_argument("--only", default=None, help="run one question id")
    args = parser.parse_args(argv)

    config = yaml.safe_load((ROOT / args.config).read_text(encoding="utf-8-sig"))
    protocol_path = ROOT / "configs" / "protocol.yaml"
    protocol = {
        "version": yaml.safe_load(protocol_path.read_text(encoding="utf-8-sig"))["version"],
        "sha256": sha256_path(protocol_path),
    }
    runs_root = ROOT / config["output_dir"]
    runs_root.mkdir(parents=True, exist_ok=True)

    failures = 0
    matched = 0
    for question_path in sorted(ROOT.glob(config["question_glob"])):
        question_dir = question_path.parent
        if args.only and question_dir.name != args.only:
            continue
        matched += 1
        result = run_question(
            question_dir,
            config["budget"],
            protocol,
            runs_root,
            config["provider"],
            provider_config=config.get("provider_config"),
            pricing=config.get("pricing"),
        )
        counters = result["trace"]["counters"]
        print(
            "%-6s score=%3d/%-3d status=%-13s cutoff=%-14s steps=%d tools=%d retries=%d errors=%d  %s"
            % (
                result["trace"]["question_id"],
                result["score"]["score"],
                result["score"]["max_score"],
                result["trace"]["status"],
                result["compliance"]["status"],
                counters["steps"],
                counters["tool_calls"],
                counters["retries"],
                counters["errors"],
                result["run_id"],
            )
        )
        if result["trace"]["status"] != "submitted":
            failures += 1
    if not matched:
        print("no questions matched", file=sys.stderr)
        return 1
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
