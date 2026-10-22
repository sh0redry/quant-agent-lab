import json
import urllib.request

import pytest

from src.agent.providers import MockProvider, OpenAICompatibleProvider, ProviderError


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def read(self):
        return json.dumps(self._payload).encode("utf-8")


def completion_payload(tool_calls=None, content="", usage=None):
    message = {"content": content}
    if tool_calls:
        message["tool_calls"] = tool_calls
    return {"choices": [{"message": message}], "usage": usage or {"prompt_tokens": 11, "completion_tokens": 4}}


@pytest.fixture()
def captured(monkeypatch):
    box = {}

    def fake_urlopen(request, timeout=None):
        box["url"] = request.full_url
        box["body"] = json.loads(request.data.decode("utf-8"))
        box["timeout"] = timeout
        return FakeResponse(box.get("payload") or completion_payload())

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setenv("TEST_API_KEY", "secret")
    box["fake"] = fake_urlopen
    return box


def test_provider_parses_tool_calls_and_usage(captured):
    captured["payload"] = completion_payload(
        tool_calls=[
            {
                "id": "call_abc",
                "type": "function",
                "function": {"name": "read_evidence", "arguments": "{\"path\": \"a.md\"}"},
            }
        ]
    )
    provider = OpenAICompatibleProvider(model="m", api_key_env="TEST_API_KEY")
    message = provider.complete([{"role": "user", "content": "hi"}], tools=[], timeout=5)
    assert message.tool_calls[0].id == "call_abc"
    assert message.tool_calls[0].name == "read_evidence"
    assert message.tool_calls[0].args == {"path": "a.md"}
    assert message.usage["prompt_tokens"] == 11
    assert captured["body"]["model"] == "m"


def test_provider_forwards_history_and_bounds_timeout(captured):
    provider = OpenAICompatibleProvider(model="m", api_key_env="TEST_API_KEY", timeout=30)
    history = [
        {"role": "assistant", "content": "", "tool_calls": [{"id": "c1", "type": "function",
         "function": {"name": "calculate", "arguments": "{\"expression\": \"1+1\"}"}}]},
        {"role": "tool", "tool_call_id": "c1", "content": "{\"value\": 2}"},
    ]
    provider.complete(history, tools=[], timeout=2)
    assert captured["body"]["messages"] == history
    assert captured["timeout"] == 2


def test_provider_without_key_refuses_to_run(monkeypatch):
    monkeypatch.delenv("MISSING_KEY", raising=False)
    with pytest.raises(ProviderError):
        OpenAICompatibleProvider(model="m", api_key_env="MISSING_KEY")


def test_mock_provider_generates_and_preserves_ids():
    provider = MockProvider(
        [
            {"text": "", "tool_calls": [{"name": "read_evidence", "args": {"path": "a.md"}}]},
            {"text": "", "tool_calls": [{"id": "fixed_id", "name": "submit", "args": {"answer": "42"}}]},
        ]
    )
    first = provider.complete([], [])
    second = provider.complete([], [])
    assert first.tool_calls[0].id.startswith("call_")
    assert second.tool_calls[0].id == "fixed_id"


def test_mock_provider_exhaustion_raises():
    provider = MockProvider([])
    with pytest.raises(ProviderError):
        provider.complete([], [])
