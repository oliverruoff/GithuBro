from __future__ import annotations

import re

from app.github.client import GitHubClient
from app.modes import Comment


def list_all(client: GitHubClient, repo: str) -> list[dict]:
    return client.json([
        "pr", "list", "--repo", repo, "--state", "all", "--limit", "100",
        "--json", "number,title,headRefName,url,body,state,createdAt",
    ]) or []


def matching_for_issue(prs: list[dict], issue_number: int) -> dict | None:
    pattern = re.compile(rf"^agent/{issue_number}-")
    matches = [pr for pr in prs if pattern.match(pr.get("headRefName", ""))]
    if not matches:
        return None
    # Prefer an open PR; otherwise use the newest deterministically.
    return sorted(matches, key=lambda pr: (str(pr.get("state", "")).lower() == "open", pr.get("createdAt", "")), reverse=True)[0]


def get_pr(client: GitHubClient, repo: str, number: int) -> dict:
    return client.json([
        "pr", "view", str(number), "--repo", repo,
        "--json", "number,title,body,headRefName,state,url,comments,commits",
    ])


def get_comments(client: GitHubClient, repo: str, number: int) -> list[Comment]:
    issue_rows = client.json(["api", f"repos/{repo}/issues/{number}/comments"]) or []
    review_rows = client.json(["api", f"repos/{repo}/pulls/{number}/comments"]) or []
    comments = [Comment(x.get("body") or "", x["created_at"], x["user"]["login"], "pr") for x in issue_rows]
    comments += [Comment(x.get("body") or "", x["created_at"], x["user"]["login"], "review") for x in review_rows]
    return sorted(comments, key=lambda item: item.created_at)


def comment(client: GitHubClient, repo: str, number: int, body: str) -> None:
    client.body_file_command(["pr", "comment", str(number), "--repo", repo], body)


def create_pr(client: GitHubClient, repo: str, base: str, head: str, title: str, body: str) -> str:
    return client.body_file_command([
        "pr", "create", "--repo", repo, "--base", base, "--head", head, "--title", title,
    ], body).strip()


def update_pr(client: GitHubClient, repo: str, number: int, *, title: str | None = None, body: str | None = None) -> None:
    args = ["pr", "edit", str(number), "--repo", repo]
    if title is not None:
        args += ["--title", title]
    if body is not None:
        client.body_file_command(args, body)
    else:
        client.command(args)
