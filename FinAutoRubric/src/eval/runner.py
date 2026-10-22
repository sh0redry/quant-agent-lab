"""Orchestrate one run: question -> episode -> judge -> artifacts on disk."""
import platform
import posixpath
from pathlib import Path
import sys

from ..agent.loop import run_episode
from ..agent.providers import MockProvider, OpenAICompatibleProvider
from ..agent.tools import Toolbox
from ..common import file_manifest, iso, new_run_id, now, read_json, sha256_path, write_json
from .judge import RuleJudge
from .rubric import load_rubric


def build_provider(kind, question_dir, config=None):
    config = config or {}
    if kind == "mock":
        return MockProvider(read_json(question_dir / "mock_script.json"))
    if kind == "openai":
        if "model" not in config:
            raise ValueError("openai provider needs a model in configs/mock_run.yaml")
        return OpenAICompatibleProvider(
            model=config["model"],
            base_url=config.get("base_url"),
            api_key_env=config.get("api_key_env", "OPENAI_API_KEY"),
        )
    raise ValueError("unknown provider kind: %r" % kind)


def estimate_cost(usage, pricing):
    if not pricing:
        return None
    prompt = usage.get("prompt_tokens", 0) or 0
    completion = usage.get("completion_tokens", 0) or 0
    return round(
        prompt / 1000.0 * float(pricing.get("input_per_1k", 0))
        + completion / 1000.0 * float(pricing.get("output_per_1k", 0)),
        6,
    )


def cutoff_compliance(question, trace, evidence_root=None):
    """Track tool-visible exposure, separately from use in the final answer."""
    material = question.get("post_cutoff_material") or []

    def canonical(path):
        if evidence_root is not None:
            return str((Path(evidence_root) / path).resolve())
        return posixpath.normpath(path.replace('\\', '/'))

    declared = {canonical(path): path for path in material}
    exposed = set()
    sources = []
    for step in trace["steps"]:
        for call in step["tool_calls"]:
            if not call.get("ok"):
                continue
            name = call.get("name")
            if name == "read_evidence":
                paths = [(call.get("args") or {}).get("path")]
            elif name == "search_evidence":
                paths = [hit.get("file") for hit in (call.get("result") or {}).get("hits", [])]
            else:
                continue
            for path in paths:
                if isinstance(path, str) and canonical(path) in declared:
                    label = declared[canonical(path)]
                    exposed.add(label)
                    source = {"tool": name, "path": label}
                    if source not in sources:
                        sources.append(source)
    status = "not-applicable" if not material else ("violated" if exposed else "clean")
    return {"post_cutoff_material": material, "read_by_agent": sorted(exposed),
            "exposure_sources": sources, "measurement": "tool-visible exposure, not final-answer use", "status": status}


def run_question(question_dir, budget, protocol, runs_root, provider_kind="mock", provider_config=None, pricing=None):
    question_dir = question_dir.resolve()
    question_path = question_dir / "question.json"
    rubric_path = question_dir / "rubric.json"

    question = read_json(question_path)
    rubric = load_rubric(read_json(rubric_path))
    evidence_dir = question_dir / question.get("evidence_dir", "evidence")
    toolbox = Toolbox(evidence_dir)
    provider = build_provider(provider_kind, question_dir, provider_config)

    run_id = new_run_id(provider_kind, question["id"])
    started = now()
    trace = run_episode(question, provider, toolbox, budget)
    score = RuleJudge().score(rubric, trace["final_answer"], trace["status"])
    compliance = cutoff_compliance(question, trace, toolbox.root)
    finished = now()

    run_dir = runs_root / run_id
    write_json(run_dir / "trace.json", dict({"run_id": run_id, "started_at": iso(started)}, **trace))
    write_json(
        run_dir / "score.json",
        dict(
            {
                "run_id": run_id,
                "scored_at": iso(finished),
                "cutoff_compliance": compliance,
                "cost_estimate_usd": estimate_cost(trace["counters"]["usage"], pricing),
            },
            **score,
        ),
    )
    write_json(
        run_dir / "config.json",
        {
            "run_id": run_id,
            "started_at": iso(started),
            "finished_at": iso(finished),
            "provider": {"kind": provider_kind, "name": trace["provider"], "model": getattr(provider, "model", None)},
            "pricing": pricing,
            "protocol": protocol,
            "budget": budget,
            "usage": trace["counters"]["usage"],
            "question": {
                "path": str(question_path.relative_to(question_path.parents[2])),
                "sha256": sha256_path(question_path),
            },
            "rubric": {"sha256": sha256_path(rubric_path)},
            "evidence": file_manifest(evidence_dir),
            "python": sys.version.split()[0],
            "platform": platform.platform(),
        },
    )
    return {"run_id": run_id, "run_dir": run_dir, "trace": trace, "score": score, "compliance": compliance}
