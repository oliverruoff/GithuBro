from __future__ import annotations

import logging
from dataclasses import dataclass

from app.config import Config
from app.github.client import GitHubClient
from app.github.issues import get_comments as get_issue_comments
from app.github.issues import list_open_with_label
from app.github.labels import names
from app.github.prs import get_comments as get_pr_comments
from app.github.prs import list_all, matching_for_issue
from app.github.recovery import is_stale, recover
from app.modes import Mode, determine_mode

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class Candidate:
    repo: str
    issue: dict
    mode: Mode
    pr: dict | None


def poll(client: GitHubClient, config: Config) -> Candidate | None:
    candidates: list[Candidate] = []
    for repo in config.repos:
        try:
            repo_candidate = _candidate_for_repo(client, config, repo)
        except Exception:
            log.warning(
                "repository poll failed; skipping repo",
                exc_info=True,
                extra={"repo": repo},
            )
            continue
        if repo_candidate:
            candidates.append(repo_candidate)
    if not candidates:
        log.info("no candidates")
        return None
    return min(candidates, key=lambda c: (c.issue.get("updatedAt", ""), c.repo, c.issue["number"]))


def _candidate_for_repo(client: GitHubClient, config: Config, repo: str) -> Candidate | None:
    # Locked issues no longer carry the trigger label, so query both state labels
    # to make stale-run recovery possible after a container restart.
    by_number = {i["number"]: i for i in list_open_with_label(client, repo, config.trigger_label)}
    for item in list_open_with_label(client, repo, config.in_progress_label):
        by_number.setdefault(item["number"], item)
    for issue in sorted(by_number.values(), key=lambda x: (x.get("updatedAt", ""), x["number"])):
        number = issue["number"]
        try:
            issue_comments = get_issue_comments(client, repo, number)
            label_set = names(issue.get("labels", []))
            if config.in_progress_label in label_set:
                if not is_stale(issue_comments, config.heartbeat_stale_after):
                    continue
                recover(client, config, repo, number, issue_comments)
                issue["labels"] = [{"name": config.trigger_label}]
                issue_comments = get_issue_comments(client, repo, number)
            pr = matching_for_issue(list_all(client, repo), number)
            comments = list(issue_comments)
            if pr and str(pr.get("state", "")).lower() == "open":
                comments.extend(get_pr_comments(client, repo, pr["number"]))
            return Candidate(repo, issue, determine_mode(pr, comments), pr)
        except Exception:
            log.warning("mode discrimination failed; skipping issue", exc_info=True, extra={"repo": repo, "issue": number})
    return None
