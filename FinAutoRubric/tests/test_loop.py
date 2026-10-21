import pytest

from src.agent.loop import run_episode
from src.agent.providers import MockProvider, ProviderError
from src.agent.tools import Toolbox
from src.eval.judge import RuleJudge
from src.eval.rubric import load_rubric

BUDGET = {"max_steps": 4, "max_tool_calls": 4, "timeout_seconds": 30}
QUESTION = {"id": "t-01", "version": "1", "as_of": "2025-01-01", "prompt": "answer"}
RUBRIC = load_rubric(
    {
        "total_points": 100,
        "items": [
            {"id": "R1", "weight": 100, "requirement": "says 42",
             "check": {"type": "contains_all", "values": ["42"]}},
        ],
    }
)


@pytest.fixture()
def toolbox(tmp_path):
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    (evidence / "a.md").write_text("42\n", encoding="utf-8")
    return Toolbox(evidence)


def run(script, toolbox):
    return run_episode(QUESTION, MockProvider(script), toolbox, BUDGET)


def test_submit_ends_episode(toolbox):
    trace = run([{"text": "go", "tool_calls": [{"name": "submit", "args": {"answer": "the value is 42"}}]}], toolbox)
    assert trace["status"] == "submitted"
    assert trace["final_answer"] == "the value is 42"
    assert trace["counters"] == {"steps": 1, "tool_calls": 1, "errors": 0, "retries": 0}


def test_text_without_submit_is_not_accepted(toolbox):
    trace = run([{"text": "42"}] * 4, toolbox)  # exhausts max_steps without submit
    assert trace["status"] == "max_steps"
    assert trace["final_answer"] is None


def test_script_exhaustion_is_a_run_error(toolbox):
    trace = run([{"text": "42"}], toolbox)
    assert trace["status"] == "error"
    assert "mock script exhausted" in trace["error"]


def test_tool_error_is_recorded_and_shown(toolbox):
    trace = run(
        [{"text": "", "tool_calls": [{"name": "read_evidence", "args": {"path": "../x"}}]},
         {"text": "", "tool_calls": [{"name": "submit", "args": {"answer": "42"}}]}],
        toolbox,
    )
    assert trace["status"] == "submitted"
    assert trace["counters"]["errors"] == 1
    assert trace["steps"][0]["tool_calls"][0]["ok"] is False


def test_budget_stops_the_loop(toolbox):
    script = [{"text": "", "tool_calls": [{"name": "search_evidence", "args": {"query": "42"}}]}] * 10
    trace = run(script, toolbox)
    assert trace["status"] == "max_steps"


def test_judge_gives_zero_without_submit(toolbox):
    trace = run([{"text": "42"}], toolbox)
    score = RuleJudge().score(RUBRIC, trace["final_answer"], trace["status"])
    assert score["score"] == 0
    assert score["items"][0]["detail"]["reason"].startswith("no submitted answer")
