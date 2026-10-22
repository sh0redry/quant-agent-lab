import pytest

from src.eval.rubric import RubricError, check_item, find_numbers, load_rubric


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


def test_load_rubric_rejects_incomplete_number_check():
    with pytest.raises(RubricError):
        load_rubric({"items": [make_item(check={"type": "number_within", "values": [1.0]})]})


def test_contains_all_is_case_insensitive():
    passed, detail = check_item({"type": "contains_all", "values": ["Q4", "2024"]}, "latest is q4 2024")
    assert passed and detail["missing"] == []


def test_not_contains_flags_forbidden_value():
    passed, detail = check_item({"type": "not_contains", "values": ["8.8"]}, "about 8.8 percent")
    assert not passed and detail["found"] == ["8.8"]


def test_number_within_uses_tolerance():
    assert check_item({"type": "number_within", "values": [3.0, 0.05]}, "change of +3.02 pp")[0]
    assert not check_item({"type": "number_within", "values": [3.0, 0.05]}, "change of +4.0 pp")[0]


def test_thousands_separator_is_one_number():
    assert find_numbers("revenue 1,234.56 million") == [1234.56]


def test_parenthesised_negative():
    assert find_numbers("net income (1,234.56)") == [-1234.56]


def test_fullwidth_digits_and_minus():
    assert find_numbers("变化为 －3.5 个百分点") == [-3.5]


def test_iso_dates_are_not_numbers():
    assert find_numbers("as of 2025-02-04 revenue 498.0") == [498.0]


def test_number_within_can_require_nearby_keyword():
    check = {"type": "number_within", "values": [498.0, 0.5], "near": ["营业收入"]}
    assert check_item(check, "该季度营业收入为 498.0 百万元")[0]
    assert not check_item(check, "员工人数 498.0 人")[0]


def test_number_within_near_missing_keyword_fails():
    check = {"type": "number_within", "values": [498.0, 0.5], "near": ["revenue"]}
    passed, detail = check_item(check, "498.0")
    assert not passed and detail["near"] == ["revenue"]


@pytest.mark.parametrize("answer,expected", [
    ("营业收入为498.0百万元", True),
    ("营业收入为100百万元，员工人数为 498.0 人", False),
    ("营业收入为100百万元员工人数为498.0人", False),
    ("营业收入；员工人数为498.0人", False),
    ("营业收入：员工人数为498.0人", False),
    ("revenue was 498.0 million", True),
    ("revenue 100; employees 498.0", False),
])
def test_metric_number_binding(answer, expected):
    check = {"type": "number_within", "values": [498.0, 0.5], "near": ["营业收入", "revenue"]}
    assert check_item(check, answer)[0] is expected


def test_chinese_adjacent_thousands_and_fullwidth_dates():
    assert find_numbers("收入为1,234.56百万元") == [1234.56]
    assert find_numbers("截至２０２５－０２－０４收入为４９８．０百万元") == [498.0]


def test_explicit_unit_constraint():
    check = {"type": "number_within", "values": [498.0, 0.5], "near": ["营业收入"], "unit": ["百万元"]}
    assert check_item(check, "营业收入498.0百万元")[0]
    assert not check_item(check, "营业收入498.0元")[0]
