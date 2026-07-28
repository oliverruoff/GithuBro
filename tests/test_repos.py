import pytest

from app.config import Config
from app.github.repos import list_user_repos
from app.main import provision_labels, resolve_repos


class RepoListClient:
    def __init__(self, repos: list[str] | None = None, *, error: Exception | None = None):
        self.repos = [] if repos is None else repos
        self.error = error
        self.args: list[str] | None = None

    def json(self, args):
        self.args = list(args)
        if self.error is not None:
            raise self.error
        assert args[:2] == ["repo", "list"]
        return [{"nameWithOwner": slug} for slug in self.repos]


def test_list_user_repos_returns_sorted_unique_slugs():
    client = RepoListClient(["b/repo", "a/repo", "a/repo", "c/repo"])
    assert list_user_repos(client, "alice") == ["a/repo", "b/repo", "c/repo"]
    assert client.args == ["repo", "list", "alice", "--json", "nameWithOwner", "--limit", "100"]


def test_list_user_repos_handles_empty_response():
    assert list_user_repos(RepoListClient([]), "alice") == []


@pytest.fixture
def env(monkeypatch):
    for name in (
        "GITHUB_PAT", "GITHUB_REPOS", "GITHUB_USERNAME",
        "BRO_REASONING_EFFORT", "BRO_LOG_LEVEL",
        "BRO_HEARTBEAT_INTERVAL_SECONDS", "BRO_HEARTBEAT_STALE_AFTER_SECONDS",
        "BRO_POLL_INTERVAL_SECONDS", "BRO_RUN_TIMEOUT_SECONDS",
    ):
        monkeypatch.delenv(name, raising=False)
    return monkeypatch


def test_config_from_env_allows_empty_repos(env):
    env.setenv("GITHUB_PAT", "secret")
    env.setenv("GITHUB_REPOS", "")
    config = Config.from_env()
    assert config.repos == ()


def test_config_from_env_allows_unset_repos(env):
    env.setenv("GITHUB_PAT", "secret")
    config = Config.from_env()
    assert config.repos == ()


def test_config_from_env_trims_whitespace_and_skips_empty_entries(env):
    env.setenv("GITHUB_PAT", "secret")
    env.setenv("GITHUB_REPOS", " , owner/repo , , other/repo ")
    assert Config.from_env().repos == ("owner/repo", "other/repo")


def test_config_from_env_rejects_malformed_repos(env):
    env.setenv("GITHUB_PAT", "secret")
    env.setenv("GITHUB_REPOS", "owner/repo,missing-slash")
    with pytest.raises(ValueError, match="owner/repo format"):
        Config.from_env()


def test_resolve_repos_populates_empty_repos_from_user():
    config = Config(github_pat="secret", repos=(), username="alice")
    client = RepoListClient(["alice/two", "alice/one"])
    resolved = resolve_repos(client, config)
    assert resolved.repos == ("alice/one", "alice/two")
    assert resolved.username == "alice"
    assert client.args == ["repo", "list", "alice", "--json", "nameWithOwner", "--limit", "100"]


def test_resolve_repos_is_noop_when_repos_already_set():
    config = Config(github_pat="secret", repos=("owner/repo",), username="alice")
    resolved = resolve_repos(RepoListClient(), config)
    assert resolved.repos == ("owner/repo",)
    assert resolved is config


def test_resolve_repos_exits_when_user_has_no_repos():
    config = Config(github_pat="secret", repos=(), username="alice")
    with pytest.raises(SystemExit):
        resolve_repos(RepoListClient([]), config)


def test_resolve_repos_exits_when_lookup_fails():
    config = Config(github_pat="secret", repos=(), username="alice")
    client = RepoListClient(error=RuntimeError("gh exploded"))
    with pytest.raises(SystemExit):
        resolve_repos(client, config)


def test_provision_labels_logs_created_and_existing(monkeypatch, config):
    created = {"o/repo": ("agent-in-progress",), "o/other": ()}
    monkeypatch.setattr("app.main.ensure_workflow_labels", lambda *a, **kw: created)
    messages = []
    monkeypatch.setattr("app.main.log.info", lambda msg, *args, **kw: messages.append(msg % args if args else msg))
    provision_labels(object(), config)
    assert any("created missing" in m for m in messages)
    assert any("workflow labels ready" in m for m in messages)
