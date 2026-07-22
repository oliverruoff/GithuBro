from __future__ import annotations

import os
from dataclasses import dataclass


def _positive_int(name: str, default: int) -> int:
    raw = os.getenv(name, str(default))
    try:
        value = int(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer") from exc
    if value <= 0:
        raise ValueError(f"{name} must be greater than zero")
    return value


@dataclass(frozen=True)
class Config:
    github_pat: str
    repos: tuple[str, ...]
    username: str = "oliverruoff"
    trigger_label: str = "agent"
    in_progress_label: str = "agent-in-progress"
    done_label: str = "agent-done"
    base_branch: str = "main"
    pr_target: str = "main"
    pi_args: str = ""
    reasoning_effort: str = "medium"
    poll_interval: int = 900
    heartbeat_interval: int = 1200
    heartbeat_stale_after: int = 2700
    run_timeout: int = 5400
    log_level: str = "INFO"

    @classmethod
    def from_env(cls) -> "Config":
        pat = os.getenv("GITHUB_PAT", "").strip()
        repos = tuple(x.strip() for x in os.getenv("GITHUB_REPOS", "").split(",") if x.strip())
        if not pat:
            raise ValueError("GITHUB_PAT is required")
        if not repos:
            raise ValueError("GITHUB_REPOS must contain at least one owner/repo")
        if any(repo.count("/") != 1 or not all(repo.split("/")) for repo in repos):
            raise ValueError("GITHUB_REPOS entries must use owner/repo format")
        effort = os.getenv("BRO_REASONING_EFFORT", "medium").lower()
        if effort not in {"low", "medium", "high"}:
            raise ValueError("BRO_REASONING_EFFORT must be low, medium, or high")
        log_level = os.getenv("BRO_LOG_LEVEL", "INFO").upper()
        if log_level not in {"DEBUG", "INFO", "WARNING", "ERROR"}:
            raise ValueError("BRO_LOG_LEVEL must be DEBUG, INFO, WARNING, or ERROR")
        heartbeat = _positive_int("BRO_HEARTBEAT_INTERVAL_SECONDS", 1200)
        stale = _positive_int("BRO_HEARTBEAT_STALE_AFTER_SECONDS", 2700)
        if stale <= heartbeat:
            raise ValueError("BRO_HEARTBEAT_STALE_AFTER_SECONDS must exceed heartbeat interval")
        base = os.getenv("GITHUB_BASE_BRANCH", "main")
        return cls(
            github_pat=pat,
            repos=repos,
            username=os.getenv("GITHUB_USERNAME", "oliverruoff"),
            trigger_label=os.getenv("GITHUB_LABEL_TRIGGER", "agent"),
            in_progress_label=os.getenv("GITHUB_LABEL_IN_PROGRESS", "agent-in-progress"),
            done_label=os.getenv("GITHUB_LABEL_DONE", "agent-done"),
            base_branch=base,
            pr_target=os.getenv("GITHUB_PR_TARGET", base),
            pi_args=os.getenv("PI_ARGS", ""),
            reasoning_effort=effort,
            poll_interval=_positive_int("BRO_POLL_INTERVAL_SECONDS", 900),
            heartbeat_interval=heartbeat,
            heartbeat_stale_after=stale,
            run_timeout=_positive_int("BRO_RUN_TIMEOUT_SECONDS", 5400),
            log_level=log_level,
        )
