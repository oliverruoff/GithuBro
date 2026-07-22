from app.github.client import GitHubClient


def names(labels: list[dict | str]) -> set[str]:
    return {label if isinstance(label, str) else label["name"] for label in labels}


def transition(
    client: GitHubClient, repo: str, number: int, *, add: str, remove: str | None = None,
) -> None:
    args = ["issue", "edit", str(number), "--repo", repo, "--add-label", add]
    if remove and remove != add:
        args += ["--remove-label", remove]
    client.command(args)
