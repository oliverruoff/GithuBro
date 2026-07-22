from __future__ import annotations

from app.github.client import GitHubClient
from app.modes import Comment


def list_open_with_label(client: GitHubClient, repo: str, label: str) -> list[dict]:
    return client.json([
        "issue", "list", "--repo", repo, "--label", label, "--state", "open",
        "--json", "number,title,updatedAt,labels", "--limit", "100",
    ]) or []


def get_issue(client: GitHubClient, repo: str, number: int) -> dict:
    return client.json([
        "issue", "view", str(number), "--repo", repo,
        "--json", "title,body,comments,labels,number,updatedAt,state",
    ])


def get_comments(client: GitHubClient, repo: str, number: int) -> list[Comment]:
    rows = client.json(["api", f"repos/{repo}/issues/{number}/comments"]) or []
    return [Comment(row.get("body") or "", row["created_at"], row["user"]["login"], "issue") for row in rows]


def post_comment(client: GitHubClient, repo: str, number: int, body: str) -> None:
    client.body_file_command(["issue", "comment", str(number), "--repo", repo], body)
