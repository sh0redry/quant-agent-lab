import json
import pytest

from src.common import new_run_id
from src.eval.runner import run_question

BUDGET = {"max_steps": 4, "max_tool_calls": 4, "timeout_seconds": 30, "max_tool_retries": 1}
PROTOCOL = {"version": "test", "sha256": "0" * 64}


def make_project(tmp_path, post_cutoff=None, reads="a.md"):
    qdir = tmp_path / "q1"
    (qdir / "evidence").mkdir(parents=True)
    (qdir / "evidence" / "a.md").write_text("value 42\n", encoding="utf-8")
    (qdir / "question.json").write_text(
        json.dumps(
            {
                "id": "t-01",
                "version": "1",
                "as_of": "2025-01-01",
                "prompt": "p",
                "post_cutoff_material": post_cutoff or [],
            }
        ),
        encoding="utf-8",
    )
    (qdir / "rubric.json").write_text(
        json.dumps(
            {
                "total_points": 100,
                "items": [{"id": "R1", "weight": 100, "requirement": "says 42",
                           "check": {"type": "contains_all", "values": ["42"]}}],
            }
        ),
        encoding="utf-8",
    )
    script = [
        {"text": "", "tool_calls": [{"name": "read_evidence", "args": {"path": reads}}]},
        {"text": "", "tool_calls": [{"name": "submit", "args": {"answer": "value 42"}}]},
    ]
    (qdir / "mock_script.json").write_text(json.dumps(script), encoding="utf-8")
    return qdir


def test_run_id_is_unique_within_a_second():
    ids = {new_run_id("mock", "t-01") for _ in range(50)}
    assert len(ids) == 50


def test_runner_writes_manifest_usage_and_compliance(tmp_path):
    qdir = make_project(tmp_path, post_cutoff=["a.md"])
    runs = tmp_path / "runs"
    result = run_question(qdir, BUDGET, PROTOCOL, runs, "mock")
    config = json.loads((result["run_dir"] / "config.json").read_text(encoding="utf-8"))
    score = json.loads((result["run_dir"] / "score.json").read_text(encoding="utf-8"))

    assert result["score"]["score"] == 100
    expected_bytes = (qdir / "evidence" / "a.md").stat().st_size
    assert config["evidence"] == [{"path": "a.md", "bytes": expected_bytes, "sha256": config["evidence"][0]["sha256"]}]
    assert len(config["evidence"][0]["sha256"]) == 64
    assert config["usage"]["prompt_tokens"] == 0
    assert score["cutoff_compliance"]["status"] == "violated"
    assert score["cutoff_compliance"]["read_by_agent"] == ["a.md"]
    assert score["cost_estimate_usd"] is None


def test_runner_reports_clean_compliance(tmp_path):
    qdir = make_project(tmp_path, post_cutoff=["never_read.md"])
    result = run_question(qdir, BUDGET, PROTOCOL, tmp_path / "runs", "mock")
    assert result["compliance"]["status"] == "clean"


def test_runner_estimates_cost_from_usage(tmp_path, monkeypatch):
    qdir = make_project(tmp_path)
    runs = tmp_path / "runs"
    result = run_question(qdir, BUDGET, PROTOCOL, runs, "mock", pricing={"input_per_1k": 1.0, "output_per_1k": 2.0})
    score = json.loads((result["run_dir"] / "score.json").read_text(encoding="utf-8"))
    # mock provider reports no usage, so cost is exactly zero rather than missing
    assert score["cost_estimate_usd"] == 0.0


@pytest.mark.parametrize("reads", ["./a.md", "sub/../a.md"])
def test_cutoff_normalizes_read_paths(tmp_path, reads):
    qdir = make_project(tmp_path, post_cutoff=["a.md"], reads=reads)
    result = run_question(qdir, BUDGET, PROTOCOL, tmp_path / "runs")
    assert result["compliance"]["status"] == "violated"
    assert result["compliance"]["read_by_agent"] == ["a.md"]


def test_cutoff_tracks_search_exposure(tmp_path):
    qdir = make_project(tmp_path, post_cutoff=["./a.md"])
    script = json.loads((qdir / "mock_script.json").read_text())
    script[0]["tool_calls"] = [{"name": "search_evidence", "args": {"query": "42"}}]
    (qdir / "mock_script.json").write_text(json.dumps(script))
    result = run_question(qdir, BUDGET, PROTOCOL, tmp_path / "runs")
    assert result["compliance"]["status"] == "violated"
    assert result["compliance"]["read_by_agent"] == ["./a.md"]
    assert result["compliance"]["exposure_sources"] == [{"tool": "search_evidence", "path": "./a.md"}]
