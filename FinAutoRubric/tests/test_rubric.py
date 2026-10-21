import pytest

from src.eval.rubric import RubricError, check_item, load_rubric


def make_item(**overrides):
    item = {"id": "R1", "weight": 100, "requirement": "x", "check": {"type": "contains_all", "values": ["a"]}}
    item.update(overrides)
    return item


def test_load_rubric_rejects_weight_mismatch():
    with pytest.raises(RubricError):
        load_rubric({"total_points": 100, "items": [make_item(weight=90)]})


def test_load_rubric_rejects_unknown_check_type():
    with pytest.raises(RubricError):
        load_rubric({"items": [make_item(check={"type": "vibes"})]})


def test_contains_all_is_case_insensitive():
    passed, detail = check_item({"type": "contains_all", "values": ["Q4", "2024"]}, "latest is q4 2024")
    assert passed and detail["missing"] == []


def test_not_contains_flags_forbidden_value():
    passed, detail = check_item({"type": "not_contains", "values": ["8.8"]}, "about 8.8 percent")
    assert not passed and detail["found"] == ["8.8"]


def test_number_within_uses_tolerance():
    assert check_item({"type": "number_within", "values": [3.0, 0.05]}, "change of +3.02 pp")[0]
    assert not check_item({"type": "number_within", "values": [3.0, 0.05]}, "change of +4.0 pp")[0]
