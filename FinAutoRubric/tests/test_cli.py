import json

import pytest

from scripts import run_eval


@pytest.fixture
def project(tmp_path, monkeypatch):
    monkeypatch.setattr(run_eval, "ROOT", tmp_path)
    (tmp_path / "configs").mkdir()
    (tmp_path / "configs/protocol.yaml").write_text('version: test\n')
    (tmp_path / "config.yaml").write_text(json.dumps({
        "question_glob": "questions/*/question.json", "output_dir": "runs",
        "budget": {}, "provider": "mock",
    }))
    return tmp_path


def test_empty_glob_fails(project, capsys):
    assert run_eval.main(["--config", "config.yaml"]) == 1
    assert 'no questions matched' in capsys.readouterr().err


def test_unmatched_only_fails(project, capsys):
    qdir = project / "questions/q1"
    qdir.mkdir(parents=True)
    (qdir / "question.json").write_text('{}')
    assert run_eval.main(["--config", "config.yaml", "--only", "missing"]) == 1
    assert 'no questions matched' in capsys.readouterr().err


@pytest.mark.parametrize("status,exit_code", [("submitted", 0), ("timeout", 1), ("error", 1)])
def test_exit_code_reflects_episode_completion(project, monkeypatch, status, exit_code):
    qdir = project / "questions/q1"
    qdir.mkdir(parents=True)
    (qdir / "question.json").write_text('{}')
    monkeypatch.setattr(run_eval, 'run_question', lambda *a, **kw: {
        'trace': {'question_id': 'q1', 'status': status,
                  'counters': dict(steps=1, tool_calls=1, retries=0, errors=0)},
        'score': {'score': 0, 'max_score': 100}, 'compliance': {'status': 'clean'}, 'run_id': 'test',
    })
    assert run_eval.main(["--config", "config.yaml"]) == exit_code
