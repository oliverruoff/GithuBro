from __future__ import annotations

import logging

from app.github.client import GitHubClient

log = logging.getLogger(__name__)


def list_user_repos(client: GitHubClient, username: str, *, limit: int = 100) -> list[str]:
    """Return active, non-fork `owner/repo` slugs owned by ``username``.

    Used to populate ``Config.repos`` when ``GITHUB_REPOS`` is empty: in that
    case the worker watches every non-archived source repository the configured
    user owns so that issues labelled with the trigger label are picked up
    regardless of which repository they live in. Forks are excluded because
    their issue trackers commonly belong to the upstream repository or are
    disabled entirely.

    Archived repositories are excluded: GitHub returns HTTP 403 for any label
    write against an archived repo, which would otherwise abort label
    provisioning at startup (SPEC §9.16).
    """
    rows = client.json([
        "repo", "list", username, "--json", "nameWithOwner,isArchived,isFork",
        "--limit", str(limit),
    ]) or []
    active = [
        row for row in rows
        if row.get("nameWithOwner") and not row.get("isArchived") and not row.get("isFork")
    ]
    archived = sum(1 for row in rows if row.get("isArchived"))
    forks = sum(1 for row in rows if row.get("isFork"))
    if archived:
        log.info(
            "skipping %d archived repos (label writes would return HTTP 403)",
            archived,
        )
    if forks:
        log.info("skipping %d forked repos", forks)
    slugs = {row["nameWithOwner"] for row in active}
    return sorted(slugs)
