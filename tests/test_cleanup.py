from pathlib import Path

from app.modes import Mode
from app.runner.cleanup import cleanup
from app.runner.llm import LLMResult
from app.runner.poll import Candidate
from app.runner.setup import SetupResult


def prepared(tmp_path):
    candidate = Candidate("o/r", {"number": 5, "title": "x"}, Mode.FRESH, None)
    return SetupResult(candidate, tmp_path, "agent/5-x", {"number": 5, "title": "x"}, ())


def test_clarification_precedes_existing_pr(monkeypatch, config, tmp_path):
    from app.modes import Comment
    calls = []
    monkeypatch.setattr("app.runner.cleanup.get_comments", lambda *_: [
        Comment("[githubro:runner][event:start]", "2026-01-01T10:00:00Z"),
        Comment("[githubro:agent][outcome:clarification] question", "2026-01-01T10:01:00Z"),
    ])
    monkeypatch.setattr("app.runner.cleanup.list_all", lambda *_: [{"state": "open", "headRefName": "agent/5-x", "url": "u"}])
    monkeypatch.setattr("app.runner.cleanup.transition", lambda *a, **kw: calls.append(kw))
    assert cleanup(object(), config, prepared(tmp_path), LLMResult(0, False, "", "", 1)) == "clarification"
    assert calls == [{"add": "agent", "remove": "agent-in-progress"}]


def test_pr_without_valid_outcome_is_stuck(monkeypatch, config, tmp_path):
    calls, comments = [], []
    monkeypatch.setattr("app.runner.cleanup.get_comments", lambda *_: [])
    monkeypatch.setattr("app.runner.cleanup.list_all", lambda *_: [{"state": "open", "headRefName": "agent/5-x", "url": "u"}])
    monkeypatch.setattr("app.runner.cleanup.transition", lambda *a, **kw: calls.append(kw))
    monkeypatch.setattr("app.runner.cleanup.post_comment", lambda *a: comments.append(a[-1]))
    assert cleanup(object(), config, prepared(tmp_path), LLMResult(0, False, "", "", 1)) == "stuck"
    assert comments[0].endswith("@alice")
