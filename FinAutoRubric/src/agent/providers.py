"""Model providers.

The agent loop depends on `complete(messages, tools, timeout=None)` and expects an
OpenAI-shaped conversation history: assistant turns carry `tool_calls`, tool turns
carry `tool_call_id`. The mock provider replays a scripted JSON scenario so an
end-to-end run needs no model call. `OpenAICompatibleProvider` is a thin HTTP
adapter; it is contract-tested against a fake transport and has not been run
against a live API (no key in this environment).
"""
import json
import os
import urllib.request
from dataclasses import dataclass, field


class ProviderError(RuntimeError):
    pass


@dataclass
class ToolCall:
    id: str
    name: str
    args: dict = field(default_factory=dict)


@dataclass
class AssistantMessage:
    text: str = ""
    tool_calls: list = field(default_factory=list)
    usage: dict = field(default_factory=dict)


def _call_id(turn_index, call_index):
    return "call_%d_%d" % (turn_index, call_index)


class MockProvider:
    """Replay a scripted list of assistant turns (data/fixtures/*/mock_script.json)."""

    kind = "mock"

    def __init__(self, script, name="mock"):
        self.script = list(script)
        self.name = name
        self.model = None
        self.calls = 0

    def complete(self, messages, tools, timeout=None):
        if self.calls >= len(self.script):
            raise ProviderError(
                "mock script exhausted after %d turns; the scenario ended without submit()" % self.calls
            )
        turn = self.script[self.calls]
        self.calls += 1
        calls = []
        for index, entry in enumerate(turn.get("tool_calls", []), start=1):
            calls.append(
                ToolCall(
                    id=entry.get("id") or _call_id(self.calls, index),
                    name=entry["name"],
                    args=entry.get("args", {}),
                )
            )
        return AssistantMessage(text=turn.get("text", ""), tool_calls=calls)


class OpenAICompatibleProvider:
    """Chat-completions adapter. Requires the API key environment variable to be set."""

    kind = "openai"

    def __init__(self, model, base_url=None, api_key_env="OPENAI_API_KEY", timeout=120):
        self.name = "openai-compatible:%s" % model
        self.model = model
        self.base_url = (base_url or os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")).rstrip("/")
        self.api_key = os.environ.get(api_key_env)
        self.timeout = timeout
        if not self.api_key:
            raise ProviderError("%s is not set; refusing to run a paid model" % api_key_env)

    def complete(self, messages, tools, timeout=None):
        body = json.dumps(
            {"model": self.model, "messages": messages, "tools": tools, "temperature": 0}
        ).encode("utf-8")
        request = urllib.request.Request(
            self.base_url + "/chat/completions",
            data=body,
            headers={"Content-Type": "application/json", "Authorization": "Bearer " + self.api_key},
        )
        budget = self.timeout if timeout is None else min(self.timeout, max(timeout, 0.001))
        with urllib.request.urlopen(request, timeout=budget) as response:
            payload = json.loads(response.read().decode("utf-8"))
        message = payload["choices"][0]["message"]
        calls = []
        for index, call in enumerate(message.get("tool_calls") or [], start=1):
            calls.append(
                ToolCall(
                    id=call.get("id") or _call_id(0, index),
                    name=call["function"]["name"],
                    args=json.loads(call["function"].get("arguments") or "{}"),
                )
            )
        return AssistantMessage(
            text=message.get("content") or "",
            tool_calls=calls,
            usage=payload.get("usage") or {},
        )
