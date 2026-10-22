"""Rubric loading and deterministic item checks.

Number parsing is deliberately finance-aware: thousands separators, parenthesised
negatives, full-width digits and ISO dates are handled, and `number_within` can be
anchored to a local label-value form (`near`). This is a conservative syntax
check, not general financial semantics or period/coreference resolution.
"""
import re

CHECK_TYPES = {"contains_all", "contains_any", "not_contains", "regex", "number_within"}

_FULLWIDTH = str.maketrans("０１２３４５６７８９．－，", "0123456789.-,")
_DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}(?:[T ]\d{2}:\d{2}(?::\d{2})?)?")
_NUMBER_RE = re.compile(r"(?<![A-Za-z0-9_.,])(\()?([+-]?\d[\d,]*(?:\.\d+)?)(\))?")
_CLAUSE_RE = re.compile(r"[。；;!?！？\n，]|,(?!\d)|(?<!\d),|\.(?!\d)")
_LABEL_GAP_RE = re.compile(
    r"\s*[:：=]?\s*(?:(?:为|是|约为|约|达到|达|was|is|of|equals?|approximately|about)\s*)?"
    r"[:：=]?\s*[$¥€£]?\s*", re.IGNORECASE
)


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
        if kind == "number_within" and len(item["check"].get("values", [])) < 2:
            raise RubricError("item %s: number_within needs [value, tolerance]" % item["id"])
    total = sum(item["weight"] for item in items)
    expected = data.get("total_points", 100)
    if total != expected:
        raise RubricError("item weights sum to %s, expected %s" % (total, expected))
    return data


def _normalise(text):
    return _normalise_keep_offsets(text)


def _normalise_keep_offsets(text):
    """Normalise width and mask ISO dates without shifting character offsets."""
    text = text.translate(_FULLWIDTH)
    return _DATE_RE.sub(lambda match: " " * len(match.group(0)), text)


def _parse_number(opening, token, closing):
    value = float(token.replace(",", ""))
    if opening and closing:
        value = -value
    return value


def iter_numbers(text):
    """Yield (match, value) pairs with offsets into `text`."""
    masked = _normalise_keep_offsets(text)
    for match in _NUMBER_RE.finditer(masked):
        opening, token, closing = match.group(1), match.group(2), match.group(3)
        if closing and not opening:
            continue
        yield match, _parse_number(opening, token, closing)


def find_numbers(text):
    return [value for _, value in iter_numbers(text)]


def _matches_label(text, match, keywords, window=80):
    start = max(0, match.start() - window)
    for boundary in _CLAUSE_RE.finditer(text, 0, match.start()):
        start = max(start, boundary.end())
    prefix = text[start:match.start()]
    for keyword in keywords:
        for label in re.finditer(re.escape(keyword), prefix, flags=re.IGNORECASE):
            if _LABEL_GAP_RE.fullmatch(prefix[label.end():]):
                return True
    return False


def check_item(check, answer):
    """Return (passed, detail). Text checks are case-insensitive."""
    kind = check["type"]
    values = check.get("values", [])
    haystack = answer.lower()
    if kind == "contains_all":
        missing = [value for value in values if value.lower() not in haystack]
        return (not missing, {"missing": missing})
    if kind == "contains_any":
        hit = [value for value in values if value.lower() in haystack]
        return (bool(hit), {"matched": hit})
    if kind == "not_contains":
        found = [value for value in values if value.lower() in haystack]
        return (not found, {"found": found})
    if kind == "regex":
        missing = [pattern for pattern in values if not re.search(pattern, answer, flags=re.IGNORECASE)]
        return (not missing, {"unmatched_patterns": missing})
    if kind == "number_within":
        target, tolerance = float(values[0]), float(values[1])
        near = check.get("near") or []
        seen = []
        hits = []
        for match, value in iter_numbers(answer):
            seen.append(value)
            if abs(value - target) > tolerance:
                continue
            if near and not _matches_label(answer, match, near):
                continue
            units = check.get("unit") or []
            if units and not any(answer[match.end():].lstrip().lower().startswith(unit.lower()) for unit in units):
                continue
            hits.append(value)
        detail = {"target": target, "tolerance": tolerance, "numbers_found": seen[:12]}
        if near:
            detail["near"] = near
        return (bool(hits), detail)
    raise RubricError("unsupported check type: %s" % kind)
