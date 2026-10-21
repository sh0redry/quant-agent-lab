"""Rubric loading and deterministic item checks."""
import re

CHECK_TYPES = {"contains_all", "contains_any", "not_contains", "regex", "number_within"}


class RubricError(ValueError):
    pass


def load_rubric(data):
    items = data.get("items")
    if not items:
        raise RubricError("rubric has no items")
    seen = set()
    for item in items:
        missing = {"id", "weight", "requirement", "check"} - set(item)
        if missing:
            raise RubricError("item %s missing fields: %s" % (item.get("id"), sorted(missing)))
        if item["id"] in seen:
            raise RubricError("duplicate item id: %s" % item["id"])
        seen.add(item["id"])
        kind = item["check"].get("type")
        if kind not in CHECK_TYPES:
            raise RubricError("unsupported check type: %s" % kind)
    total = sum(item["weight"] for item in items)
    if total != data.get("total_points", 100):
        raise RubricError("item weights sum to %s, expected %s" % (total, data.get("total_points", 100)))
    return data


def _find_numbers(text):
    return [float(m) for m in re.findall(r"-?\d+(?:\.\d+)?", text)]


def check_item(check, answer):
    """Return (passed, detail). Checks are case-insensitive for text values."""
    kind = check["type"]
    values = check.get("values", [])
    haystack = answer.lower()
    if kind == "contains_all":
        missing = [v for v in values if v.lower() not in haystack]
        return (not missing, {"missing": missing})
    if kind == "contains_any":
        hit = [v for v in values if v.lower() in haystack]
        return (bool(hit), {"matched": hit})
    if kind == "not_contains":
        found = [v for v in values if v.lower() in haystack]
        return (not found, {"found": found})
    if kind == "regex":
        missing = [p for p in values if not re.search(p, answer, flags=re.IGNORECASE)]
        return (not missing, {"unmatched_patterns": missing})
    if kind == "number_within":
        target, tolerance = float(values[0]), float(values[1])
        numbers = _find_numbers(answer)
        close = [n for n in numbers if abs(n - target) <= tolerance]
        return (bool(close), {"target": target, "tolerance": tolerance, "numbers_found": numbers[:12]})
    raise RubricError("unsupported check type: %s" % kind)
