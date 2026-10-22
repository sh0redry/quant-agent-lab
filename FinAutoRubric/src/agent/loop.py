"""Single-episode agent loop.

Budget, deadline and retries are enforced here rather than documented and hoped
for: the remaining time is passed into every model call, checked again after the
call and before every tool call, and tool errors are retried at most
`budget.max_tool_retries` times (each retry counted).
"""
import json
import time

SYSTEM_PROMPT = (
    "You are a financial research assistant. Every factual value you report must come from "
    "the evidence directory, and every calculation must be executed with the calculate tool. "
    "When your answer is complete, call submit exactly once. Never invent a number that you "
    "did not read or compute."
)

USAGE_KEYS = ("prompt_tokens", "completion_tokens", "total_tokens")


def assistant_history_entry(message):
    """OpenAI-shaped assistant turn, keeping structured tool calls and their ids."""
    entry = {"role": "assistant", "content": message.text or ""}
    if message.tool_calls:
        entry["tool_calls"] = [
            {
                "id": call.id,
                "type": "function",
                "function": {"name": call.name, "arguments": json.dumps(call.args, ensure_ascii=False)},
            }
            for call in message.tool_calls
        ]
    return entry


def run_episode(question, provider, toolbox, budget):
    started = time.monotonic()
    deadline = started + budget["timeout_seconds"]
    max_retries = int(budget.get("max_tool_retries", 0))
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": question["prompt"]},
    ]
    steps = []
    counters = {
        "steps": 0,
        "tool_calls": 0,
        "errors": 0,
        "retries": 0,
        "usage": {key: 0 for key in USAGE_KEYS},
    }
    status = "max_steps"
    error = None
    final_answer = None

    for index in range(1, budget["max_steps"] + 1):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            status = "timeout"
            error = "deadline reached before model call"
            break
        try:
            message = provider.complete(messages, toolbox.specs(), timeout=remaining)
        except Exception as exc:
            if isinstance(exc, TimeoutError) or time.monotonic() >= deadline:
                status = "timeout"
                error = "%s: %s" % (type(exc).__name__, exc)
            else:
                status = "error"
                error = "%s: %s" % (type(exc).__name__, exc)
            break

        counters["steps"] += 1
        for key in USAGE_KEYS:
            value = (message.usage or {}).get(key)
            if isinstance(value, (int, float)):
                counters["usage"][key] += int(value)

        step = {"index": index, "text": message.text, "tool_calls": []}
        steps.append(step)

        if time.monotonic() >= deadline:
            status = "timeout"
            error = "deadline exceeded during model call"
            break

        messages.append(assistant_history_entry(message))
        if not message.tool_calls:
            continue

        stop = False
        for call in message.tool_calls:
            if time.monotonic() >= deadline:
                status = "timeout"
                error = "deadline reached before tool call"
                stop = True
                break
            if counters["tool_calls"] >= budget["max_tool_calls"]:
                status = "max_tool_calls"
                stop = True
                break

            counters["tool_calls"] += 1
            record = {"id": call.id, "name": call.name, "args": call.args, "attempts": []}
            ok = False
            result = None
            for attempt in range(max_retries + 1):
                if time.monotonic() >= deadline:
                    status, error, stop = "timeout", "deadline reached before tool attempt", True
                    break
                if attempt:
                    counters["retries"] += 1
                begin = time.monotonic()
                try:
                    result = toolbox.call(call.name, call.args)
                    ok = True
                except Exception as exc:
                    result = {"error": "%s: %s" % (type(exc).__name__, exc)}
                    ok = False
                record["attempts"].append(
                    {"ok": ok, "result": result, "elapsed_ms": round((time.monotonic() - begin) * 1000, 3)}
                )
                if time.monotonic() >= deadline:
                    status, error, stop = "timeout", "deadline exceeded during tool call", True
                    break
                if ok:
                    break
            if record["attempts"] and not ok:
                counters["errors"] += 1
            record["ok"] = ok
            record["result"] = result
            record["elapsed_ms"] = round(sum(item["elapsed_ms"] for item in record["attempts"]), 3)
            step["tool_calls"].append(record)

            if stop:
                break

            messages.append({"role": "tool", "tool_call_id": call.id, "content": json.dumps(result, ensure_ascii=False)})
            if call.name == "submit" and ok:
                final_answer = str(call.args.get("answer", ""))
                status = "submitted"
                stop = True
                break
        if stop:
            break
    else:
        status = "max_steps"

    return {
        "question_id": question["id"],
        "question_version": question.get("version"),
        "as_of": question.get("as_of"),
        "status": status,
        "error": error,
        "final_answer": final_answer,
        "steps": steps,
        "counters": counters,
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "provider": provider.name,
    }
