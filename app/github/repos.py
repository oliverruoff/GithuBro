from __future__ import annotations

import logging

from app.github.client import GitHubClient

log = logging.getLogger(__name__)


def list_user_repos(client: GitHubClient, username: str, *, limit: int = 100) -> list[str]:
    """Return the `owner/repo` slugs of every active repository owned by ``username``.

    Used to populate ``Config.repos`` when ``GITHUB_REPOS`` is empty: in that
    case the worker watches every non-archived repository the configured user
    owns so that issues labelled with the trigger label are picked up
    regardless of which repository they live in.

    Archived repositories are excluded: GitHub returns HTTP 403 for any label
    write against an archived repo, which would otherwise abort label
    provisioning at startup (SPEC §9.16).
    """
    rows = client.json([
        "repo", "list", username, "--json", "nameWithOwner,isArchived",
        "--limit", str(limit),
    ]) or []
    active = [row for row in rows if row.get("nameWithOwner") and not row.get("isArchived")]
    archived = sum(1 for row in rows if row.get("isArchived"))
    if archived:
        log.info(
            "skipping %d archived repos (label writes would return HTTP 403)",
            archived,
        )
    slugs = {row["nameWithOwner"] for row in active}
    return sorted(slugs)
