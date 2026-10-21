"""Judges. v0 judges see the final answer only (the official judges see the full trace)."""
from .rubric import check_item


class RuleJudge:
    """Deterministic judge: executes the rubric's own checks. No model call."""

    name = "rule"

    def score(self, rubric, answer, status):
        items = []
        for item in rubric["items"]:
            if status != "submitted" or answer is None:
                passed, detail = False, {"reason": "no submitted answer (status=%s)" % status}
            else:
                passed, detail = check_item(item["check"], answer)
            items.append(
                {
                    "id": item["id"],
                    "weight": item["weight"],
                    "requirement": item["requirement"],
                    "passed": bool(passed),
                    "detail": detail,
                }
            )
        awarded = sum(item["weight"] for item in items if item["passed"])
        return {
            "judge": self.name,
            "sees": "final_answer",
            "score": awarded,
            "max_score": rubric.get("total_points", 100),
            "items": items,
            "completion": status,
        }
