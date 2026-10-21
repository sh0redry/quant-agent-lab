import pytest

from src.agent.tools import ToolError, Toolbox, safe_eval


@pytest.fixture()
def toolbox(tmp_path):
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    (evidence / "note.md").write_text("2025 Gross Margin 35.0\n", encoding="utf-8")
    return Toolbox(evidence)


def test_read_evidence_returns_text(toolbox):
    result = toolbox.call("read_evidence", {"path": "note.md"})
    assert "Gross Margin" in result["text"]


def test_path_escape_is_blocked(toolbox):
    with pytest.raises(ToolError):
        toolbox.call("read_evidence", {"path": "../secret.txt"})


def test_search_returns_line_numbers(toolbox):
    result = toolbox.call("search_evidence", {"query": "margin"})
    assert result["hits"][0]["line"] == 1


def test_calculate_rejects_names():
    with pytest.raises(ToolError):
        safe_eval("__import__('os').system('dir')")


def test_calculate_arithmetic():
    assert safe_eval("(1240-806)/1240*100") > 34.9
