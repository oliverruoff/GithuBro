from __future__ import annotations

import logging
from dataclasses import dataclass, replace
from pathlib import Path

import yaml

from app.config import Config
from app.github import branches
from app.github.client import GitHubClient
from app.github.issues import get_comments as get_issue_comments
from app.github.issues import get_issue, post_comment
from app.github.labels import transition
from app.github.prs import get_comments as get_pr_comments
from app.github.prs import get_pr
from app.modes import Comment, Mode, user_feedback_since_activity
from app.runner.poll import Candidate
from app.util.slug import branch_name
from app.util.subprocess import CommandError, run
from app.util.time import iso_now

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class SetupResult:
    candidate: Candidate
    work: Path
    branch: str
    issue: dict
    comments: tuple[Comment, ...]


def setup(client: GitHubClient, config: Config, candidate: Candidate) -> SetupResult:
    repo, number = candidate.repo, candidate.issue["number"]
    transition(client, repo, number, add=config.in_progress_label, remove=config.trigger_label)
    initial_branch = candidate.pr["headRefName"] if candidate.mode != Mode.FRESH and candidate.pr else branch_name(number, candidate.issue["title"])
    post_comment(client, repo, number, _starting_comment(config, candidate, initial_branch))
    work: Path | None = None
    try:
        work = branches.prepare_clone(config, repo, number)
        active = candidate
        branch = initial_branch
        if candidate.mode == Mode.FRESH:
            branches.checkout_fresh(work, config.base_branch, branch)
        elif branches.remote_branch_exists(work, branch):
            branches.checkout_existing(work, branch)
        else:
            log.warning("existing PR branch missing; falling back to fresh", extra={"repo": repo, "issue": number})
            active = replace(candidate, mode=Mode.FRESH, pr=None)
            branch = branch_name(number, candidate.issue["title"])
            branches.checkout_fresh(work, config.base_branch, branch)
        issue = get_issue(client, repo, number)
        comments = get_issue_comments(client, repo, number)
        _write_context(client, config, active, issue, comments, work, branch)
        size = (work / ".githubro" / "issue_context.md").stat().st_size
        log.info("setup complete", extra={"repo": repo, "issue": number, "mode": active.mode.value, "branch": branch})
        log.info("context size bytes: %s", size)
        return SetupResult(active, work, branch, issue, tuple(comments))
    except Exception as exc:
        body = (
            "[githubro:runner][event:error]\n"
            f"⚠️ githubro setup failed: {type(exc).__name__}: {str(exc)[:500]}\n"
            f"@{config.username}"
        )
        try:
            post_comment(client, repo, number, body)
        except Exception:
            log.exception("failed to post setup error", extra={"repo": repo, "issue": number})
        raise


def _starting_comment(config: Config, candidate: Candidate, branch: str) -> str:
    mode = candidate.mode
    if mode == Mode.FRESH:
        middle = f"🐣 githubro picked up this issue.\nTarget branch: `{branch}`\nI'll keep you posted.\n@{config.username}"
    elif mode == Mode.REVISION:
        middle = f"🔁 githubro picked up this issue.\nResuming branch: `{branch}`\nPR: {candidate.pr['url']}\nI'll review your feedback.\n@{config.username}"
    else:
        middle = f"🔎 githubro picked up this issue.\nRe-checking PR: {candidate.pr['url']}\nI'll verify the implementation.\n@{config.username}"
    return f"[githubro:runner][event:start][mode:{mode.value}]\n{middle}"


def _render_comments(comments: list[Comment]) -> str:
    if not comments:
        return "_No comments._"
    chunks = []
    for comment in sorted(comments, key=lambda c: c.created_at):
        marker = " (githubro)" if comment.body.startswith(("[githubro:runner]", "[githubro:agent]")) else ""
        chunks.append(f"### @{comment.author} at {comment.created_at}{marker}\n\n{comment.body}")
    return "\n\n".join(chunks)


def _write_context(client: GitHubClient, config: Config, candidate: Candidate, issue: dict, issue_comments: list[Comment], work: Path, branch: str) -> None:
    pr = get_pr(client, candidate.repo, candidate.pr["number"]) if candidate.pr else None
    pr_comments = get_pr_comments(client, candidate.repo, pr["number"]) if pr else []
    frontmatter = {
        "repo": candidate.repo, "issue": issue["number"], "mode": candidate.mode.value,
        "branch": branch, "base_branch": config.base_branch, "pr_target": config.pr_target,
        "pr_url": pr.get("url") if pr else None, "pr_number": pr.get("number") if pr else None,
        "github_username": config.username, "captured_at": iso_now(),
    }
    try:
        tree = run(["tree", "-L", "2", "-I", "node_modules"], cwd=work).stdout
    except CommandError:
        tree = run(["find", ".", "-maxdepth", "2", "-not", "-path", "./.git/*"], cwd=work).stdout
    root_ls = run(["ls", "-la"], cwd=work).stdout
    sections = [
        "---\n" + yaml.safe_dump(frontmatter, sort_keys=False).strip() + "\n---",
        f"## Title\n\n{issue.get('title', '')}",
        f"## Body\n\n{issue.get('body') or '_No body._'}",
        f"## Comments\n\n{_render_comments(issue_comments)}",
    ]
    if pr:
        commits = pr.get("commits") or []
        commit_lines = "\n".join(f"- {c.get('oid', '')[:12]} {c.get('messageHeadline', '')}" for c in commits) or "_No commits._"
        sections.append(
            f"## Linked PR\n\nURL: {pr['url']}\n\nBranch: `{pr['headRefName']}`\n\n"
            f"### PR body\n\n{pr.get('body') or '_No body._'}\n\n### PR comments\n\n{_render_comments(pr_comments)}\n\n"
            f"### Commits\n\n{commit_lines}"
        )
    sections.append(f"## Repo structure\n\n```text\n{tree}\n{root_ls}\n```")
    if candidate.mode == Mode.SELF_AUDIT:
        diff = run(["git", "diff", f"{config.base_branch}...HEAD", "--stat"], cwd=work).stdout
        sections.append(f"## Last diff\n\n```text\n{diff}\n```")
    if candidate.mode == Mode.REVISION:
        all_comments = [*issue_comments, *pr_comments]
        current_starts = [
            c.created_at for c in issue_comments
            if c.body.startswith("[githubro:runner][event:start]")
        ]
        current_start = max(current_starts, default="")
        historical = [c for c in all_comments if not current_start or c.created_at < current_start]
        feedback = user_feedback_since_activity(historical)
        sections.append(f"## User feedback since last githubro activity\n\n{_render_comments(feedback)}")
    context_dir = work / ".githubro"
    context_dir.mkdir(exist_ok=True)
    (context_dir / "issue_context.md").write_text("\n\n".join(sections) + "\n", encoding="utf-8")
