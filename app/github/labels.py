from app.github.client import GitHubClient


LABEL_STYLE = {
    "trigger": ("FBCA04", "Queue for githubro"),
    "in_progress": ("D4C5F9", "githubro is processing this issue"),
    "done": ("0E8A16", "githubro completed this issue"),
}


def names(labels: list[dict | str]) -> set[str]:
    return {label if isinstance(label, str) else label["name"] for label in labels}


def transition(
    client: GitHubClient, repo: str, number: int, *, add: str, remove: str | None = None,
) -> None:
    args = ["issue", "edit", str(number), "--repo", repo, "--add-label", add]
    if remove and remove != add:
        args += ["--remove-label", remove]
    client.command(args)


def list_names(client: GitHubClient, repo: str) -> set[str]:
    rows = client.json([
        "label", "list", "--repo", repo, "--limit", "100", "--json", "name",
    ]) or []
    return {row["name"] for row in rows}


def ensure_workflow_labels(
    client: GitHubClient,
    repos: tuple[str, ...],
    *,
    trigger: str,
    in_progress: str,
    done: str,
) -> dict[str, tuple[str, ...]]:
    """Create missing state-machine labels and return what was created per repo."""
    desired = (
        (trigger, *LABEL_STYLE["trigger"]),
        (in_progress, *LABEL_STYLE["in_progress"]),
        (done, *LABEL_STYLE["done"]),
    )
    created: dict[str, tuple[str, ...]] = {}
    for repo in repos:
        existing = list_names(client, repo)
        repo_created: list[str] = []
        for label, color, description in desired:
            if label in existing:
                continue
            try:
                client.command([
                    "label", "create", label, "--repo", repo,
                    "--color", color, "--description", description,
                ])
            except Exception:
                # Another githubro instance may have created it after our list.
                if label not in list_names(client, repo):
                    raise
            existing.add(label)
            repo_created.append(label)
        created[repo] = tuple(repo_created)
    return created
