"""Model providers.

The agent loop only depends on `complete(messages, tools)`. The mock provider is
scripted from a JSON file so an end-to-end run is reproducible without a model
call or an API key. The OpenAI-compatible provider is a thin HTTP adapter and is
not exercised by the offline round.
"""
import json
import os
import urllib.request
from dataclasses import dataclass, field


class ProviderError(RuntimeError):
    pass


@dataclass
class ToolCall:
    name: str
    args: dict = field(default_factory=dict)


@dataclass
class AssistantMessage:
    text: str = ""
    tool_calls: list = field(default_factory=list)


class MockProvider:
    """Replay a scripted list of assistant turns (see data/fixtures/*/mock_script.json)."""

    def __init__(self, script, name="mock"):
        self.script = list(script)
        self.name = name
        self.calls = 0

    def complete(self, messages, tools):
        if self.calls >= len(self.script):
            raise ProviderError(
                "mock script exhausted after %d turns; the scenario ended without submit()" % self.calls
            )
        turn = self.script[self.calls]
        self.calls += 1
        calls = [ToolCall(name=c["name"], args=c.get("args", {})) for c in turn.get("tool_calls", [])]
        return AssistantMessage(text=turn.get("text", ""), tool_calls=calls)


class OpenAICompatibleProvider:
    """Minimal chat-completions adapter. Requires OPENAI_API_KEY and OPENAI_BASE_URL."""

    def __init__(self, model, base_url=None, api_key_env="OPENAI_API_KEY", timeout=120):
        self.name = "openai-compatible:%s" % model
        self.model = model
        self.base_url = (base_url or os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")).rstrip("/")
        self.api_key = os.environ.get(api_key_env)
        self.timeout = timeout
        if not self.api_key:
            raise ProviderError("%s is not set; refusing to run a paid model" % api_key_env)

    def complete(self, messages, tools):
        body = json.dumps(
            {"model": self.model, "messages": messages, "tools": tools, "temperature": 0}
        ).encode("utf-8")
        request = urllib.request.Request(
            self.base_url + "/chat/completions",
            data=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer " + self.api_key,
            },
        )
        with urllib.request.urlopen(request, timeout=self.timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
        message = payload["choices"][0]["message"]
        calls = []
        for call in message.get("tool_calls") or []:
            calls.append(ToolCall(name=call["function"]["name"], args=json.loads(call["function"]["arguments"] or "{}")))
        return AssistantMessage(text=message.get("content") or "", tool_calls=calls)
