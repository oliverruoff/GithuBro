import pytest

from app.config import Config
from app.github.labels import ensure_workflow_labels
from app.github.repos import list_user_repos


class RepoListClient:
    def __init__(self, repos: list[dict] | None = None):
        self.repos = repos or []
        self.args: list[str] | None = None

    def json(self, args):
        self.args = list(args)
        assert args[:2] == ["repo", "list"]
        return list(self.repos)


class LabelListClient:
    """Mock that simulates one repo returning HTTP 403 (archived/read-only)."""

    def __init__(self, *, failing_repos: set[str]):
        self.failing_repos = failing_repos
        self.commands: list[list[str]] = []
        self.json_calls: list[list[str]] = []

    def command(self, args):
        self.commands.append(list(args))

    def json(self, args):
        self.json_calls.append(list(args))
        assert args[:2] == ["label", "list"]
        repo = args[args.index("--repo") + 1]
        if repo in self.failing_repos:
            from app.util.subprocess import CommandError
            raise CommandError(f"command failed (1): gh: HTTP 403: repository archived ({repo})")
        return [{"name": "agent"}, {"name": "agent-in-progress"}, {"name": "agent-done"}]


def test_list_user_repos_excludes_archived_repos():
    client = RepoListClient([
        {"nameWithOwner": "alice/active", "isArchived": False},
        {"nameWithOwner": "alice/old", "isArchived": True},
        {"nameWithOwner": "alice/legacy", "isArchived": True},
        {"nameWithOwner": "alice/fresh", "isArchived": False},
    ])
    assert list_user_repos(client, "alice") == ["alice/active", "alice/fresh"]
    assert client.args == ["repo", "list", "alice", "--json", "nameWithOwner,isArchived,isFork", "--limit", "100"]


def test_list_user_repos_excludes_forks():
    client = RepoListClient([
        {"nameWithOwner": "alice/source", "isArchived": False, "isFork": False},
        {"nameWithOwner": "alice/fork", "isArchived": False, "isFork": True},
    ])
    assert list_user_repos(client, "alice") == ["alice/source"]


def test_list_user_repos_treats_missing_is_archived_as_active():
    """Legacy rows without ``isArchived`` (older `gh` versions) stay included."""
    client = RepoListClient([{"nameWithOwner": "alice/legacy-no-field"}])
    assert list_user_repos(client, "alice") == ["alice/legacy-no-field"]


def test_ensure_workflow_labels_skips_repos_that_cannot_be_read():
    """A repo returning HTTP 403 must not abort label provisioning for siblings."""
    client = LabelListClient(failing_repos={"alice/archived"})
    created = ensure_workflow_labels(
        client, ("alice/active", "alice/archived", "alice/other"),
        trigger="agent", in_progress="agent-in-progress", done="agent-done",
    )
    # Both healthy repos reported as already-labelled; the archived one is skipped.
    assert created["alice/active"] == ()
    assert created["alice/other"] == ()
    assert created["alice/archived"] == ()
    # Sanity: label list was attempted for every repo exactly once.
    assert len(client.json_calls) == 3
    assert all(call[:2] == ["label", "list"] for call in client.json_calls)
