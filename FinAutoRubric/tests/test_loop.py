import copy
import time
from types import SimpleNamespace

import pytest

from src.agent.loop import run_episode
from src.agent.providers import AssistantMessage, MockProvider, ToolCall
from src.agent.tools import Toolbox
from src.eval.judge import RuleJudge
from src.eval.rubric import load_rubric

BUDGET = {"max_steps": 4, "max_tool_calls": 4, "timeout_seconds": 30, "max_tool_retries": 1}
QUESTION = {"id": "t-01", "version": "1", "as_of": "2025-01-01", "prompt": "answer"}
RUBRIC = load_rubric(
    {
        "total_points": 100,
        "items": [
            {"id": "R1", "weight": 100, "requirement": "says 42", "check": {"type": "contains_all", "values": ["42"]}},
        ],
    }
)


@pytest.fixture()
def toolbox(tmp_path):
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    (evidence / "a.md").write_text("42\n", encoding="utf-8")
    return Toolbox(evidence)


class RecordingProvider:
    """Wrap a provider and keep a copy of every message list it saw."""

    def __init__(self, inner):
        self.inner = inner
        self.name = inner.name
        self.seen = []

    def complete(self, messages, tools, timeout=None):
        self.seen.append(copy.deepcopy(messages))
        return self.inner.complete(messages, tools, timeout)


class SlowProvider:
    name = "slow"

    def __init__(self, delay):
        self.delay = delay
        self.seen_timeouts = []

    def complete(self, messages, tools, timeout=None):
        self.seen_timeouts.append(timeout)
        time.sleep(self.delay)
        return AssistantMessage(text="late", tool_calls=[ToolCall(id="call_late", name="submit", args={"answer": "42"})])


class FlakyToolbox:
    def __init__(self, failures=1):
        self.failures = failures
        self.calls = 0

    def specs(self):
        return []

    def call(self, name, args):
        self.calls += 1
        if self.calls <= self.failures:
            raise RuntimeError("transient")
        return {"ok": True}


def run(script, toolbox, budget=None):
    return run_episode(QUESTION, MockProvider(script), toolbox, budget or BUDGET)


def test_submit_ends_episode(toolbox):
    trace = run([{"text": "go", "tool_calls": [{"name": "submit", "args": {"answer": "the value is 42"}}]}], toolbox)
    assert trace["status"] == "submitted"
    assert trace["final_answer"] == "the value is 42"
    assert trace["counters"]["steps"] == 1
    assert trace["counters"]["tool_calls"] == 1
    assert trace["counters"]["retries"] == 0


def test_history_keeps_structured_tool_calls_and_ids(toolbox):
    provider = RecordingProvider(
        MockProvider(
            [
                {"text": "", "tool_calls": [{"name": "read_evidence", "args": {"path": "a.md"}}]},
                {"text": "", "tool_calls": [{"name": "submit", "args": {"answer": "42"}}]},
            ]
        )
    )
    trace = run_episode(QUESTION, provider, toolbox, BUDGET)
    assert trace["status"] == "submitted"
    second_turn = provider.seen[1]
    assistant = [m for m in second_turn if m["role"] == "assistant"][0]
    tool = [m for m in second_turn if m["role"] == "tool"][0]
    assert assistant["tool_calls"][0]["id"] == tool["tool_call_id"]
    assert assistant["tool_calls"][0]["function"]["name"] == "read_evidence"


def test_text_without_submit_is_not_accepted(toolbox):
    trace = run([{"text": "42"}] * 4, toolbox)
    assert trace["status"] == "max_steps"
    assert trace["final_answer"] is None


def test_script_exhaustion_is_a_run_error(toolbox):
    trace = run([{"text": "42"}], toolbox)
    assert trace["status"] == "error"
    assert "mock script exhausted" in trace["error"]


def test_tool_error_is_recorded_and_shown(toolbox):
    trace = run(
        [
            {"text": "", "tool_calls": [{"name": "read_evidence", "args": {"path": "../x"}}]},
            {"text": "", "tool_calls": [{"name": "submit", "args": {"answer": "42"}}]},
        ],
        toolbox,
    )
    assert trace["status"] == "submitted"
    assert trace["counters"]["retries"] == 1
    assert trace["counters"]["errors"] == 1
    record = trace["steps"][0]["tool_calls"][0]
    assert record["ok"] is False
    assert len(record["attempts"]) == 2


def test_no_retry_budget_means_single_attempt(toolbox):
    budget = dict(BUDGET, max_tool_retries=0)
    trace = run([{"text": "", "tool_calls": [{"name": "read_evidence", "args": {"path": "../x"}}]},
                 {"text": "", "tool_calls": [{"name": "submit", "args": {"answer": "42"}}]}], toolbox, budget)
    assert trace["counters"]["retries"] == 0
    assert len(trace["steps"][0]["tool_calls"][0]["attempts"]) == 1


def test_retry_recovers_a_transient_tool_failure():
    toolbox = FlakyToolbox(failures=1)
    trace = run_episode(QUESTION, MockProvider([{"text": "", "tool_calls": [{"name": "probe", "args": {}}]}]), toolbox,
                        dict(BUDGET, max_steps=2, max_tool_calls=2, max_tool_retries=1))
    assert trace["counters"]["retries"] == 1
    assert trace["counters"]["errors"] == 0
    assert trace["steps"][0]["tool_calls"][0]["ok"] is True


def test_budget_stops_the_loop(toolbox):
    script = [{"text": "", "tool_calls": [{"name": "search_evidence", "args": {"query": "42"}}]}] * 10
    trace = run(script, toolbox)
    assert trace["status"] == "max_steps"


def test_deadline_is_passed_to_the_provider(toolbox):
    provider = SlowProvider(delay=0.01)
    run_episode(QUESTION, provider, toolbox, dict(BUDGET, timeout_seconds=5))
    assert provider.seen_timeouts[0] is not None
    assert 0 < provider.seen_timeouts[0] <= 5


def test_slow_provider_past_deadline_is_a_timeout(toolbox):
    provider = SlowProvider(delay=0.05)
    trace = run_episode(QUESTION, provider, toolbox, dict(BUDGET, timeout_seconds=0.005, max_steps=3))
    assert trace["status"] == "timeout"
    assert trace["final_answer"] is None


def test_judge_gives_zero_without_submit(toolbox):
    trace = run([{"text": "42"}], toolbox)
    score = RuleJudge().score(RUBRIC, trace["final_answer"], trace["status"])
    assert score["score"] == 0
    assert score["items"][0]["detail"]["reason"].startswith("no submitted answer")


@pytest.mark.parametrize("fails", [False, True])
def test_tool_past_deadline_cannot_submit_or_retry(monkeypatch, fails):
    from src.agent import loop
    clock = [0.0]
    monkeypatch.setattr(loop, "time", SimpleNamespace(monotonic=lambda: clock[0]))

    class ExpiringToolbox:
        calls = 0

        def specs(self):
            return []

        def call(self, name, args):
            self.calls += 1
            clock[0] = 1.0
            if fails:
                raise RuntimeError("failed after deadline")
            return {"accepted": True}

    toolbox = ExpiringToolbox()
    trace = run([{"tool_calls": [{"name": "submit", "args": {"answer": "42"}}]}],
                toolbox, dict(BUDGET, timeout_seconds=0.5))
    assert trace["status"] == "timeout"
    assert trace["final_answer"] is None
    assert toolbox.calls == 1
    assert trace["counters"]["retries"] == 0
    assert len(trace["steps"][0]["tool_calls"][0]["attempts"]) == 1
    assert RuleJudge().score(RUBRIC, trace["final_answer"], trace["status"])["score"] == 0
