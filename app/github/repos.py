from __future__ import annotations

from app.github.client import GitHubClient


def list_user_repos(client: GitHubClient, username: str, *, limit: int = 100) -> list[str]:
    """Return the `owner/repo` slugs of every repository owned by ``username``.

    Used to populate ``Config.repos`` when ``GITHUB_REPOS`` is empty: in that
    case the worker watches every repository the configured user owns so that
    issues labelled with the trigger label are picked up regardless of which
    repository they live in.
    """
    rows = client.json([
        "repo", "list", username, "--json", "nameWithOwner", "--limit", str(limit),
    ]) or []
    slugs = {row["nameWithOwner"] for row in rows if row.get("nameWithOwner")}
    return sorted(slugs)
