"""Orchestrate one run: question -> episode -> judge -> artifacts on disk."""
import platform
import sys

from ..agent.loop import run_episode
from ..agent.providers import MockProvider
from ..agent.tools import Toolbox
from ..common import iso, new_run_id, now, read_json, sha256_path, write_json
from .judge import RuleJudge
from .rubric import load_rubric


def build_provider(kind, question_dir):
    if kind == "mock":
        return MockProvider(read_json(question_dir / "mock_script.json"))
    raise ValueError("provider %r is not wired into the offline round" % kind)


def run_question(question_dir, budget, protocol, runs_root, provider_kind="mock"):
    question_dir = question_dir.resolve()
    question_path = question_dir / "question.json"
    rubric_path = question_dir / "rubric.json"

    question = read_json(question_path)
    rubric = load_rubric(read_json(rubric_path))
    toolbox = Toolbox(question_dir / question.get("evidence_dir", "evidence"))
    provider = build_provider(provider_kind, question_dir)

    run_id = new_run_id(provider_kind, question["id"])
    started = now()
    trace = run_episode(question, provider, toolbox, budget)
    score = RuleJudge().score(rubric, trace["final_answer"], trace["status"])
    finished = now()

    run_dir = runs_root / run_id
    write_json(run_dir / "trace.json", dict({"run_id": run_id, "started_at": iso(started)}, **trace))
    write_json(run_dir / "score.json", dict({"run_id": run_id, "scored_at": iso(finished)}, **score))
    write_json(
        run_dir / "config.json",
        {
            "run_id": run_id,
            "started_at": iso(started),
            "finished_at": iso(finished),
            "provider": trace["provider"],
            "protocol": protocol,
            "budget": budget,
            "question": {"path": str(question_path.relative_to(question_path.parents[2])), "sha256": sha256_path(question_path)},
            "rubric": {"sha256": sha256_path(rubric_path)},
            "python": sys.version.split()[0],
            "platform": platform.platform(),
        },
    )
    return {"run_id": run_id, "run_dir": run_dir, "trace": trace, "score": score}
