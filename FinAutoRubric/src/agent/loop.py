"""Single-episode agent loop with explicit budgeting and a full trace."""
import json
import time

SYSTEM_PROMPT = (
    "You are a financial research assistant. Every factual value you report must come from "
    "the evidence directory, and every calculation must be executed with the calculate tool. "
    "When your answer is complete, call submit exactly once. Never invent a number that you "
    "did not read or compute."
)


def run_episode(question, provider, toolbox, budget):
    started = time.monotonic()
    deadline = started + budget["timeout_seconds"]
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": question["prompt"]},
    ]
    steps = []
    counters = {"steps": 0, "tool_calls": 0, "errors": 0, "retries": 0}
    status = "max_steps"
    error = None
    final_answer = None

    for index in range(1, budget["max_steps"] + 1):
        if time.monotonic() > deadline:
            status = "timeout"
            break
        try:
            message = provider.complete(messages, toolbox.specs())
        except Exception as exc:  # provider failure is a run failure, not an agent decision
            status = "error"
            error = "%s: %s" % (type(exc).__name__, exc)
            break

        counters["steps"] += 1
        step = {"index": index, "text": message.text, "tool_calls": []}
        steps.append(step)
        if message.text:
            messages.append({"role": "assistant", "content": message.text})

        if not message.tool_calls:
            # A textual answer without submit() is not accepted: the protocol requires an explicit submit.
            continue

        stop = False
        for call in message.tool_calls:
            if counters["tool_calls"] >= budget["max_tool_calls"]:
                status = "max_tool_calls"
                stop = True
                break
            counters["tool_calls"] += 1
            begin = time.monotonic()
            try:
                result = toolbox.call(call.name, call.args)
                ok = True
            except Exception as exc:  # tool failure is recorded, then shown to the agent
                result = {"error": "%s: %s" % (type(exc).__name__, exc)}
                ok = False
                counters["errors"] += 1
            step["tool_calls"].append(
                {
                    "name": call.name,
                    "args": call.args,
                    "ok": ok,
                    "result": result,
                    "elapsed_ms": round((time.monotonic() - begin) * 1000, 3),
                }
            )
            messages.append({"role": "tool", "content": json.dumps(result, ensure_ascii=False)})
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
