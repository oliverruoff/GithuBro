from __future__ import annotations

import glob
import shutil
from datetime import datetime

from app.config import Config
from app.github.client import GitHubClient
from app.github.issues import post_comment
from app.github.labels import transition
from app.modes import Comment
from app.util.time import seconds_old


def latest_runner_activity(comments: list[Comment]) -> Comment | None:
    runners = [c for c in comments if c.body.startswith("[githubro:runner]")]
    return max(runners, key=lambda c: c.created_at, default=None)


def is_stale(comments: list[Comment], stale_after: int, now: datetime | None = None) -> bool:
    latest = latest_runner_activity(comments)
    return latest is None or seconds_old(latest.created_at, now) > stale_after


def recover(client: GitHubClient, config: Config, repo: str, number: int, comments: list[Comment]) -> None:
    latest = latest_runner_activity(comments)
    age = seconds_old(latest.created_at) if latest else None
    minutes = max(1, config.heartbeat_stale_after // 60)
    body = (
        "[githubro:runner][event:recovery]\n"
        f"♻️ githubro detected a stale run on this issue (last runner activity > {minutes} minutes ago).\n"
        "Resetting and re-queueing.\n"
        f"@{config.username}"
    )
    post_comment(client, repo, number, body)
    transition(client, repo, number, add=config.trigger_label, remove=config.in_progress_label)
    basename = repo.rsplit("/", 1)[-1]
    for path in glob.glob(f"/tmp/{basename}-{number}-*"):
        shutil.rmtree(path, ignore_errors=True)
