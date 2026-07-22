from __future__ import annotations

import logging
import re

from app.config import Config
from app.github.branches import remove_worktree
from app.github.client import GitHubClient
from app.github.issues import get_comments, post_comment
from app.github.labels import transition
from app.github.prs import list_all, matching_for_issue
from app.runner.llm import LLMResult
from app.runner.setup import SetupResult

log = logging.getLogger(__name__)
OUTCOME = re.compile(r"^\[githubro:agent\]\[outcome:(success|clarification|audit-passed)\]")


def cleanup(client: GitHubClient, config: Config, setup: SetupResult, result: LLMResult) -> str:
    repo, number = setup.candidate.repo, setup.issue["number"]
    try:
        comments = get_comments(client, repo, number)
        starts = [c for c in comments if c.body.startswith("[githubro:runner][event:start]")]
        start_at = max((c.created_at for c in starts), default="")
        outcomes = []
        for comment in comments:
            match = OUTCOME.match(comment.body)
            if match and comment.created_at > start_at:
                outcomes.append((comment.created_at, match.group(1)))
        outcome = max(outcomes, default=("", ""))[1]
        pr = matching_for_issue(list_all(client, repo), number)
        open_pr = bool(pr and str(pr.get("state", "")).lower() == "open")
        if outcome == "clarification":
            transition(client, repo, number, add=config.trigger_label, remove=config.in_progress_label)
        elif outcome == "audit-passed" and open_pr:
            transition(client, repo, number, add=config.done_label, remove=config.in_progress_label)
        elif outcome == "success" and open_pr:
            transition(client, repo, number, add=config.done_label, remove=config.in_progress_label)
        else:
            outcome = "stuck"
            transition(client, repo, number, add=config.trigger_label, remove=config.in_progress_label)
            post_comment(client, repo, number, (
                "[githubro:runner][event:error]\n"
                "⚠️ githubro exited without a valid result and re-queued the issue.\n"
                f"@{config.username}"
            ))
        log.info("cleanup complete", extra={
            "repo": repo, "issue": number, "mode": setup.candidate.mode.value,
            "outcome": outcome, "runtime_seconds": round(result.runtime_seconds, 2),
            "pr_url": pr.get("url") if pr else None,
        })
        if outcome == "stuck":
            log.error("pi exit=%s timeout=%s stdout_tail=%r stderr_tail=%r", result.exit_code, result.timed_out, result.stdout[-2000:], result.stderr[-2000:])
        return outcome
    finally:
        remove_worktree(setup.work)
