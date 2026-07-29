from app.runner.poll import poll


def test_idle_tick_returns_none(monkeypatch, config, caplog):
    caplog.set_level("INFO")
    monkeypatch.setattr("app.runner.poll.list_open_with_label", lambda *_: [])
    assert poll(object(), config) is None
    assert "no candidates" in caplog.text


def test_global_fifo_selects_oldest(monkeypatch, config):
    config = type(config)(**{**config.__dict__, "repos": ("o/new", "o/old")})
    rows = {
        ("o/new", "agent"): [{"number": 1, "title": "new", "updatedAt": "2026-02-01T00:00:00Z", "labels": [{"name": "agent"}]}],
        ("o/old", "agent"): [{"number": 2, "title": "old", "updatedAt": "2026-01-01T00:00:00Z", "labels": [{"name": "agent"}]}],
    }
    monkeypatch.setattr("app.runner.poll.list_open_with_label", lambda _c, repo, label: rows.get((repo, label), []))
    monkeypatch.setattr("app.runner.poll.get_issue_comments", lambda *_: [])
    monkeypatch.setattr("app.runner.poll.list_all", lambda *_: [])
    assert poll(object(), config).repo == "o/old"


def test_repo_failure_does_not_block_other_repos(monkeypatch, config, caplog):
    config = type(config)(**{**config.__dict__, "repos": ("o/broken", "o/healthy")})
    issue = {
        "number": 1,
        "title": "queued",
        "updatedAt": "2026-01-01T00:00:00Z",
        "labels": [{"name": "agent"}],
    }

    def list_issues(_client, repo, label):
        if repo == "o/broken":
            raise RuntimeError("issues are disabled")
        return [issue] if label == "agent" else []

    caplog.set_level("WARNING")
    monkeypatch.setattr("app.runner.poll.list_open_with_label", list_issues)
    monkeypatch.setattr("app.runner.poll.get_issue_comments", lambda *_: [])
    monkeypatch.setattr("app.runner.poll.list_all", lambda *_: [])

    assert poll(object(), config).repo == "o/healthy"
    assert "repository poll failed; skipping repo" in caplog.text


def test_fresh_in_progress_issue_is_skipped(monkeypatch, config):
    issue = {"number": 1, "title": "x", "updatedAt": "2026-01-01T00:00:00Z", "labels": [{"name": "agent-in-progress"}]}
    monkeypatch.setattr("app.runner.poll.list_open_with_label", lambda _c, _r, label: [issue] if label == "agent-in-progress" else [])
    monkeypatch.setattr("app.runner.poll.get_issue_comments", lambda *_: [])
    monkeypatch.setattr("app.runner.poll.is_stale", lambda *_: False)
    assert poll(object(), config) is None
